from io import BytesIO
import html
import math
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

def safe_text(value, default="—"):
    if value is None:
        return default
    if isinstance(value, (dict, list, tuple)):
        if isinstance(value, dict):
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        return ", ".join(str(v) for v in value)
    text = str(value)
    return text if text.strip() else default

def safe_float(value, default=0.0):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default

def money(value):
    return f"${safe_float(value):,.0f}"

def para(value, style):
    return Paragraph(html.escape(safe_text(value)).replace("\n", "<br/>"), style)

def make_table(rows, widths, header=True):
    normalized = []
    for row in rows:
        normalized.append([safe_text(cell) for cell in row])
    table = Table(normalized, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#d8dee8")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("PADDING", (0,0), (-1,-1), 6),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef3fa")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(commands))
    return table

def make_report(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid report payload.")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36,
        title="CyberRisk AI Report",
        author="CyberRisk AI"
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=20, leading=24, spaceAfter=18
    )
    heading = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"],
        fontSize=14, leading=18, spaceBefore=8, spaceAfter=10
    )
    body = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"],
        fontSize=9.5, leading=13, spaceAfter=8
    )
    small = ParagraphStyle(
        "ReportSmall", parent=body, fontSize=8, leading=10
    )

    r = data.get("risk_summary") or {}
    f = data.get("financial_risk") or {}
    ds = data.get("dataset") or {}
    comp = data.get("compliance") or {}
    drivers = data.get("risk_drivers") or []
    recommendations = data.get("recommendations") or []
    appetite = data.get("risk_appetite") or {}
    simulation = data.get("simulation") or {}
    model = data.get("model") or {}

    story = [
        Paragraph("CyberRisk AI — Cyber Risk Quantification Report", title),
        para(
            f"Dataset: {safe_text(ds.get('filename'), 'Uploaded dataset')} | "
            f"Rows: {safe_text(ds.get('rows'))} | Columns: {safe_text(ds.get('columns'))}",
            body
        ),
        Spacer(1, 8),
        Paragraph("Executive Summary", heading),
    ]

    summary = [
        ["Metric", "Result"],
        ["Cyber Risk Score", f"{safe_text(r.get('risk_score'))}/100"],
        ["Risk Level", safe_text(r.get("risk_level"))],
        ["Incident Probability", f"{safe_float(r.get('probability'))*100:.1f}%"],
        ["Potential Financial Loss", money(f.get("potential_loss_usd"))],
        ["Expected Annual Loss", money(f.get("expected_annual_loss_usd"))],
        ["Control Effectiveness", f"{safe_text(r.get('control_effectiveness'))}%"],
        ["Risk Appetite Status", safe_text(appetite.get("status"), "Not configured")],
        ["Compliance Status", f"{safe_text(comp.get('score'))}%"],
    ]
    story += [make_table(summary, [235, 275]), Spacer(1, 16)]

    story.append(Paragraph("Top Risk Drivers", heading))
    driver_rows = [["Factor", "Observed evidence", "Priority", "Contribution"]]
    for item in drivers[:10]:
        if not isinstance(item, dict):
            continue
        driver_rows.append([
            item.get("factor", ""),
            item.get("observed_value", ""),
            item.get("severity", ""),
            item.get("contribution", "")
        ])
    if len(driver_rows) == 1:
        driver_rows.append(["No major drivers detected", "—", "—", "—"])
    story += [make_table(driver_rows, [190, 150, 85, 85]), Spacer(1, 16)]

    story.append(Paragraph("AI Recommendations", heading))
    rec_rows = [["Action", "Priority", "Cost", "Avoided exposure", "ROSI"]]
    for item in recommendations[:10]:
        if not isinstance(item, dict):
            continue
        rec_rows.append([
            item.get("action", ""),
            item.get("priority", ""),
            money(item.get("estimated_cost_usd")),
            money(item.get("expected_loss_avoided_usd")),
            f"{safe_text(item.get('rosi_pct'))}%"
        ])
    if len(rec_rows) == 1:
        rec_rows.append(["No immediate recommendation", "—", "—", "—", "—"])
    story += [make_table(rec_rows, [180, 70, 80, 110, 70]), Spacer(1, 16)]

    story.append(Paragraph("Scenario-Based What-If Estimate", heading))
    if simulation:
        story += [make_table([["Risk before / after", f"{safe_text(simulation.get('risk_before'))} / {safe_text(simulation.get('risk_after'))}"], ["Exposure avoided", money(simulation.get("loss_avoided_usd"))]], [235, 275]), Spacer(1, 16)]
    else:
        story.append(para("No what-if scenario was included in this report payload.", body))

    story.append(Paragraph("Data and Model Status", heading))
    story += [make_table([["Prediction source", safe_text(model.get("prediction_source"))], ["Reference records", safe_text(model.get("reference_records"))], ["Data completeness", f"{safe_text(model.get('data_completeness_pct'))}%"], ["Model status", safe_text(model.get("status"))]], [235, 275]), PageBreak()]

    story.append(Paragraph("Compliance Status", heading))
    control_rows = [["Control", "Framework", "Status"]]
    for item in comp.get("controls", []) if isinstance(comp.get("controls", []), list) else []:
        if not isinstance(item, dict):
            continue
        control_rows.append([
            item.get("control", ""),
            item.get("framework", ""),
            safe_text(item.get("status"), "Gap")
        ])
    if len(control_rows) == 1:
        control_rows.append(["No compliance controls returned", "—", "—"])
    story += [make_table(control_rows, [220, 165, 125]), Spacer(1, 16)]

    story.append(Paragraph("Management Interpretation", heading))
    explanation = data.get("llm_explanation")
    if isinstance(explanation, dict):
        explanation = explanation.get("error") or "LLM explanation was unavailable."
    if not explanation:
        explanation = (
            "The platform translates cybersecurity posture into incident probability, "
            "financial exposure, risk drivers, compliance posture and prioritized security actions. "
            "Results should be validated against organization-specific financial and security data "
            "before production decisions."
        )
    story.append(para(explanation, body))

    story.append(Paragraph("Assumptions & Limitations", heading))
    story.append(para(
        "Financial exposure is an estimate, not guaranteed future loss. Control costs and risk-reduction values are configurable prototype assumptions. Attack probability is a model estimate. Production use requires organization-specific calibration, live integrations and business criticality context.",
        small
    ))

    doc.build(story)
    buf.seek(0)
    return buf
