"""ESG Report PDF generation - detailed investor-grade report"""
import re
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from datetime import datetime
from fpdf import FPDF

from src.api.middleware.auth import require_auth
from src.api.routes.frameworks import FRAMEWORK_OUTPUTS
from src.db.database import fetch_metrics, fetch_trends, fetch_risk_flags


# Dynamic data loaders — replaces old module-level constants
def _get_metrics(org_id: str = ""):
    """Fetch metrics and build display dict matching old METRICS shape."""
    from src.api.routes.dashboard import _build_metric_display
    rows = fetch_metrics(org_id=org_id)
    return {row["cluster"]: _build_metric_display(row) for row in rows}


def _get_trend_data(org_id: str = ""):
    """Fetch trend data grouped by cluster."""
    result = {}
    for cluster in ("energy_kwh", "emissions_tco2", "water_m3"):
        rows = fetch_trends(cluster, org_id=org_id)
        month_names = {
            "2024-09": "Sep 2024", "2024-10": "Oct 2024", "2024-11": "Nov 2024",
            "2024-12": "Dec 2024", "2025-01": "Jan 2025",
        }
        result[cluster] = [
            {"month": month_names.get(r["recorded_at"][:7], r["recorded_at"][:7]), "value": r["value"]}
            for r in rows
        ]
    return result


def _get_alerts(org_id: str = ""):
    """Fetch risk flags as alert-shaped dicts."""
    flags = fetch_risk_flags(org_id=org_id)
    return [
        {
            "id": f["id"],
            "metric_type": f["cluster"],
            "message": f["flag_text"],
            "severity": f["severity"].lower(),
            "triggered_at": f["created_at"],
            "acknowledged": bool(f["acknowledged"]),
            "acknowledged_at": f.get("acknowledged_at"),
            "actual_value": "",
            "threshold": "",
        }
        for f in flags
    ]

router = APIRouter()

# ── Colour palette ──────────────────────────────────────────────────────────────
# Light theme: white backgrounds, dark text
DARK_BG   = (255, 255, 255)   # white (was near-black)
SURFACE   = (245, 245, 245)   # light grey (cards/sections)
SURFACE2  = (238, 238, 238)   # slightly darker grey (alternating rows)
BORDER    = (200, 200, 200)   # border colour
GREEN     = ( 15, 100,  40)   # dark green accent
GREEN_DIM = ( 60, 130,  80)   # medium green
RED       = (180,  30,  30)   # dark red accent
AMBER     = (180, 120,   0)   # dark amber accent
TEXT      = ( 20,  20,  20)   # near-black text (primary)
TEXT_DIM  = (100, 100, 100)   # medium grey (secondary)
WHITE     = (255, 255, 255)   # pure white


def _u(s):
    """Replace non-ASCII chars with safe equivalents for Helvetica."""
    s = s.replace("—", "-")
    s = s.replace("–", "-")
    s = s.replace("²", "2")
    s = s.replace("³", "3")
    s = s.replace("¹", "1")
    s = s.replace("°", "deg")
    s = s.replace("·", "-")
    s = re.sub(r"[\x80-\U0010ffff]", "", s)
    return s


class ESGReportPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*TEXT_DIM)
        self.cell(0, 8,
                  _u("ESG Supply Chain Intelligence  |  Confidential  |  Page ") + str(self.page_no()),
                  align="C")


def build_pdf(org_id: str = ""):
    METRICS = _get_metrics(org_id=org_id)
    TREND_DATA = _get_trend_data(org_id=org_id)
    ALERTS = _get_alerts(org_id=org_id)
    pdf = ESGReportPDF()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()
    _render_cover(pdf, METRICS, ALERTS)
    pdf.add_page()
    _render_metrics_page(pdf, METRICS, TREND_DATA)
    pdf.add_page()
    _render_risk_alerts(pdf, ALERTS)
    pdf.add_page()
    _render_frameworks(pdf, METRICS)
    return bytes(pdf.output())


