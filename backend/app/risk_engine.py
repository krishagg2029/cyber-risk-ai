from __future__ import annotations
import math

def _clip(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))

def heuristic_probability(row) -> float:
    # Used only as a safe fallback if pretrained inference is unavailable.
    score = 0.18
    score += 0.09 * float(row["Internet_Exposed"])
    score += 0.07 * float(row["Phishing_Click"])
    score += 0.08 * float(row["Credential_Stolen"])
    score += 0.08 * float(row["Privilege_Escalation"])
    score += 0.07 * float(row["Lateral_Movement"])
    score += 0.05 * float(row["Persistence"])
    score += 0.06 * _clip(float(row["CVSS_Score"]) / 10)
    score += 0.06 * _clip(float(row["Open_Vulnerabilities"]) / 20)
    score += 0.04 * _clip(float(row["Patch_Age_Days"]) / 180)
    score += 0.04 * _clip(float(row["ThirdParty_Risk"]) / 100)
    score += 0.04 * _clip(float(row["Insider_Risk"]) / 100)
    score += 0.03 * (1 - _clip(float(row["Security_Maturity"]) / 100))
    score -= 0.07 * float(row["MFA"])
    score -= 0.04 * float(row["Firewall"])
    score -= 0.04 * float(row["EDR"])
    score -= 0.03 * float(row["IDS"])
    score -= 0.03 * float(row["Security_Training"])
    return _clip(score, 0.01, 0.99)

def control_effectiveness(row) -> float:
    values = [
        float(row["Firewall"]), float(row["MFA"]), float(row["EDR"]),
        float(row["IDS"]), float(row["Security_Training"]),
        1.0 if str(row["Password_Policy"]).lower() in {"strong", "high"} else 0.5,
        _clip(float(row["Security_Audit_Score"]) / 100),
        _clip(float(row["Security_Maturity"]) / 100),
    ]
    return round(sum(values) / len(values) * 100, 1)

def risk_level(score: float) -> str:
    if score >= 80: return "Critical"
    if score >= 60: return "High"
    if score >= 35: return "Medium"
    return "Low"

def calculate_risk(row, probability: float):
    effectiveness = control_effectiveness(row)
    adjusted = _clip(probability * (1 - 0.35 * effectiveness / 100), 0.01, 0.99)
    score = round(adjusted * 100, 1)
    return {
        "probability": round(adjusted, 4),
        "risk_score": score,
        "risk_level": risk_level(score),
        "control_effectiveness": effectiveness
    }

def risk_drivers(row):
    drivers = []
    checks = [
        ("High CVSS vulnerability severity", float(row["CVSS_Score"]) >= 7, float(row["CVSS_Score"]) * 3, f"CVSS = {float(row['CVSS_Score']):.1f}", "Critical vulnerabilities increase exploitation exposure."),
        ("Internet exposure", float(row["Internet_Exposed"]) == 1, 18, "Internet exposed = Yes", "External exposure increases the attack surface."),
        ("MFA not enabled", float(row["MFA"]) == 0, 16, "MFA = Disabled", "Compromised credentials face fewer barriers."),
        ("Aged patches", float(row["Patch_Age_Days"]) > 60, 12, f"Patch age = {float(row['Patch_Age_Days']):.0f} days", "Delayed patching leaves known weaknesses open longer."),
        ("Open vulnerabilities", float(row["Open_Vulnerabilities"]) >= 5, 12, f"Open vulnerabilities = {float(row['Open_Vulnerabilities']):.0f}", "Unremediated vulnerabilities increase exploitation paths."),
        ("Slow detection", float(row["Detection_Time_Min"]) > 120, 10, f"Detection time = {float(row['Detection_Time_Min']):.0f} min", "Longer detection time can increase incident impact."),
        ("Slow response", float(row["Response_Time_Min"]) > 120, 9, f"Response time = {float(row['Response_Time_Min']):.0f} min", "Slow containment can increase operational impact."),
        ("Third-party risk", float(row["ThirdParty_Risk"]) > 60, 8, f"Third-party risk = {float(row['ThirdParty_Risk']):.0f}", "Supplier dependencies can introduce additional attack paths."),
        ("Low security maturity", float(row["Security_Maturity"]) < 50, 8, f"Security maturity = {float(row['Security_Maturity']):.0f}", "Low maturity indicates fewer resilient security practices."),
    ]
    for name, condition, contribution, observed_value, explanation in checks:
        if condition:
            drivers.append({
                "factor": name,
                "contribution": round(min(35, contribution), 1),
                "severity": "Critical" if contribution >= 20 else "High",
                "observed_value": observed_value,
                "explanation": explanation,
            })
    return sorted(drivers, key=lambda x: x["contribution"], reverse=True)[:6]
