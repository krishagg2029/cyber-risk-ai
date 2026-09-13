from __future__ import annotations
import os
import json

ACTIONS = [
    {"action": "Enable MFA", "cost": 15000, "risk_reduction": 0.16},
    {"action": "Patch critical vulnerabilities", "cost": 25000, "risk_reduction": 0.20},
    {"action": "Increase EDR coverage", "cost": 30000, "risk_reduction": 0.13},
    {"action": "Improve security training", "cost": 10000, "risk_reduction": 0.08},
    {"action": "Reduce Internet exposure", "cost": 20000, "risk_reduction": 0.12},
    {"action": "Improve detection and response", "cost": 40000, "risk_reduction": 0.14},
]

def deterministic_recommendations(row, potential_loss):
    recs = []
    if float(row["MFA"]) == 0:
        recs.append(ACTIONS[0])
    if float(row["Patch_Age_Days"]) > 60 or float(row["Open_Vulnerabilities"]) >= 5:
        recs.append(ACTIONS[1])
    if float(row["EDR"]) == 0:
        recs.append(ACTIONS[2])
    if float(row["Security_Training"]) == 0:
        recs.append(ACTIONS[3])
    if float(row["Internet_Exposed"]) == 1:
        recs.append(ACTIONS[4])
    if float(row["Detection_Time_Min"]) > 120 or float(row["Response_Time_Min"]) > 120:
        recs.append(ACTIONS[5])

    output = []
    for item in recs[:6]:
        avoided = potential_loss * item["risk_reduction"]
        cost = item["cost"]
        rosi = (avoided - cost) / cost * 100
        output.append({
            "action": item["action"],
            "priority": "Critical" if item["risk_reduction"] >= 0.16 else "High",
            "estimated_cost_usd": cost,
            "expected_risk_reduction_pct": round(item["risk_reduction"] * 100, 1),
            "expected_loss_avoided_usd": round(avoided, 2),
            "rosi_pct": round(rosi, 1)
        })
    return sorted(output, key=lambda x: x["rosi_pct"], reverse=True)

def llm_recommendations(context):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = """You are a cybersecurity risk analyst. Return practical management recommendations
based ONLY on the supplied JSON. Do not invent facts. Explain priorities, cost-effectiveness,
and financial risk. Keep it concise."""
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            input=prompt + "\nDATA:\n" + json.dumps(context)
        )
        return response.output_text
    except Exception as exc:
        return {"error": str(exc)}
