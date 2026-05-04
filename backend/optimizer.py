"""
optimizer.py — Rule-based static analysis engine.
Checks for: long methods, deep nesting, magic numbers, dead code,
god classes, missing docstrings, unused imports.
No AI — pure AST/regex rules.
"""

import ast
import re
from dataclasses import dataclass, field
from backend.parser import ParsedCode


# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: str        # "critical" | "warning" | "info"
    category: str
    message: str
    line: int
    suggestion: str
    code_snippet: str = ""


@dataclass
class OptimizationReport:
    score: int           # 0–100
    issues: list[Issue]
    summary: dict        # counts by severity
    cleaned_code: str    # original code + inline comment suggestions


# ─────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────

MAX_METHOD_LINES = 20
MAX_NESTING_DEPTH = 3
GOD_CLASS_METHODS = 10
MAGIC_NUMBER_WHITELIST = {0, 1, -1, 2, 10, 100, 1000, 3600, 24, 60}


# ─────────────────────────────────────────────────────────────
# Python-specific checks via AST
# ─────────────────────────────────────────────────────────────

def _check_python(code: str, parsed: ParsedCode) -> list[Issue]:
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        issues.append(Issue(
            severity="critical", category="Syntax",
            message=f"Syntax error: {e.msg}",
            line=e.lineno or 0,
            suggestion="Fix the syntax error before analysis.",
        ))
        return issues

    # ── Collect used names for dead-code detection ──
    all_loaded = set()
    all_stored = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                all_loaded.add(node.id)
            elif isinstance(node.ctx, ast.Store):
                all_stored.add(node.id)

    # ── Unused imports ──
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                imported_names.add((name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names.add((name, node.lineno))

    for (name, lineno) in imported_names:
        if name not in all_loaded and name != '*':
            issues.append(Issue(
                severity="warning", category="Dead Code",
                message=f"Unused import: '{name}'",
                line=lineno,
                suggestion=f"Remove 'import {name}' if it's not needed.",
            ))

    # ── Function-level checks ──
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        fn_name = node.name
        start = node.lineno
        end = node.end_lineno or node.lineno
        fn_lines = end - start + 1

        # Long method
        if fn_lines > MAX_METHOD_LINES:
            issues.append(Issue(
                severity="warning", category="Long Method",
                message=f"Function '{fn_name}' is {fn_lines} lines long (max: {MAX_METHOD_LINES})",
                line=start,
                suggestion=f"Break '{fn_name}' into smaller helper functions.",
            ))

        # Missing docstring
        has_doc = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False
        if not has_doc and fn_name != '__init__':
            issues.append(Issue(
                severity="info", category="Missing Docstring",
                message=f"Function '{fn_name}' has no docstring",
                line=start,
                suggestion=f'Add a docstring: def {fn_name}(...):\\n    """Description here."""',
            ))

        # Deep nesting
        def _max_depth(n, depth=0):
            if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                depth += 1
            max_d = depth
            for child in ast.iter_child_nodes(n):
                max_d = max(max_d, _max_depth(child, depth))
            return max_d

        nest = _max_depth(node)
        if nest > MAX_NESTING_DEPTH:
            issues.append(Issue(
                severity="warning", category="Deep Nesting",
                message=f"Function '{fn_name}' has nesting depth {nest} (max: {MAX_NESTING_DEPTH})",
                line=start,
                suggestion="Extract nested logic into helper functions or use early returns.",
            ))

        # Magic numbers
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                val = child.value
                if val not in MAGIC_NUMBER_WHITELIST and not isinstance(val, bool):
                    issues.append(Issue(
                        severity="info", category="Magic Number",
                        message=f"Magic number {val} in '{fn_name}'",
                        line=getattr(child, 'lineno', start),
                        suggestion=f"Replace {val} with a named constant, e.g., MAX_VALUE = {val}",
                    ))

        # Unused variables
        stored_in_fn = set()
        loaded_in_fn = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    stored_in_fn.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    loaded_in_fn.add(child.id)
        unused_vars = stored_in_fn - loaded_in_fn - {'_'}
        for var in unused_vars:
            if not var.startswith('_'):
                issues.append(Issue(
                    severity="info", category="Dead Code",
                    message=f"Variable '{var}' assigned but never used in '{fn_name}'",
                    line=start,
                    suggestion=f"Remove or use '{var}', or prefix with '_' if intentionally unused.",
                ))

    # ── Class-level checks ──
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        cls_name = node.name
        methods = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        n_methods = len(methods)

        # God class
        if n_methods >= GOD_CLASS_METHODS:
            issues.append(Issue(
                severity="critical", category="God Class",
                message=f"Class '{cls_name}' has {n_methods} methods (threshold: {GOD_CLASS_METHODS})",
                line=node.lineno,
                suggestion=f"Split '{cls_name}' into smaller, focused classes following Single Responsibility Principle.",
            ))

        # Missing class docstring
        has_doc = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False
        if not has_doc:
            issues.append(Issue(
                severity="info", category="Missing Docstring",
                message=f"Class '{cls_name}' has no docstring",
                line=node.lineno,
                suggestion=f'Add a class docstring: class {cls_name}:\\n    """Description here."""',
            ))

    return issues


# ─────────────────────────────────────────────────────────────
# Java-specific checks via regex
# ─────────────────────────────────────────────────────────────

def _check_java(code: str, parsed: ParsedCode) -> list[Issue]:
    issues = []
    lines = code.splitlines()

    for cls in parsed.classes:
        # God class
        if len(cls.methods) >= GOD_CLASS_METHODS:
            issues.append(Issue(
                severity="critical", category="God Class",
                message=f"Class '{cls.name}' has {len(cls.methods)} methods",
                line=1,
                suggestion=f"Split '{cls.name}' into smaller, focused classes.",
            ))

        for method in cls.methods:
            # Long method
            if method.lines > MAX_METHOD_LINES:
                issues.append(Issue(
                    severity="warning", category="Long Method",
                    message=f"Method '{method.name}' in '{cls.name}' is {method.lines} lines",
                    line=method.start_line,
                    suggestion=f"Refactor '{method.name}' into smaller helper methods.",
                ))

            # Deep nesting
            if method.nesting_depth > MAX_NESTING_DEPTH:
                issues.append(Issue(
                    severity="warning", category="Deep Nesting",
                    message=f"Method '{method.name}' has nesting depth {method.nesting_depth}",
                    line=method.start_line,
                    suggestion="Extract nested blocks or use guard clauses.",
                ))

            # Missing docstring/javadoc
            if not method.has_docstring and method.name != cls.name:
                issues.append(Issue(
                    severity="info", category="Missing Javadoc",
                    message=f"Method '{method.name}' in '{cls.name}' has no Javadoc comment",
                    line=method.start_line,
                    suggestion=f"Add /** ... */ Javadoc above '{method.name}'.",
                ))

            # Magic numbers
            for num in method.magic_numbers[:3]:  # cap per method
                issues.append(Issue(
                    severity="info", category="Magic Number",
                    message=f"Magic number {num} in '{method.name}'",
                    line=method.start_line,
                    suggestion=f"Replace {num} with a named constant.",
                ))

    # Unused imports (basic check)
    imports = re.findall(r'import\s+([\w.]+)\s*;', code)
    for imp in imports:
        short = imp.split('.')[-1]
        if short != '*' and code.count(short) <= 1:
            issues.append(Issue(
                severity="warning", category="Dead Code",
                message=f"Possibly unused import: {imp}",
                line=1,
                suggestion=f"Remove 'import {imp}' if not used.",
            ))

    return issues


# ─────────────────────────────────────────────────────────────
# Score Calculation
# ─────────────────────────────────────────────────────────────

SEVERITY_WEIGHTS = {"critical": 15, "warning": 5, "info": 1}


def _calc_score(issues: list[Issue]) -> int:
    penalty = sum(SEVERITY_WEIGHTS.get(i.severity, 1) for i in issues)
    score = max(0, 100 - penalty)
    return score


# ─────────────────────────────────────────────────────────────
# Cleaned Code Generator
# ─────────────────────────────────────────────────────────────

def _generate_cleaned_code(code: str, issues: list[Issue], language: str) -> str:
    lines = code.splitlines()
    comment_char = "#" if language == "python" else "//"

    # Group issues by line number
    line_issues: dict[int, list[Issue]] = {}
    for issue in issues:
        ln = issue.line
        if ln > 0:
            line_issues.setdefault(ln, []).append(issue)

    output = []
    header_comment = (
        f"{comment_char} ═══════════════════════════════════════════════════\n"
        f"{comment_char}  CodeLens Optimization Report\n"
        f"{comment_char}  Issues found: {len(issues)}\n"
        f"{comment_char} ═══════════════════════════════════════════════════\n"
    )
    output.append(header_comment)

    for i, line in enumerate(lines, start=1):
        if i in line_issues:
            for issue in line_issues[i]:
                severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "•")
                output.append(
                    f"{comment_char} {severity_icon} [{issue.category}] {issue.message}\n"
                    f"{comment_char}    💡 {issue.suggestion}"
                )
        output.append(line)

    return "\n".join(output)


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def analyze(code: str, parsed: ParsedCode) -> OptimizationReport:
    if parsed.language == "python":
        issues = _check_python(code, parsed)
    else:
        issues = _check_java(code, parsed)

    # Remove duplicate issues (same line + category)
    seen = set()
    deduped = []
    for issue in issues:
        key = (issue.line, issue.category, issue.message[:40])
        if key not in seen:
            seen.add(key)
            deduped.append(issue)
    issues = deduped

    # Sort: critical first, then warnings, then info
    order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: (order.get(i.severity, 3), i.line))

    score = _calc_score(issues)
    summary = {
        "critical": sum(1 for i in issues if i.severity == "critical"),
        "warning": sum(1 for i in issues if i.severity == "warning"),
        "info": sum(1 for i in issues if i.severity == "info"),
        "total": len(issues),
    }
    cleaned = _generate_cleaned_code(code, issues, parsed.language)

    return OptimizationReport(score=score, issues=issues, summary=summary, cleaned_code=cleaned)
