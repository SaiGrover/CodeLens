# 🔬 CodeLens — Static Code Analysis Dashboard

> Paste code → Get metrics, diagrams, and optimization report. No AI API needed.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the backend (FastAPI)
uvicorn backend.main:app --reload --port 8000

# 3. In another terminal, start the frontend (Streamlit)
streamlit run frontend/app.py --server.port 8501
```

Or use the convenience script:
```bash
chmod +x run.sh && ./run.sh
```

Then open → **http://localhost:8501**

---

## 📁 Project Structure

```
codelens/
├── frontend/
│   └── app.py              ← Streamlit UI (dark-themed dashboard)
├── backend/
│   ├── main.py             ← FastAPI routes (/analyze, /detect-language, /diagram/png)
│   ├── parser.py           ← AST-based Python parser + regex Java parser
│   ├── metrics.py          ← Halstead + COCOMO + Coupling/Cohesion
│   ├── diagram.py          ← PlantUML syntax generator + public server renderer
│   └── optimizer.py        ← Rule-based static analysis engine
└── requirements.txt
```

---

## 📊 Features

| Feature | Description |
|---|---|
| **Language Detection** | Auto-detects Python or Java |
| **Halstead Metrics** | Volume, Difficulty, Effort, Time, Predicted Bugs |
| **COCOMO Estimation** | Effort (PM), Dev Time, Team Size, Productivity |
| **Coupling & Cohesion** | Per-class analysis with Good/Medium/Bad labels |
| **Sequence Diagram** | Generated PlantUML → rendered via free public server |
| **Optimization Report** | Long methods, deep nesting, magic numbers, dead code, god classes, missing docstrings |

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/detect-language` | Detect Python or Java |
| `POST` | `/analyze` | Full analysis (all metrics) |
| `POST` | `/diagram/png` | Fetch diagram PNG bytes |

### Example

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello():\n    print(\"world\")"}'
```

---

## ✅ No External APIs Required

- Analysis is 100% local
- Only the sequence diagram render uses PlantUML's **free public server** (`plantuml.com/plantuml/png/...`)
- No API keys, no accounts, no data sent to AI services

---

## 📦 Dependencies

```
fastapi       — Backend API framework
uvicorn       — ASGI server for FastAPI
streamlit     — Frontend dashboard
httpx         — Async HTTP client
requests      — HTTP for PlantUML server
python-dotenv — Environment variable management
pydantic      — Data validation
```

Python 3.10+ required (uses `ast.parse` with `end_lineno` support).