# ── Cover page ────────────────────────────────────────────────────────────────
def _render_cover(pdf, METRICS, ALERTS):
    # Top accent bar — bright green
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, 210, 6, "F")

    # Dark header block
    pdf.set_fill_color(*DARK_BG)
    pdf.rect(0, 6, 210, 42, "F")

    pdf.set_xy(20, 16)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 10, _u("ESG Supply Chain Intelligence"), ln=True)

    pdf.set_xy(20, 29)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_DIM)
    pdf.cell(0, 6, _u("Bangladesh Export Textiles Ltd.  |  H&M Supplier"), ln=True)

    pdf.ln(14)

    # ── Report identity box ──────────────────────────────────────────────────
    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(20, pdf.get_y(), 170, 30, "FD")

    pdf.set_xy(28, pdf.get_y() + 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, _u("Q1 2025 ESG Performance Report"), ln=True)

    pdf.set_xy(28, pdf.get_y() + 2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_DIM)
    period = "Period: January 2025  |  Prepared for: H&M  |  Generated: " + datetime.utcnow().strftime("%d %B %Y")
    pdf.cell(0, 6, _u(period), ln=True)
    pdf.ln(16)

    # ── Organisation Profile ─────────────────────────────────────────────────
    _section_title(pdf, "Organisation Profile")
    pdf.ln(2)
    _kv(pdf, "Company", "Bangladesh Export Textiles Ltd.")
    _kv(pdf, "Industry", "Garment manufacturing (wet processing)")
    _kv(pdf, "Employees", "3,200")
    _kv(pdf, "Primary Buyer", "H&M")
    _kv(pdf, "Platform Connected Since", "2024-09-15")
    _kv(pdf, "Reporting Frameworks", "CSRD / ESRS E1 / ISSB S2 / GRI / TCFD")
    pdf.ln(10)

    # ── 4 KPI tiles ──────────────────────────────────────────────────────────
    _section_title(pdf, "Key Performance Indicators")
    pdf.ln(4)

    # Pull live values from backend data
    risk_total  = len(ALERTS)
    risk_broken = sum(1 for a in ALERTS if a["severity"] == "warning")
    risk_accent = RED if risk_broken > 0 else (AMBER if risk_total > 3 else GREEN)

    # Build Scope 1+2+3 sum
    s1 = METRICS.get("emissions_tco2", {}).get("value", 0)   # Scope 1+2
    s3a = METRICS.get("scope3_category1", {}).get("value", 0)  # Scope 3 Cat 1
    s3b = METRICS.get("scope3_category6", {}).get("value", 0)  # Scope 3 Cat 6
    total_co2e = s1 + s3a + s3b

    diesel = METRICS.get("diesel_consumed", {})
    diesel_broken = diesel.get("chain_valid", True) is False

    _kpi_card(pdf, 0, "Active Risk Flags",   str(risk_total),   "Avg 12d open",              risk_accent)
    _kpi_card(pdf, 1, "Scope 3 Completeness", "61%",           "48/78 suppliers responded",  GREEN)
    _kpi_card(pdf, 2, "Scope 1+2+3 Emissions", f"{total_co2e:,.1f} tCO2e", "All scopes combined", RED)
    _kpi_card(pdf, 3, "Diesel Chain",
              f"{diesel.get('value', 0):.1f} tCO2e",
              "BROKEN - manual entry" if diesel_broken else "INTACT",
              RED if diesel_broken else GREEN)
    pdf.ln(6)

    # ── Hash chain integrity ─────────────────────────────────────────────────
    pdf.ln(6)
    _section_title(pdf, "Hash Chain Integrity")
    pdf.ln(2)

    all_metrics = list(METRICS.items())
    broken = [k for k, v in all_metrics if v.get("chain_valid", True) is False]
    intact = len(all_metrics) - len(broken)

    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(20, pdf.get_y(), 170, 14, "FD")
    y0 = pdf.get_y() + 3

    if not broken:
        pdf.set_xy(28, y0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*GREEN)
        pdf.cell(50, 6, _u("ALL CHAINS INTACT"), ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 6, _u(f"{intact}/{len(all_metrics)} metrics - no tampering detected"), ln=True)
    else:
        pdf.set_xy(28, y0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*RED)
        pdf.cell(50, 6, _u(f"{len(broken)} CHAIN(S) BROKEN"), ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 6, _u(f"{intact}/{len(all_metrics)} intact - see Metrics page"), ln=True)

    pdf.ln(16)

    # ── Metrics at a glance ──────────────────────────────────────────────────
    _section_title(pdf, "Metrics At A Glance")
    pdf.ln(2)
    _metrics_table_header(pdf)
    for key, m in all_metrics:
        _metrics_table_row(pdf, key, m)

    pdf.ln(8)

    # ── Evidence note ────────────────────────────────────────────────────────
    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(20, pdf.get_y(), 170, 16, "FD")
    y0 = pdf.get_y() + 3
    pdf.set_xy(28, y0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 5, _u("Tamper-Evident Hash Chain"), ln=True)
    pdf.set_xy(28, y0 + 5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*TEXT_DIM)
    pdf.multi_cell(154, 4.5, _u(
        "Every record carries a SHA-256 hash incorporating the previous record's hash, "
        "creating a tamper-evident ledger.  Source: SAP Business One  |  "
        "Calculation: IEA 2023 / GHG Protocol 2022 Emission Factors"
    ), ln=True)


