"""
parser.py — AST-based code parser for Python and regex-based for Java.
Extracts structural info: classes, methods, imports, calls, variables, operators.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MethodInfo:
    name: str
    lines: int
    start_line: int
    end_line: int
    args: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    has_docstring: bool = False
    nesting_depth: int = 0
    variables: list[str] = field(default_factory=list)
    magic_numbers: list[float] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    methods: list[MethodInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # classes it references


@dataclass
class ParsedCode:
    language: str
    loc: int  # lines of code (non-blank, non-comment)
    total_lines: int
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[MethodInfo] = field(default_factory=list)  # top-level functions
    imports: list[str] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    operands: list[str] = field(default_factory=list)
    all_calls: list[tuple[str, str]] = field(default_factory=list)  # (caller, callee)
    raw_lines: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Language Detection
# ─────────────────────────────────────────────────────────────

def detect_language(code: str) -> str:
    """Detect whether code is Python or Java."""
    java_indicators = [
        r'\bpublic\s+class\b',
        r'\bprivate\s+\w+\s+\w+\s*[;(]',
        r'\bSystem\.out\.println\b',
        r'\bpublic\s+static\s+void\s+main\b',
        r'^\s*import\s+java\.',
        r'\bnew\s+\w+\(',
        r';\s*$',
    ]
    java_score = sum(1 for p in java_indicators if re.search(p, code, re.MULTILINE))

    python_indicators = [
        r'^\s*def\s+\w+\s*\(',
        r'^\s*class\s+\w+.*:',
        r'^\s*import\s+\w+',
        r'^\s*from\s+\w+\s+import',
        r'print\s*\(',
        r'^\s*#',
        r':\s*$',
    ]
    python_score = sum(1 for p in python_indicators if re.search(p, code, re.MULTILINE))

    return "java" if java_score > python_score else "python"


# ─────────────────────────────────────────────────────────────
# Python Parser (AST-based)
# ─────────────────────────────────────────────────────────────

PYTHON_OPERATORS = {
    ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
    ast.Mod: '%', ast.Pow: '**', ast.FloorDiv: '//',
    ast.BitAnd: '&', ast.BitOr: '|', ast.BitXor: '^',
    ast.LShift: '<<', ast.RShift: '>>',
    ast.And: 'and', ast.Or: 'or', ast.Not: 'not',
    ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=',
    ast.Gt: '>', ast.GtE: '>=', ast.Is: 'is', ast.IsNot: 'is not',
    ast.In: 'in', ast.NotIn: 'not in',
    ast.USub: '-', ast.UAdd: '+', ast.Invert: '~',
    ast.If: 'if', ast.For: 'for', ast.While: 'while',
    ast.Return: 'return', ast.Assign: '=', ast.AugAssign: '+=',
}


def _max_nesting(node: ast.AST) -> int:
    """Compute max nesting depth for a function/method body."""
    def _depth(n, current=0):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            current += 1
        max_d = current
        for child in ast.iter_child_nodes(n):
            max_d = max(max_d, _depth(child, current))
        return max_d
    return _depth(node)


def _collect_calls(node: ast.AST) -> list[str]:
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
            elif isinstance(child.func, ast.Name):
                calls.append(child.func.id)
    return calls


def _collect_magic_numbers(node: ast.AST) -> list[float]:
    magic = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
            val = child.value
            if val not in (0, 1, -1, True, False, 2):
                magic.append(val)
    return magic


def _collect_variables(node: ast.AST) -> list[str]:
    vars_ = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            vars_.append(child.id)
    return list(set(vars_))


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.classes: list[ClassInfo] = []
        self.functions: list[MethodInfo] = []
        self.operators: list[str] = []
        self.operands: list[str] = []
        self.all_calls: list[tuple[str, str]] = []
        self._current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        prev = self._current_class
        self._current_class = node.name
        ci = ClassInfo(
            name=node.name,
            base_classes=[b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
        )
        # collect attributes
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Attribute) and isinstance(t.ctx, ast.Store):
                        ci.attributes.append(t.attr)
        # collect methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                mi = self._parse_func(item)
                ci.methods.append(mi)
        # collect dependencies (names used in class body that look like class refs)
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                ci.dependencies.append(child.id)
        ci.dependencies = list(set(ci.dependencies) - {node.name})
        self.classes.append(ci)
        self.generic_visit(node)
        self._current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self._current_class is None:
            mi = self._parse_func(node)
            self.functions.append(mi)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _parse_func(self, node: ast.FunctionDef) -> MethodInfo:
        start = node.lineno
        end = node.end_lineno or node.lineno
        lines = end - start + 1
        has_doc = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False
        args = [a.arg for a in node.args.args]
        calls = _collect_calls(node)
        caller = self._current_class or "<module>"
        for c in calls:
            self.all_calls.append((caller, c))
        return MethodInfo(
            name=node.name,
            lines=lines,
            start_line=start,
            end_line=end,
            args=args,
            calls=calls,
            has_docstring=has_doc,
            nesting_depth=_max_nesting(node),
            variables=_collect_variables(node),
            magic_numbers=_collect_magic_numbers(node),
        )

    # collect operators and operands globally
    def visit_BinOp(self, node):
        op_name = PYTHON_OPERATORS.get(type(node.op), str(type(node.op).__name__))
        self.operators.append(op_name)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        op_name = PYTHON_OPERATORS.get(type(node.op), str(type(node.op).__name__))
        self.operators.append(op_name)
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op in node.ops:
            self.operators.append(PYTHON_OPERATORS.get(type(op), str(type(op).__name__)))
        self.generic_visit(node)

    def visit_Name(self, node):
        self.operands.append(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node):
        self.operands.append(str(node.value))
        self.generic_visit(node)

    def visit_If(self, node):
        self.operators.append('if')
        self.generic_visit(node)

    def visit_For(self, node):
        self.operators.append('for')
        self.generic_visit(node)

    def visit_While(self, node):
        self.operators.append('while')
        self.generic_visit(node)

    def visit_Return(self, node):
        self.operators.append('return')
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.operators.append('=')
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.operators.append('import')
            self.operands.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.operators.append('import')
        if node.module:
            self.operands.append(node.module)
        self.generic_visit(node)


def _count_python_loc(code: str) -> tuple[int, int]:
    lines = code.splitlines()
    total = len(lines)
    loc = sum(
        1 for l in lines
        if l.strip() and not l.strip().startswith('#')
    )
    return loc, total


def parse_python(code: str) -> ParsedCode:
    lines = code.splitlines()
    loc, total = _count_python_loc(code)

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        # Return minimal parsed result on syntax error
        return ParsedCode(
            language="python", loc=loc, total_lines=total,
            raw_lines=lines
        )

    visitor = _PythonVisitor(lines)
    visitor.visit(tree)

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return ParsedCode(
        language="python",
        loc=loc,
        total_lines=total,
        classes=visitor.classes,
        functions=visitor.functions,
        imports=imports,
        operators=visitor.operators,
        operands=visitor.operands,
        all_calls=visitor.all_calls,
        raw_lines=lines,
    )


# ─────────────────────────────────────────────────────────────
# Java Parser (Regex-based)
# ─────────────────────────────────────────────────────────────

JAVA_OPERATORS = [
    '+', '-', '*', '/', '%', '++', '--', '==', '!=', '<', '>', '<=', '>=',
    '&&', '||', '!', '&', '|', '^', '~', '<<', '>>', '=', '+=', '-=',
    'if', 'for', 'while', 'switch', 'return', 'new', 'instanceof',
    'try', 'catch', 'throw', 'import', 'extends', 'implements',
]


def _extract_java_methods(class_body: str, class_name: str) -> list[MethodInfo]:
    methods = []
    # Match method signatures
    method_pattern = re.compile(
        r'(?:public|private|protected|static|final|synchronized|\s)*'
        r'(?:\w+(?:<[^>]*>)?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+\w+\s*)?\{',
        re.MULTILINE
    )
    lines = class_body.splitlines()
    for m in method_pattern.finditer(class_body):
        name = m.group(1)
        if name in ('if', 'for', 'while', 'switch', 'catch', 'try', class_name):
            continue
        start_pos = m.start()
        start_line = class_body[:start_pos].count('\n') + 1
        # rough end: find matching brace
        depth = 0
        end_line = start_line
        in_method = False
        for i, ch in enumerate(class_body[start_pos:], start_pos):
            if ch == '{':
                depth += 1
                in_method = True
            elif ch == '}':
                depth -= 1
                if in_method and depth == 0:
                    end_line = class_body[:i].count('\n') + 1
                    break
        method_lines = end_line - start_line + 1
        args_str = m.group(2)
        args = [a.strip().split()[-1] for a in args_str.split(',') if a.strip()]

        # calls
        body_text = class_body[start_pos:start_pos + (end_line - start_line + 1) * 80]
        call_matches = re.findall(r'(\w+)\s*\(', body_text)
        calls = [c for c in call_matches if c != name and c not in ('if', 'for', 'while')]

        # magic numbers
        magic_nums = [float(n) for n in re.findall(r'\b(\d+\.?\d*)\b', body_text)
                      if float(n) not in (0, 1, 2)]

        # nesting depth — count nested blocks
        nesting = 0
        max_nest = 0
        for ch in body_text:
            if ch == '{':
                nesting += 1
                max_nest = max(max_nest, nesting)
            elif ch == '}':
                nesting = max(0, nesting - 1)

        has_doc = '/**' in class_body[max(0, start_pos-200):start_pos] or \
                  '//' in class_body[max(0, start_pos-100):start_pos]

        methods.append(MethodInfo(
            name=name,
            lines=method_lines,
            start_line=start_line,
            end_line=end_line,
            args=args,
            calls=calls,
            has_docstring=has_doc,
            nesting_depth=max(0, max_nest - 1),
            magic_numbers=magic_nums,
        ))
    return methods


def parse_java(code: str) -> ParsedCode:
    lines = code.splitlines()
    total = len(lines)
    loc = sum(
        1 for l in lines
        if l.strip() and not l.strip().startswith('//') and not l.strip().startswith('*')
    )

    classes = []
    class_pattern = re.compile(
        r'(?:public|private|protected|abstract|final|\s)*class\s+(\w+)'
        r'(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{',
        re.MULTILINE
    )
    for cm in class_pattern.finditer(code):
        cname = cm.group(1)
        bases = [cm.group(2)] if cm.group(2) else []
        # Extract class body
        start = cm.end() - 1  # the opening brace
        depth = 0
        end = start
        for i, ch in enumerate(code[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = code[start:end+1]
        methods = _extract_java_methods(body, cname)
        # attributes: field declarations
        attr_pattern = re.compile(
            r'(?:private|public|protected)\s+(?:static\s+)?(?:final\s+)?'
            r'\w+(?:<[^>]*>)?\s+(\w+)\s*[=;]'
        )
        attrs = attr_pattern.findall(body)

        # dependencies: types used
        type_pattern = re.compile(r'\b([A-Z]\w+)\b')
        deps = list(set(type_pattern.findall(body)) - {cname})

        ci = ClassInfo(
            name=cname,
            methods=methods,
            attributes=list(set(attrs)),
            base_classes=bases,
            dependencies=deps,
        )
        classes.append(ci)

    # operators & operands
    operators = []
    operands = []
    for op in JAVA_OPERATORS:
        if re.search(r'\b' + re.escape(op) + r'\b', code):
            operators.extend([op] * len(re.findall(r'\b' + re.escape(op) + r'\b', code)))
    symbol_ops = ['+', '-', '*', '/', '==', '!=', '<=', '>=', '&&', '||']
    for op in symbol_ops:
        count = code.count(op)
        operators.extend([op] * count)

    # operands: identifiers and literals
    operands.extend(re.findall(r'\b[a-z_][a-zA-Z0-9_]*\b', code))
    operands.extend(re.findall(r'\b\d+\.?\d*\b', code))
    operands.extend(re.findall(r'"[^"]*"', code))

    imports = re.findall(r'import\s+([\w.]+)\s*;', code)

    # all calls
    all_calls = []
    call_pat = re.compile(r'(\w+)\.(\w+)\s*\(')
    for m in call_pat.finditer(code):
        all_calls.append((m.group(1), m.group(2)))

    return ParsedCode(
        language="java",
        loc=loc,
        total_lines=total,
        classes=classes,
        imports=imports,
        operators=operators,
        operands=operands,
        all_calls=all_calls,
        raw_lines=lines,
    )


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def parse_code(code: str) -> ParsedCode:
    lang = detect_language(code)
    if lang == "java":
        return parse_java(code)
    else:
        return parse_python(code)
