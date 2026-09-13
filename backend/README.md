# CyberRisk AI Backend

## 1. Create environment
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Optional API keys
Copy `.env.example` to `.env`.

- `OPENAI_API_KEY`: optional. Used only for LLM explanations/recommendations.
- `TABPFN_TOKEN`: may be needed by your TabPFN installation for headless/model access.

Never put these keys in the React frontend.

## 3. Start API
```bash
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

## Important model note
TabPFN is a pretrained tabular foundation model. This project does not train a new model from scratch. Its sklearn-style API uses `fit()` on the reference dataset for inference-time conditioning; if you require literally zero fitting/conditioning, replace that component with a hosted pretrained inference service.