# ── Metrics page ──────────────────────────────────────────────────────────────
def _render_metrics_page(pdf, METRICS, TREND_DATA):
    diesel = METRICS.get("diesel_consumed", {})
    _page_header(pdf, "Metrics Detail", "Page 2 of 4")

    # Priority metrics table
    _section_title(pdf, "Priority Metrics — Scope Reference")
    pdf.ln(3)

    headers = ["#", "Metric", "Value", "Scope", "Confidence", "Method", "Chain"]
    widths  = [8, 52, 32, 22, 22, 26, 8]
    _row_header(pdf, headers, widths)
    pdf.ln(1)

    scope_map = {
        "energy_kwh":       "Scope 2",
        "emissions_tco2":   "Scope 1+2",
        "water_m3":         "Environmental",
        "scope3_category1": "Scope 3 Cat 1",
        "diesel_consumed":  "Scope 1",
    }
    labels_map = {
        "energy_kwh":       "Electricity",
        "emissions_tco2":   "Total Emissions",
        "water_m3":         "Water Withdrawal",
        "scope3_category1": "Purchased Goods",
        "diesel_consumed":  "Diesel Combustion",
    }
    display_order = ["energy_kwh", "emissions_tco2", "water_m3", "scope3_category1", "diesel_consumed"]

    for i, key in enumerate(display_order, 1):
        m = METRICS.get(key)
        if not m:
            continue
        row = [
            str(i),
            labels_map.get(key, key),
            f"{m['value']:,} {m.get('unit', '')}",
            scope_map.get(key, "—"),
            m.get("confidence", "—"),
            m.get("calculation_method", "—").replace("_", " ").title(),
            "OK" if m.get("chain_valid", True) else "BROKEN",
        ]
        _data_row(pdf, row, widths, fill=(i % 2 == 0), chain_broken=not m.get("chain_valid", True))
        pdf.ln(0.5)

    pdf.ln(8)

    # 5-month trends
    _section_title(pdf, "5-Month Trend Data (Sep 2024 — Jan 2025)")
    pdf.ln(2)

    months = ["Sep '24", "Oct '24", "Nov '24", "Dec '24", "Jan '25"]
    trend_keys = [
        ("energy_kwh",     "Electricity (kWh)",  "kWh"),
        ("emissions_tco2", "Emissions (tCO2e)",  "tCO2e"),
        ("water_m3",       "Water (m3)",         "m3"),
    ]
    col_w = 170.0 / (len(months) + 1)
    row_h = 7

    # Header row
    pdf.set_fill_color(*SURFACE)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*TEXT_DIM)
    x = 20
    pdf.set_xy(x, pdf.get_y())
    pdf.cell(col_w, row_h, _u("Metric"), border=1, fill=True, align="C")
    x += col_w
    for m in months:
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(col_w, row_h, _u(m), border=1, fill=True, align="C")
        x += col_w
    pdf.ln(row_h)

    for metric_key, label, unit in trend_keys:
        vals = [t["value"] for t in TREND_DATA.get(metric_key, [])]
        pdf.set_fill_color(*SURFACE)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(col_w, row_h, _u(label), border=1, fill=True)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*TEXT)
        for v in vals:
            if unit == "kWh":
                display = f"{v / 1000:.0f}K"
            elif unit == "tCO2e":
                display = f"{v:.1f}"
            else:
                display = f"{v:.0f}"
            pdf.cell(col_w, row_h, display, border=1, align="C")
        pdf.ln(row_h)

    pdf.ln(10)

    # GHG Protocol Scope summary
    _section_title(pdf, "GHG Protocol Scope Summary")
    pdf.ln(2)

    scope_data = [
        ("Scope 1 — Direct Emissions",     f"{diesel.get('value', 0):.1f} tCO2e",  "Diesel combustion",         RED),
        ("Scope 2 — Indirect (Electricity)", f"{METRICS.get('emissions_tco2',{}).get('value',0):.1f} tCO2e", "Purchased electricity", AMBER),
        ("Scope 3 — Value Chain",          f"{(METRICS.get('scope3_category1',{}).get('value',0)+METRICS.get('scope3_category6',{}).get('value',0)):.1f} tCO2e", "Purchased goods + travel", AMBER),
    ]
    for label, value, note, color in scope_data:
        pdf.set_fill_color(*SURFACE)
        pdf.set_draw_color(*BORDER)
        pdf.rect(20, pdf.get_y(), 170, 12, "FD")
        y0 = pdf.get_y() + 3
        pdf.set_xy(24, y0)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color)
        pdf.cell(52, 5, _u(label), ln=False)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.cell(38, 5, _u(value), ln=False)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 5, _u(f"({note})"), ln=True)
        pdf.ln(4)

    # Chain alert
    if any(not v.get("chain_valid", True) for v in METRICS.values()):
        pdf.ln(6)
        _section_title(pdf, "Chain Integrity Alert", color=RED)
        pdf.ln(2)
        pdf.set_fill_color(*SURFACE)
        pdf.set_draw_color(*RED)
        pdf.rect(20, pdf.get_y(), 170, 26, "FD")
        y0 = pdf.get_y() + 4

        pdf.set_xy(28, y0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*RED)
        pdf.cell(0, 6, _u("MANUAL ENTRY: CHAIN INTEGRITY COMPROMISED"), ln=True)

        pdf.set_xy(28, y0 + 5)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*TEXT_DIM)
        pdf.multi_cell(154, 5, _u(
            "The Diesel Consumed (Scope 1) metric has a broken hash chain. "
            "This is a deliberate demo state showing what happens when manual entry data "
            "is altered after submission. In production, this alert fires immediately "
            "and the record is quarantined pending re-verification."
        ), ln=True)

        pdf.set_xy(28, y0 + 14)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 5, _u("Stored hash: TAMPERED_f8a7...  |  Expected: e7f6d4c2b1a0..."), ln=True)


