from __future__ import annotations

def financial_impact(row, predicted_loss_usd: float, probability: float):
    historical = float(row["Financial_Loss_USD"])
    recovery = float(row["Recovery_Cost_USD"])
    downtime = float(row["Downtime_Hours"])
    records = float(row["Records_Compromised"])
    exfil = float(row["Data_Exfiltration_GB"])

    base = max(
        predicted_loss_usd,
        historical + recovery,
        historical * 1.25,
        1000.0
    )
    operational_factor = 1 + min(1.0, downtime / 100) * 0.30
    data_factor = 1 + min(1.0, records / 1000000) * 0.25 + min(1.0, exfil / 100) * 0.20
    potential_loss = base * operational_factor * data_factor
    eal = potential_loss * probability

    return {
        "potential_loss_usd": round(potential_loss, 2),
        "expected_annual_loss_usd": round(eal, 2),
        "historical_loss_usd": round(historical, 2),
        "recovery_cost_usd": round(recovery, 2),
        "downtime_hours": round(downtime, 2),
        "records_compromised": round(records, 0),
        "data_exfiltration_gb": round(exfil, 2)
    }
