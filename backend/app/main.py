from __future__ import annotations
import os
from pathlib import Path
import traceback
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .data_processor import load_dataframe, make_model_frame, HISTORICAL_COLUMNS
from .pretrained_models import PretrainedTabularRiskModel
from .risk_engine import calculate_risk, risk_drivers
from .financial_engine import financial_impact
from .recommendation_engine import deterministic_recommendations, llm_recommendations
from .report_engine import make_report
from fastapi.responses import StreamingResponse

load_dotenv()

app = FastAPI(title="CyberRisk AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = PretrainedTabularRiskModel()

def prepare_reference(df: pd.DataFrame):
    # Keep the prototype responsive. For larger datasets, sample a representative
    # reference set while retaining class diversity.
    n = min(len(df), 5000)
    if len(df) > n:
        if "Attack_Success" in df.columns:
            parts = []
            for value in [0, 1]:
                part = df[df["Attack_Success"] == value]
                if len(part):
                    parts.append(part.sample(min(len(part), n // 2), random_state=42))
            ref = pd.concat(parts) if parts else df.sample(n, random_state=42)
            return ref.sample(min(n, len(ref)), random_state=42)
        return df.sample(n, random_state=42)
    return df

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "pretrained_tabpfn_available": model.available,
        "openai_enabled": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        data = await file.read()
        df = load_dataframe(data, file.filename)
        if len(df) == 0:
            raise ValueError("Dataset is empty.")

        # This prototype quantifies the latest uploaded assessment record; it
        # is intentionally not presented as enterprise portfolio aggregation.
        row = df.iloc[-1]
        reference = prepare_reference(df)

        X_all = make_model_frame(reference)
        X_new = make_model_frame(pd.DataFrame([row]))

        # Incident probability model: pretrained TabPFN classification.
        probability = model.classify(X_all, reference["Attack_Success"], X_new)
        probability_source = "TabPFN" if probability is not None else "Deterministic fallback"

        # For this prototype, the robust fallback is used when TabPFN cannot
        # initialize/download/handle the environment.
        if probability is None:
            from .risk_engine import heuristic_probability
            probability = heuristic_probability(row)

        # Financial impact model. We attempt pretrained TabPFN regression.
        predicted_loss = model.regress(X_all, reference["Financial_Loss_USD"], X_new)
        loss_source = "TabPFN" if predicted_loss is not None else "Historical / recovery fallback"
        if predicted_loss is None:
            predicted_loss = float(max(
                float(row.get("Financial_Loss_USD", 0)),
                float(row.get("Financial_Loss_USD", 0)) + float(row.get("Recovery_Cost_USD", 0))
            ))

        risk = calculate_risk(row, probability)
        financial = financial_impact(row, predicted_loss, risk["probability"])
        drivers = risk_drivers(row)
        recommendations = deterministic_recommendations(
            row, financial["potential_loss_usd"]
        )

        llm_context = {
            "risk": risk,
            "financial": financial,
            "drivers": drivers,
            "recommendations": recommendations
        }
        llm = llm_recommendations(llm_context)

        controls = [
            ("Multi-Factor Authentication", "NIST / ISO 27001", bool(row.get("MFA", 0))),
            ("Firewall", "NIST / CIS Controls", bool(row.get("Firewall", 0))),
            ("Endpoint Detection & Response", "NIST / CIS Controls", bool(row.get("EDR", 0))),
            ("Intrusion Detection", "NIST / CIS Controls", bool(row.get("IDS", 0))),
            ("Security Training", "NIST / ISO 27001", bool(row.get("Security_Training", 0))),
            ("Patch Management", "NIST / CIS Controls", float(row.get("Patch_Age_Days", 999)) <= 30),
            ("Vulnerability Management", "NIST / CIS Controls", float(row.get("Open_Vulnerabilities", 999)) <= 5),
            ("Security Audit", "ISO 27001 / RBI / SEBI", float(row.get("Security_Audit_Score", 0)) >= 70),
        ]
        compliance = {"score": round(sum(x[2] for x in controls) / len(controls) * 100, 1), "controls": [{"control":x[0],"framework":x[1],"status":"Implemented" if x[2] else "Gap"} for x in controls]}
        completeness = round(float(df.notna().mean().mean() * 100), 1)

        return {
            "dataset": {
                "filename": file.filename,
                "rows": int(len(df)),
                "columns": int(len(df.columns)),
                "industries": sorted(df["Industry"].dropna().astype(str).unique().tolist())[:30]
            },
            "model": {
                "name": "TabPFN pretrained tabular foundation model",
                "used_pretrained_model": probability_source == "TabPFN" or loss_source == "TabPFN",
                "fallback_used": probability_source != "TabPFN" or loss_source != "TabPFN",
                "prediction_source": {"incident_probability": probability_source, "financial_loss": loss_source},
                "status": "SUCCESS" if probability_source == "TabPFN" and loss_source == "TabPFN" else "FALLBACK",
                "reference_records": int(len(reference)),
                "data_completeness_pct": completeness,
                "financial_history_available": bool(reference["Financial_Loss_USD"].notna().any()),
                "note": "No model is trained from scratch. TabPFN may perform inference-time fitting/conditioning on reference data."
            },
            "risk_summary": risk,
            "financial_risk": financial,
            "risk_drivers": drivers,
            "recommendations": recommendations,
            "llm_explanation": llm,
            "compliance": compliance,
            "sample": {
                "industry": str(row["Industry"]),
                "company_size": str(row["Company_Size"]),
                "employee_count": int(row["Employee_Count"]),
                "attack_vector": str(row.get("Attack_Vector", "Unknown")),
                "assessment_record": int(len(df)),
                "assessment_note": "Latest uploaded assessment record is analyzed in this prototype."
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/simulate")
async def simulate(payload: dict):
    """
    Lightweight what-if simulation. Send:
    {
      "base": {"risk_score": 80, "potential_loss_usd": 1000000},
      "changes": {"MFA": true, "Firewall": true}
    }
    """
    try:
        base = payload["base"]
        changes = payload.get("changes", {})
        reduction = 0
        if changes.get("MFA") is True: reduction += 16
        if changes.get("Firewall") is True: reduction += 7
        if changes.get("EDR") is True: reduction += 12
        if changes.get("Security_Training") is True: reduction += 8
        if changes.get("Internet_Exposed") is False: reduction += 12
        reduction = min(reduction, 60)
        risk_before = float(base["risk_score"])
        loss_before = float(base["potential_loss_usd"])
        risk_after = round(risk_before * (1 - reduction / 100), 1)
        loss_after = round(loss_before * (1 - reduction / 100), 2)
        return {
            "risk_before": risk_before,
            "risk_after": risk_after,
            "risk_reduction_pct": round((1 - risk_after / max(risk_before, 0.01)) * 100, 1),
            "loss_before_usd": loss_before,
            "loss_after_usd": loss_after,
            "loss_avoided_usd": round(loss_before - loss_after, 2)
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Simulation error: {type(exc).__name__}: {exc}")

@app.post("/api/optimize")
async def optimize(payload: dict):
    budget = float(payload.get("budget_usd", 100000))
    options = payload.get("options", [])
    chosen, spent, reduction = [], 0, 0
    for item in sorted(options, key=lambda x: float(x.get("rosi_pct", 0)), reverse=True):
        cost = float(item.get("estimated_cost_usd", 0))
        if spent + cost <= budget:
            chosen.append(item)
            spent += cost
            reduction += float(item.get("expected_risk_reduction_pct", 0))
    return {
        "budget_usd": budget,
        "spent_usd": round(spent, 2),
        "remaining_usd": round(budget - spent, 2),
        "estimated_risk_reduction_pct": round(min(reduction, 90), 1),
        "estimated_exposure_avoided_usd": round(sum(float(x.get("expected_loss_avoided_usd", 0)) for x in chosen), 2),
        "selected_actions": chosen
    }


@app.post("/api/report")
async def report(payload: dict):
    try:
        pdf = make_report(payload)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=CyberRisk_AI_Report.pdf"}
        )
    except Exception as exc:
        print("PDF REPORT ERROR:", repr(exc))
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"PDF report generation error: {type(exc).__name__}: {exc}"
        )