# ── Risk alerts page ──────────────────────────────────────────────────────────
def _render_risk_alerts(pdf, ALERTS):
    _page_header(pdf, "Risk Alerts", "Page 3 of 4")

    if not ALERTS:
        pdf.set_fill_color(*SURFACE)
        pdf.rect(20, pdf.get_y(), 170, 18, "F")
        pdf.set_xy(28, pdf.get_y() + 6)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 6, _u("No active alerts."), ln=True)
        return

    _section_title(pdf, f"Active Alerts ({len(ALERTS)})")
    pdf.ln(3)

    for alert in ALERTS:
        sev  = RED   if alert["severity"] == "warning" else AMBER
        bg   = SURFACE

        pdf.set_fill_color(*bg)
        pdf.set_draw_color(*sev)
        pdf.set_line_width(0.8)
        pdf.rect(20, pdf.get_y(), 170, 22, "FD")
        y0 = pdf.get_y() + 3

        pdf.set_xy(28, y0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*sev)
        pdf.cell(0, 5, _u(f"[{alert['severity'].upper()}]  {alert['metric_type'].replace('_', ' ').title()}"), ln=True)

        pdf.set_xy(28, y0 + 5)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT)
        pdf.cell(0, 4.5, _u(alert["message"]), ln=True)

        pdf.set_xy(28, y0 + 9.5)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 4.5, _u(
            f"Actual: {alert.get('actual_value','—')}  |  "
            f"Threshold: {alert.get('threshold','—')}  |  "
            f"Triggered: {alert.get('triggered_at','—')[:10]}"
        ), ln=True)
        pdf.ln(8)

    pdf.ln(4)
    _section_title(pdf, "Risk Summary")
    pdf.ln(2)
    _kv(pdf, "Total Open Risks", str(len(ALERTS)))
    _kv(pdf, "Critical / Warnings", str(sum(1 for a in ALERTS if a["severity"] == "warning")))
    _kv(pdf, "Informational", str(sum(1 for a in ALERTS if a["severity"] != "warning")))
    _kv(pdf, "Acknowledged", str(sum(1 for a in ALERTS if a.get("acknowledged"))))

    pdf.ln(8)
    _section_title(pdf, "Scope 3 Completeness")
    pdf.ln(2)
    _kv(pdf, "Respondents", "48 / 78 suppliers")
    _kv(pdf, "Coverage", "61%")
    _kv(pdf, "Outstanding", "30 suppliers — questionnaires pending")


