"""
metrics.py — Halstead Metrics, COCOMO Estimation, Coupling & Cohesion analysis.
Pure math — no external APIs needed.
"""

import math
from dataclasses import dataclass
from typing import Optional
from backend.parser import ParsedCode


# ─────────────────────────────────────────────────────────────
# Halstead Metrics
# ─────────────────────────────────────────────────────────────

@dataclass
class HalsteadMetrics:
    n1: int          # unique operators
    n2: int          # unique operands
    N1: int          # total operators
    N2: int          # total operands
    n: int           # vocabulary = n1 + n2
    N: int           # length = N1 + N2
    volume: float    # V = N * log2(n)
    difficulty: float  # D = (n1/2) * (N2/n2)
    effort: float    # E = D * V
    time: float      # T = E / 18  (seconds)
    bugs: float      # B = V / 3000


def compute_halstead(parsed: ParsedCode) -> HalsteadMetrics:
    all_ops = parsed.operators
    all_opds = parsed.operands

    N1 = len(all_ops)
    N2 = len(all_opds)
    n1 = len(set(all_ops))
    n2 = len(set(all_opds))

    # Guard against degenerate input
    n1 = max(n1, 1)
    n2 = max(n2, 1)
    N1 = max(N1, 1)
    N2 = max(N2, 1)

    n = n1 + n2
    N = N1 + N2

    volume = N * math.log2(n) if n > 1 else 0
    difficulty = (n1 / 2) * (N2 / n2)
    effort = difficulty * volume
    time_sec = effort / 18
    bugs = volume / 3000

    return HalsteadMetrics(
        n1=n1, n2=n2, N1=N1, N2=N2,
        n=n, N=N,
        volume=round(volume, 2),
        difficulty=round(difficulty, 2),
        effort=round(effort, 2),
        time=round(time_sec, 2),
        bugs=round(bugs, 4),
    )


# ─────────────────────────────────────────────────────────────
# COCOMO Estimation
# ─────────────────────────────────────────────────────────────

@dataclass
class CocomoMetrics:
    loc: int
    kloc: float
    project_type: str      # Organic / Semi-detached / Embedded
    effort_pm: float       # Person-months
    dev_time_months: float
    team_size: float
    productivity: float    # LOC per person-month


# COCOMO Basic coefficients
COCOMO_MODES = {
    "Organic":       {"a": 2.4, "b": 1.05, "c": 2.5, "d": 0.38},
    "Semi-detached": {"a": 3.0, "b": 1.12, "c": 2.5, "d": 0.35},
    "Embedded":      {"a": 3.6, "b": 1.20, "c": 2.5, "d": 0.32},
}


def _classify_project(loc: int) -> str:
    if loc < 50_000:
        return "Organic"
    elif loc < 300_000:
        return "Semi-detached"
    else:
        return "Embedded"


def compute_cocomo(parsed: ParsedCode) -> CocomoMetrics:
    loc = parsed.loc
    kloc = loc / 1000.0
    project_type = _classify_project(loc)
    coeff = COCOMO_MODES[project_type]

    effort_pm = coeff["a"] * (kloc ** coeff["b"])
    dev_time = coeff["c"] * (effort_pm ** coeff["d"])
    team_size = effort_pm / dev_time if dev_time > 0 else 1
    productivity = loc / effort_pm if effort_pm > 0 else loc

    return CocomoMetrics(
        loc=loc,
        kloc=round(kloc, 4),
        project_type=project_type,
        effort_pm=round(effort_pm, 2),
        dev_time_months=round(dev_time, 2),
        team_size=round(team_size, 2),
        productivity=round(productivity, 0),
    )


# ─────────────────────────────────────────────────────────────
# Coupling & Cohesion
# ─────────────────────────────────────────────────────────────

@dataclass
class CouplingCohesionMetrics:
    coupling_score: float      # 0–10, lower = better (less coupled)
    cohesion_score: float      # 0–10, higher = better (more cohesive)
    coupling_label: str        # Good / Medium / Bad
    cohesion_label: str
    class_details: list[dict]  # per-class breakdown


def _label(score: float, higher_is_better: bool) -> str:
    if higher_is_better:
        if score >= 7:
            return "Good"
        elif score >= 4:
            return "Medium"
        else:
            return "Bad"
    else:
        if score <= 3:
            return "Good"
        elif score <= 6:
            return "Medium"
        else:
            return "Bad"


def compute_coupling_cohesion(parsed: ParsedCode) -> CouplingCohesionMetrics:
    classes = parsed.classes

    if not classes:
        # For script-like code with only functions
        n_funcs = len(parsed.functions)
        cohesion = min(10.0, max(0.0, 10 - n_funcs * 0.5)) if n_funcs > 0 else 5.0
        return CouplingCohesionMetrics(
            coupling_score=1.0,
            cohesion_score=round(cohesion, 1),
            coupling_label=_label(1.0, False),
            cohesion_label=_label(cohesion, True),
            class_details=[],
        )

    class_names = {c.name for c in classes}
    details = []
    coupling_scores = []
    cohesion_scores = []

    for cls in classes:
        # Coupling: count how many OTHER classes this class references
        external_deps = {d for d in cls.dependencies if d in class_names and d != cls.name}
        n_external = len(external_deps)
        # Normalize: 0 external = fully decoupled (coupling=0), 5+ = highly coupled (coupling=10)
        raw_coupling = min(10.0, n_external * 2.0)

        # Cohesion: LCOM-inspired
        # High cohesion = methods share attributes / all methods related
        n_methods = len(cls.methods)
        n_attrs = len(cls.attributes)

        if n_methods == 0:
            cohesion = 5.0
        else:
            # How many methods use class attributes (self.x patterns)
            methods_using_attrs = 0
            for m in cls.methods:
                if any(attr in m.variables or attr in m.calls for attr in cls.attributes):
                    methods_using_attrs += 1
            if n_attrs > 0:
                cohesion_ratio = methods_using_attrs / n_methods
            else:
                # No attributes — procedural class, lower cohesion
                cohesion_ratio = 0.3
            # Penalize god classes
            god_class_penalty = max(0, (n_methods - 8) * 0.3) if n_methods > 8 else 0
            cohesion = max(0.0, min(10.0, cohesion_ratio * 10 - god_class_penalty))

        coupling_scores.append(raw_coupling)
        cohesion_scores.append(cohesion)
        details.append({
            "class": cls.name,
            "methods": n_methods,
            "attributes": n_attrs,
            "external_deps": list(external_deps),
            "coupling": round(raw_coupling, 1),
            "cohesion": round(cohesion, 1),
            "coupling_label": _label(raw_coupling, False),
            "cohesion_label": _label(cohesion, True),
        })

    avg_coupling = sum(coupling_scores) / len(coupling_scores)
    avg_cohesion = sum(cohesion_scores) / len(cohesion_scores)

    return CouplingCohesionMetrics(
        coupling_score=round(avg_coupling, 1),
        cohesion_score=round(avg_cohesion, 1),
        coupling_label=_label(avg_coupling, False),
        cohesion_label=_label(avg_cohesion, True),
        class_details=details,
    )
