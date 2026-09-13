# CyberRisk Nexus — Full Stack

This ZIP contains both the React frontend and FastAPI backend.

## Architecture

React + Vite Cyber Investment War Room
→ POST `/api/analyze`
→ FastAPI
→ dataset validation/processing
→ pretrained TabPFN classification/regression
→ financial risk engine
→ risk drivers/recommendations
→ optional OpenAI LLM explanation
→ JSON
→ React dashboard: Quantify → Explain → Optimize → Simulate

## Implemented now

- Dataset-driven analysis of the latest uploaded assessment record
- TabPFN classification/regression when inference succeeds, with deterministic and financial fallbacks
- Risk scoring, financial estimation, Expected Annual Loss, evidence-based rule drivers and ROSI
- Risk appetite, security investment optimizer, scenario-based what-if comparison, control alignment and PDF reporting

## Future / production extensions

Live SIEM, EDR and vulnerability-scanner ingestion; enterprise portfolio aggregation; advanced uncertainty distributions and FAIR; dependency-aware optimization; organization-specific calibration; and continuous automated telemetry are not implemented in this prototype.

## Start backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Start frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally:
http://localhost:5173

## API keys

### OpenAI
Optional. Put your key in `backend/.env`:

```env
OPENAI_API_KEY=...
```

The key must stay in the backend. Never place it in React.

### TabPFN
TabPFN is a pretrained tabular foundation model. Depending on your installed version/environment, authentication or a model token may be required for downloading/accessing checkpoints. Follow the current TabPFN setup instructions.

## Important model clarification

The project does NOT train a new model from scratch.

However, TabPFN's Python estimator interface can use `fit()` with the uploaded/reference dataset for inference-time conditioning. If your requirement means absolutely zero fitting/conditioning, a hosted pretrained inference service is required instead.

## Dataset

The supplied Enterprise Cyber Kill Chain Dataset is expected to contain the cybersecurity and financial columns used by the backend.