# ── Framework compliance page ──────────────────────────────────────────────────
def _render_frameworks(pdf, METRICS):
    _page_header(pdf, "Framework Compliance", "Page 4 of 4")

    _section_title(pdf, "CSRD / ESRS E1 — Energy & Emissions")
    pdf.ln(3)

    fw_blocks = [
        ("energy_kwh",       "Electricity Consumption",         "energy_kwh",       GREEN),
        ("scope3_cat1_4281","Scope 3 Cat 1 — Purchased Goods","scope3_category1", GREEN),
        ("diesel_consumed", "Diesel Combustion — Scope 1",   "diesel_consumed",  AMBER),
    ]
    for fw_key, label, metric_key, color in fw_blocks:
        _framework_block(pdf, fw_key, label, metric_key, color, METRICS)
        pdf.ln(4)

    pdf.ln(8)

    # Evidence & integrity
    _section_title(pdf, "Evidence & Integrity")
    pdf.ln(2)
    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(20, pdf.get_y(), 170, 22, "FD")
    y0 = pdf.get_y() + 4

    pdf.set_xy(28, y0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 5, _u("Every metric carries a SHA-256 hash chain."), ln=True)
    pdf.set_xy(28, y0 + 5)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DIM)
    pdf.multi_cell(154, 4.5, _u(
        "The hash chain proves no post-submission tampering. Each record's hash incorporates "
        "the previous record's hash, creating a tamper-evident ledger. "
        "Diesel Consumed shows a broken chain — this is a deliberate demo state."
    ), ln=True)

    pdf.set_xy(28, pdf.get_y() + 1)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*TEXT_DIM)
    pdf.cell(0, 5, _u(
        "Source: SAP Business One  |  Calculation: IEA 2023 Emission Factors  |  "
        "Frameworks: CSRD, ISSB, GRI, TCFD"
    ), ln=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _page_header(pdf, title, subtitle=""):
    pdf.set_fill_color(*DARK_BG)
    pdf.rect(0, 0, 210, 20, "F")
    pdf.set_xy(20, 6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*GREEN)
    pdf.cell(100, 8, _u(title), ln=False)
    if subtitle:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*TEXT_DIM)
        pdf.cell(0, 8, _u(subtitle), align="R", ln=True)
    pdf.ln(8)


