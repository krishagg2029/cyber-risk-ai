from __future__ import annotations
from pathlib import Path
import io
import json
import pandas as pd

REQUIRED_COLUMNS = {
    "Industry", "Company_Size", "Employee_Count",
    "Firewall", "MFA", "EDR", "IDS", "Security_Training",
    "Password_Policy", "Patch_Age_Days", "Open_Vulnerabilities",
    "CVSS_Score", "Internet_Exposed", "Security_Audit_Score",
    "Phishing_Click", "Credential_Stolen", "Privilege_Escalation",
    "Lateral_Movement", "Persistence", "Data_Encrypted",
    "Data_Exfiltration_GB", "Attack_Success", "Attack_Stage",
    "Attack_Complexity", "Detection_Time_Min", "Response_Time_Min",
    "Downtime_Hours", "Records_Compromised", "Financial_Loss_USD",
    "Recovery_Cost_USD", "Cyber_Risk_Score", "Risk_Level",
    "Incident_Severity", "ThirdParty_Risk", "Insider_Risk",
    "Security_Maturity", "SOC_Team_Size"
}

# Inputs available before a new incident are deliberately separated from
# historical/reference columns and model targets.  Older demo datasets with all
# fields remain fully compatible, while a current assessment is not rejected
# merely because a post-incident outcome is absent.
DECISION_INPUT_COLUMNS = {
    "Industry", "Company_Size", "Employee_Count", "Firewall", "MFA", "EDR",
    "IDS", "Security_Training", "Password_Policy", "Patch_Age_Days",
    "Open_Vulnerabilities", "CVSS_Score", "Internet_Exposed",
    "Security_Audit_Score", "Detection_Time_Min", "Response_Time_Min",
    "ThirdParty_Risk", "Insider_Risk", "Security_Maturity", "SOC_Team_Size",
}
HISTORICAL_COLUMNS = {"Financial_Loss_USD", "Recovery_Cost_USD", "Downtime_Hours", "Records_Compromised", "Data_Exfiltration_GB"}

NUMERIC_COLUMNS = [
    "Employee_Count", "Firewall", "MFA", "EDR", "IDS", "Security_Training",
    "Patch_Age_Days", "Open_Vulnerabilities", "CVSS_Score", "Internet_Exposed",
    "Security_Audit_Score", "Phishing_Click", "Credential_Stolen",
    "Privilege_Escalation", "Lateral_Movement", "Persistence", "Data_Encrypted",
    "Data_Exfiltration_GB", "Attack_Success", "Detection_Time_Min",
    "Response_Time_Min", "Downtime_Hours", "Records_Compromised",
    "Financial_Loss_USD", "Recovery_Cost_USD", "Cyber_Risk_Score",
    "ThirdParty_Risk", "Insider_Risk", "Security_Maturity", "SOC_Team_Size"
]

def load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    bio = io.BytesIO(file_bytes)
    if suffix == ".csv":
        df = pd.read_csv(bio)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(bio)
    elif suffix == ".json":
        df = pd.read_json(bio)
    else:
        raise ValueError("Supported files: CSV, XLSX, XLS, JSON")

    df.columns = [str(c).strip() for c in df.columns]
    missing = sorted(DECISION_INPUT_COLUMNS - set(df.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing[:15]))

    for col in NUMERIC_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].notna().any():
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = 0

    for col in ["Industry", "Company_Size", "Password_Policy", "Attack_Stage", "Attack_Complexity"]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").astype(str)

    return df

def make_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create a compact numerical feature matrix for pretrained tabular inference."""
    cols = [
        "Employee_Count", "Firewall", "MFA", "EDR", "IDS", "Security_Training",
        "Patch_Age_Days", "Open_Vulnerabilities", "CVSS_Score", "Internet_Exposed",
        "Security_Audit_Score", "Phishing_Click", "Credential_Stolen",
        "Privilege_Escalation", "Lateral_Movement", "Persistence", "Data_Encrypted",
        "Data_Exfiltration_GB", "Detection_Time_Min", "Response_Time_Min",
        "Downtime_Hours", "Records_Compromised", "ThirdParty_Risk",
        "Insider_Risk", "Security_Maturity", "SOC_Team_Size"
    ]
    x = df[cols].copy()
    return x.replace([float("inf"), float("-inf")], 0).fillna(0)
