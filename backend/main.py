"""
main.py — FastAPI backend for CodeLens.
Diagram tab uses PlantUML (public server PNG) instead of Plotly.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import traceback

from backend.parser import parse_code, detect_language
from backend.metrics import compute_halstead, compute_cocomo, compute_coupling_cohesion
from backend.diagram import generate_plantuml, get_plantuml_url, fetch_diagram_png
from backend.optimizer import analyze

app = FastAPI(title="CodeLens API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────

class CodeRequest(BaseModel):
    code: str


class AnalysisResponse(BaseModel):
    language: str
    loc: int
    total_lines: int
    halstead: dict
    cocomo: dict
    coupling_cohesion: dict
    plantuml_syntax: str   # raw @startuml ... @enduml text
    plantuml_url: str      # PNG URL on public PlantUML server
    optimization: dict


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "CodeLens API running", "version": "3.0.0"}


@app.post("/detect-language")
def detect_lang(req: CodeRequest):
    lang = detect_language(req.code)
    return {"language": lang}


@app.post("/analyze", response_model=AnalysisResponse)
def analyze_code(req: CodeRequest):
    try:
        code = req.code.strip()
        if not code:
            raise HTTPException(status_code=400, detail="No code provided.")

        parsed   = parse_code(code)
        halstead = compute_halstead(parsed)
        cocomo   = compute_cocomo(parsed)
        cc       = compute_coupling_cohesion(parsed)

        puml_text = generate_plantuml(parsed)
        puml_url  = get_plantuml_url(puml_text)

        opt_report = analyze(code, parsed)

        return AnalysisResponse(
            language=parsed.language,
            loc=parsed.loc,
            total_lines=parsed.total_lines,
            halstead={
                "n1": halstead.n1,
                "n2": halstead.n2,
                "N1": halstead.N1,
                "N2": halstead.N2,
                "vocabulary": halstead.n,
                "length": halstead.N,
                "volume": halstead.volume,
                "difficulty": halstead.difficulty,
                "effort": halstead.effort,
                "time_seconds": halstead.time,
                "time_minutes": round(halstead.time / 60, 2),
                "predicted_bugs": halstead.bugs,
            },
            cocomo={
                "loc": cocomo.loc,
                "kloc": cocomo.kloc,
                "project_type": cocomo.project_type,
                "effort_person_months": cocomo.effort_pm,
                "dev_time_months": cocomo.dev_time_months,
                "team_size": cocomo.team_size,
                "productivity_loc_per_pm": cocomo.productivity,
            },
            coupling_cohesion={
                "coupling_score": cc.coupling_score,
                "cohesion_score": cc.cohesion_score,
                "coupling_label": cc.coupling_label,
                "cohesion_label": cc.cohesion_label,
                "class_details": cc.class_details,
            },
            plantuml_syntax=puml_text,
            plantuml_url=puml_url,
            optimization={
                "score": opt_report.score,
                "summary": opt_report.summary,
                "issues": [
                    {
                        "severity": i.severity,
                        "category": i.category,
                        "message": i.message,
                        "line": i.line,
                        "suggestion": i.suggestion,
                    }
                    for i in opt_report.issues
                ],
                "cleaned_code": opt_report.cleaned_code,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}\n{traceback.format_exc()}"
        )


@app.post("/diagram/png")
def get_diagram_png(req: CodeRequest):
    """Fetch and proxy the PNG from the PlantUML public server."""
    try:
        parsed   = parse_code(req.code)
        puml     = generate_plantuml(parsed)
        png      = fetch_diagram_png(puml)
        if png:
            return Response(content=png, media_type="image/png")
        raise HTTPException(
            status_code=503,
            detail="PlantUML server unreachable. Check your internet connection."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diagram/url")
def get_diagram_url(req: CodeRequest):
    """Return just the PlantUML PNG URL without fetching the image."""
    try:
        parsed = parse_code(req.code)
        puml   = generate_plantuml(parsed)
        return {"url": get_plantuml_url(puml), "syntax": puml}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