def _section_title(pdf, text, color=None):
    if color is None:
        color = GREEN
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*color)
    pdf.cell(0, 6, _u(text.upper()), ln=True)
    pdf.set_draw_color(*color)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)


def _kv(pdf, key, value):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_DIM)
    pdf.cell(52, 5, _u(key + ":"), ln=False)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 5, _u(value), ln=True)


def _kpi_card(pdf, i, label, value, sub, color):
    """Draw a single KPI card at position i (0-based)."""
    w  = 170.0 / 4
    cx = 20 + i * w          # left edge of this card
    cy = pdf.get_y()         # current y (top of card)
    card_h = 30

    # Card background with coloured left accent strip
    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*color)
    pdf.set_line_width(0)
    pdf.rect(cx, cy, w - 2, card_h, "FD")

    # Left accent strip
    pdf.set_fill_color(*color)
    pdf.rect(cx, cy, 4, card_h, "F")

    # Label
    tx = cx + 7
    pdf.set_xy(tx, cy + 4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*TEXT_DIM)
    pdf.cell(w - 10, 4, _u(label), align="L", ln=False)

    # Value
    pdf.set_x(tx)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*color)
    pdf.cell(w - 10, 7, _u(value), align="L", ln=False)

    # Sub
    pdf.set_x(tx)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*TEXT_DIM)
    pdf.cell(w - 10, 4, _u(sub), align="L", ln=True)


def _metrics_table_header(pdf):
    cols    = [("Metric", 44), ("Value", 32), ("Confidence", 22), ("Method", 38), ("Chain", 20)]
    x_start = 20
    pdf.set_fill_color(*SURFACE)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*TEXT_DIM)
    x = x_start
    for label, w in cols:
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(w, 6, _u(label), border=1, fill=True, align="C")
        x += w
    pdf.ln(6)


def _metrics_table_row(pdf, key, m):
    labels = {
        "energy_kwh":       "Electricity (Scope 2)",
        "emissions_tco2":   "Total Emissions (Scope 1+2)",
        "water_m3":         "Water Withdrawal",
        "scope3_category1": "Purchased Goods (Scope 3)",
        "diesel_consumed":  "Diesel Combustion (Scope 1)",
        "scope3_category6": "Business Travel (Scope 3)",
    }
    conf_colors = {"HIGH": GREEN, "MEDIUM": AMBER, "LOW": RED}
    chain_ok = m.get("chain_valid", True)
    conf_color = conf_colors.get(m.get("confidence", "MEDIUM"), TEXT_DIM)

    value_str  = f"{m['value']:,} {m.get('unit', '')}"
    method_str = m.get("calculation_method", "-").replace("_", " ").title()
    chain_str  = "INTACT" if chain_ok else "BROKEN"
    conf_str   = m.get("confidence", "—")

    cols = [
        (labels.get(key, key), 44),
        (value_str,            32),
        (conf_str,             22),
        (method_str,           38),
        (chain_str,            20),
    ]
    x = 20
    fill = True
    for i, (val, w) in enumerate(cols):
        pdf.set_xy(x, pdf.get_y())
        if i == 4:  # chain
            txt_color = GREEN if chain_ok else RED
            pdf.set_font("Helvetica", "B", 8)
        elif i == 2:  # confidence
            txt_color = conf_color
            pdf.set_font("Helvetica", "B", 8)
        elif i == 1:  # value
            txt_color = TEXT
            pdf.set_font("Helvetica", "B", 8)
        elif i == 0:  # label
            txt_color = TEXT_DIM
            pdf.set_font("Helvetica", "", 8)
        else:
            txt_color = TEXT
            pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*txt_color)
        pdf.cell(w, 6, _u(str(val)), border=1, fill=fill, align="C")
        x += w
    pdf.ln(6)


def _row_header(pdf, headers, widths):
    x = 20
    pdf.set_fill_color(*SURFACE)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*TEXT_DIM)
    for h, w in zip(headers, widths):
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(w, 6, _u(h), border=1, fill=True, align="C")
        x += w
    pdf.ln(6)


def _data_row(pdf, row, widths, fill=False, chain_broken=False):
    x = 20
    for i, (val, w) in enumerate(zip(row, widths)):
        pdf.set_xy(x, pdf.get_y())
        if i == 0:
            txt_color = TEXT_DIM
            pdf.set_font("Helvetica", "B", 8)
        elif i == 4:  # confidence
            conf_map = {"HIGH": GREEN, "MEDIUM": AMBER, "LOW": RED}
            txt_color = conf_map.get(val, TEXT)
            pdf.set_font("Helvetica", "B", 8)
        elif i == 6:  # chain
            txt_color = RED if chain_broken else GREEN
            pdf.set_font("Helvetica", "B", 8)
        else:
            txt_color = TEXT if i > 1 else TEXT_DIM
            pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*txt_color)
        pdf.cell(w, 6, _u(str(val)), border=1, fill=fill, align="C")
        x += w
    pdf.ln(6)


def _framework_block(pdf, fw_key, metric_label, metric_key, accent_color, METRICS):
    fw_data = FRAMEWORK_OUTPUTS.get(fw_key, {})
    metric   = METRICS.get(metric_key, {})

    pdf.set_fill_color(*SURFACE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(20, pdf.get_y(), 170, 36, "FD")

    y0 = pdf.get_y() + 3
    # Left accent bar
    pdf.set_fill_color(*accent_color)
    pdf.rect(20, y0, 3, 30, "F")

    # Metric label
    pdf.set_xy(26, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 6, _u(metric_label), ln=True)

    # Value
    if metric:
        pdf.set_xy(26, y0 + 6)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*accent_color)
        pdf.cell(0, 7, _u(f"{metric['value']:,} {metric.get('unit', '')}"), ln=True)

    # Framework tags
    fw_names = {
        "csrd_esrs_e1": "CSRD / ESRS E1",
        "issb_ifrs_s2":  "ISSB / IFRS S2",
        "gri_302_1":    "GRI 302-1",
        "gri_305_1":    "GRI 305-1",
        "gri_305_3":    "GRI 305-3",
        "tcfd_metrics": "TCFD",
    }
    y = pdf.get_y() + 1
    for fw_k, fw_info in fw_data.items():
        fw_name = fw_names.get(fw_k, fw_k)
        pdf.set_xy(26, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*accent_color)
        pdf.cell(40, 4, _u(fw_name), ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT)
        fid = fw_info.get("field_id", "")
        val = fw_info.get("value", "")
        pdf.cell(0, 4, _u(f"{fid} — {val}"), ln=True)
        y += 5

    pdf.ln(6)


@router.get("/esg-pdf")
def esg_report(user: dict = Depends(require_auth)):
    """Stream a 4-page detailed ESG PDF report scoped to the user's org."""
    org_id = user["org_id"]
    pdf_bytes = build_pdf(org_id=org_id)
    filename = f"ESG-Report-{org_id}-{datetime.now().strftime('%Y-Q%q')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Length": str(len(pdf_bytes)),
        },
    )
