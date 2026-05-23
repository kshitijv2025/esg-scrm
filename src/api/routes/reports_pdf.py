"""PDF Compliance Report generator for ESG SCRM platform."""

import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fpdf import fpdf
from starlette.responses import StreamingResponse

from src.api.middleware.auth import require_auth
from src.db.database import get_connection, release_connection, _fetchall, _fetchone


router = APIRouter()

# Page dimensions and layout constants
_PAGE_W = 210  # A4 width in mm
_PAGE_H = 297  # A4 height in mm
_MARGIN_L = 20
_MARGIN_R = 20
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R

# Colour palette
_GREEN = (15, 100, 40)
_GREEN_DIM = (60, 130, 80)
_RED = (180, 30, 30)
_AMBER = (180, 120, 0)
_TEXT = (20, 20, 20)
_TEXT_DIM = (100, 100, 100)
_WHITE = (255, 255, 255)
_SURFACE = (245, 245, 245)
_BORDER = (200, 200, 200)


def _safe(s: str) -> str:
    """Replace non-ASCII characters for Helvetica compatibility."""
    replacements = {
        "—": "-",
        "–": "-",
        "²": "2",
        "³": "3",
        "¹": "1",
        "°": "deg",
        "·": "-",
    }
    for char, replacement in replacements.items():
        s = s.replace(char, replacement)
    # Strip any remaining non-latin1 characters
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _CompliancePDF(fpdf.FPDF):
    """Custom PDF class with header/footer for compliance reports."""

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_TEXT_DIM)
        self.cell(
            0,
            8,
            _safe(
                "Bangladesh Export Textiles Ltd.  |  ESG Compliance Report  |  Page "
                + str(self.page_no())
            ),
            align="C",
        )


def _section_heading(pdf: fpdf.FPDF, title: str, color: tuple = _GREEN) -> None:
    """Draw a section heading with underline."""
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*color)
    pdf.cell(0, 8, _safe(title.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*color)
    pdf.set_line_width(0.5)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(4)


def _kvp(pdf: fpdf.FPDF, key: str, value: str) -> None:
    """Draw a key-value pair line."""
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_TEXT_DIM)
    pdf.cell(60, 6, _safe(key + ":"), new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_TEXT)
    pdf.cell(0, 6, _safe(value), new_x="LMARGIN", new_y="NEXT")


def _table_header(pdf: fpdf.FPDF, columns: list[tuple[str, float]]) -> None:
    """Draw a table header row with column names and widths."""
    pdf.set_fill_color(*_SURFACE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_TEXT_DIM)
    for label, width in columns:
        pdf.cell(width, 7, _safe(label), border=1, fill=True, align="C")
    pdf.ln(7)


def _table_row(
    pdf: fpdf.FPDF,
    cells: list[tuple[str, float]],
    fill: bool = False,
) -> None:
    """Draw a table data row."""
    if fill:
        pdf.set_fill_color(*_SURFACE)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_TEXT)
    for value, width in cells:
        pdf.cell(width, 6, _safe(str(value)), border=1, fill=fill, align="C")
    pdf.ln(6)


# ---------------------------------------------------------------------------
# Data-fetching helpers
# ---------------------------------------------------------------------------

_METRIC_CLUSTERS = [
    "energy_kwh",
    "emissions_tco2",
    "water_m3",
    "scope3_category1",
    "diesel_consumed",
    "scope3_category6",
]

_METRIC_LABELS = {
    "energy_kwh": "Electricity Consumption (Scope 2)",
    "emissions_tco2": "Total Emissions (Scope 1+2)",
    "water_m3": "Water Withdrawal",
    "scope3_category1": "Purchased Goods (Scope 3 Cat 1)",
    "diesel_consumed": "Diesel Combustion (Scope 1)",
    "scope3_category6": "Business Travel (Scope 3 Cat 6)",
}


def _fetch_latest_metrics(org_id: str = "") -> list[dict]:
    """Retrieve the latest metric per cluster, scoped to org_id."""
    conn = get_connection()
    try:
        rows = []
        for cluster in _METRIC_CLUSTERS:
            try:
                if org_id:
                    row = _fetchone(
                        conn,
                        "SELECT m.value, m.unit, m.confidence, m.source, m.period, m.recorded_at "
                        "FROM metrics m JOIN factories f ON m.factory_id = f.id "
                        "WHERE f.org_id = ? AND m.cluster = ? "
                        "ORDER BY m.recorded_at DESC LIMIT 1",
                        (org_id, cluster),
                    )
                else:
                    row = _fetchone(
                        conn,
                        "SELECT value, unit, confidence, source, period, recorded_at "
                        "FROM metrics WHERE cluster = ? ORDER BY recorded_at DESC LIMIT 1",
                        (cluster,),
                    )
            except Exception:
                # Fallback if factories table doesn't exist (e.g., test DB)
                row = _fetchone(
                    conn,
                    "SELECT value, unit, confidence, source, period, recorded_at "
                    "FROM metrics WHERE cluster = ? ORDER BY recorded_at DESC LIMIT 1",
                    (cluster,),
                )
            if row:
                row["cluster"] = cluster
                row["label"] = _METRIC_LABELS.get(cluster, cluster)
                rows.append(row)
        return rows
    finally:
        release_connection(conn)


_SEVERITY_ORDER = (
    "CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 WHEN 'INFO' THEN 3 ELSE 4 END"
)


def _fetch_risk_flags_ordered(org_id: str = "") -> list[dict]:
    """Retrieve risk flags sorted by severity (CRITICAL first), scoped to org_id."""
    conn = get_connection()
    try:
        if org_id:
            return _fetchall(
                conn,
                "SELECT id, flag_text, cluster, severity, days_overdue, priority_score, "
                "created_at, acknowledged "
                "FROM risk_flags WHERE org_id = ? "
                f"ORDER BY {_SEVERITY_ORDER} ASC, priority_score DESC",
                (org_id,),
            )
        return _fetchall(
            conn,
            "SELECT id, flag_text, cluster, severity, days_overdue, priority_score, "
            "created_at, acknowledged "
            f"FROM risk_flags ORDER BY {_SEVERITY_ORDER} ASC, priority_score DESC",
        )
    finally:
        release_connection(conn)


def _fetch_framework_mappings(framework: str = "") -> list[dict]:
    """Retrieve framework mappings (reference data, shared across orgs)."""
    conn = get_connection()
    try:
        if framework:
            return _fetchall(
                conn,
                "SELECT cluster, metric_name, framework, disclosure_code, description "
                "FROM framework_mappings WHERE framework = ? "
                "ORDER BY cluster, disclosure_code",
                (framework.lower(),),
            )
        return _fetchall(
            conn,
            "SELECT cluster, metric_name, framework, disclosure_code, description "
            "FROM framework_mappings ORDER BY framework, cluster, disclosure_code",
        )
    finally:
        release_connection(conn)


def _fetch_supplier_summary(org_id: str = "") -> dict:
    """Return supplier stats scoped to org_id."""
    conn = get_connection()
    try:
        params = (org_id,) if org_id else ()

        if org_id:
            total_row = _fetchone(
                conn, "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ?", params
            )
            tier_a = _fetchone(
                conn,
                "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ? AND risk_tier = 'A'",
                params,
            )
            tier_b = _fetchone(
                conn,
                "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ? AND risk_tier = 'B'",
                params,
            )
            tier_c = _fetchone(
                conn,
                "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ? AND risk_tier = 'C'",
                params,
            )
            responded = _fetchone(
                conn,
                "SELECT COUNT(*) as cnt FROM suppliers "
                "WHERE org_id = ? AND questionnaire_status = 'responded'",
                params,
            )
        else:
            total_row = _fetchone(conn, "SELECT COUNT(*) as cnt FROM suppliers")
            tier_a = _fetchone(conn, "SELECT COUNT(*) as cnt FROM suppliers WHERE risk_tier = 'A'")
            tier_b = _fetchone(conn, "SELECT COUNT(*) as cnt FROM suppliers WHERE risk_tier = 'B'")
            tier_c = _fetchone(conn, "SELECT COUNT(*) as cnt FROM suppliers WHERE risk_tier = 'C'")
            responded = _fetchone(
                conn,
                "SELECT COUNT(*) as cnt FROM suppliers WHERE questionnaire_status = 'responded'",
            )

        total = total_row["cnt"] if total_row else 0
        response_count = responded["cnt"] if responded else 0

        return {
            "total": total,
            "tier_a": tier_a["cnt"] if tier_a else 0,
            "tier_b": tier_b["cnt"] if tier_b else 0,
            "tier_c": tier_c["cnt"] if tier_c else 0,
            "response_count": response_count,
            "response_rate": round(response_count / total * 100) if total else 0,
        }
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# PDF section renderers
# ---------------------------------------------------------------------------


def _render_cover_page(pdf: fpdf.FPDF) -> None:
    """Cover page with company name, report title, date, and reporting period."""
    # Green accent bar at top
    pdf.set_fill_color(*_GREEN)
    pdf.rect(0, 0, _PAGE_W, 6, "F")

    pdf.ln(30)

    # Company name
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*_TEXT)
    pdf.cell(0, 12, _safe("Bangladesh Export Textiles Ltd."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Report title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_GREEN)
    pdf.cell(0, 10, _safe("ESG Compliance Report"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Report identity box
    pdf.set_fill_color(*_SURFACE)
    pdf.set_draw_color(*_BORDER)
    box_y = pdf.get_y()
    pdf.rect(_MARGIN_L, box_y, _CONTENT_W, 28, "FD")

    pdf.set_xy(_MARGIN_L + 8, box_y + 5)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_TEXT)
    pdf.cell(
        0,
        7,
        _safe("Report Date: " + datetime.utcnow().strftime("%d %B %Y")),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_xy(_MARGIN_L + 8, box_y + 13)
    pdf.set_text_color(*_TEXT_DIM)
    pdf.cell(
        0,
        7,
        _safe("Reporting Period: September 2024 - January 2025"),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_xy(_MARGIN_L + 8, box_y + 21)
    pdf.set_text_color(*_TEXT_DIM)
    pdf.cell(0, 7, _safe("Prepared for: H&M Group"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)

    # Company profile section
    _section_heading(pdf, "Company Profile")
    _kvp(pdf, "Company", "Bangladesh Export Textiles Ltd.")
    _kvp(pdf, "Industry", "Garment Manufacturing (Wet Processing)")
    _kvp(pdf, "Employees", "3,200")
    _kvp(pdf, "Primary Buyer", "H&M")
    _kvp(pdf, "Reporting Frameworks", "GRI / TCFD / CSRD / ISSB")
    _kvp(pdf, "Platform Connected Since", "September 2024")


def _render_executive_summary(pdf: fpdf.FPDF, metrics: list[dict], risk_flags: list[dict]) -> None:
    """Executive summary with key totals and active risk flag count."""
    _section_heading(pdf, "Executive Summary")
    pdf.ln(2)

    # Build summary values from metrics
    total_emissions = 0.0
    energy_kwh = 0.0
    water_m3 = 0.0
    for m in metrics:
        val = m.get("value", 0) or 0
        cluster = m.get("cluster", "")
        if "emissions" in cluster or "scope3" in cluster or "diesel" in cluster:
            total_emissions += val
        if cluster == "energy_kwh":
            energy_kwh = val
        if cluster == "water_m3":
            water_m3 = val

    active_flags = len(risk_flags)
    critical_count = sum(1 for f in risk_flags if f.get("severity") == "CRITICAL")

    # Summary cards
    pdf.set_fill_color(*_SURFACE)
    pdf.set_draw_color(*_BORDER)

    summaries = [
        ("Total Emissions", f"{total_emissions:,.1f} tCO2e"),
        ("Energy Consumption", f"{energy_kwh:,.0f} kWh"),
        ("Water Usage", f"{water_m3:,.0f} m3"),
        ("Active Risk Flags", f"{active_flags} ({critical_count} Critical)"),
    ]

    card_h = 20
    start_y = pdf.get_y()
    for i, (label, value) in enumerate(summaries):
        col = i % 2
        row = i // 2
        cx = _MARGIN_L + col * (_CONTENT_W / 2 + 2)
        cy = start_y + row * (card_h + 4)
        cw = _CONTENT_W / 2 - 2

        pdf.set_fill_color(*_SURFACE)
        pdf.rect(cx, cy, cw, card_h, "FD")

        # Left accent
        pdf.set_fill_color(*_GREEN)
        pdf.rect(cx, cy, 3, card_h, "F")

        pdf.set_xy(cx + 6, cy + 3)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_TEXT_DIM)
        pdf.cell(cw - 10, 5, _safe(label), new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(cx + 6, cy + 9)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_GREEN)
        pdf.cell(cw - 10, 7, _safe(value), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(start_y + 2 * (card_h + 4) + 4)


def _render_environmental_table(pdf: fpdf.FPDF, metrics: list[dict]) -> None:
    """Environmental performance table with value, unit, confidence, source."""
    _section_heading(pdf, "Environmental Performance")
    pdf.ln(2)

    columns = [
        ("Metric", 56),
        ("Value", 30),
        ("Unit", 20),
        ("Confidence", 24),
        ("Source", 40),
    ]
    _table_header(pdf, columns)

    for i, m in enumerate(metrics):
        value_str = f"{m.get('value', 0):,.1f}" if m.get("value") is not None else "-"
        cells = [
            (m.get("label", m.get("cluster", "-")), columns[0][1]),
            (value_str, columns[1][1]),
            (m.get("unit", "-"), columns[2][1]),
            (m.get("confidence", "-"), columns[3][1]),
            (m.get("source", "-"), columns[4][1]),
        ]
        _table_row(pdf, cells, fill=(i % 2 == 0))


def _render_risk_flags(pdf: fpdf.FPDF, risk_flags: list[dict]) -> None:
    """Risk flags summary listed by severity, CRITICAL first."""
    _section_heading(pdf, "Risk Flags Summary")
    pdf.ln(2)

    if not risk_flags:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_TEXT_DIM)
        pdf.cell(0, 8, _safe("No active risk flags."), new_x="LMARGIN", new_y="NEXT")
        return

    severity_colors = {
        "CRITICAL": _RED,
        "WARNING": _AMBER,
        "INFO": _GREEN_DIM,
    }

    for flag in risk_flags:
        severity = flag.get("severity", "INFO")
        color = severity_colors.get(severity, _TEXT)

        # Flag card
        card_h = 16
        pdf.set_fill_color(*_SURFACE)
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.8)
        pdf.rect(_MARGIN_L, pdf.get_y(), _CONTENT_W, card_h, "FD")
        y0 = pdf.get_y()

        # Left accent strip
        pdf.set_fill_color(*color)
        pdf.rect(_MARGIN_L, y0, 3, card_h, "F")

        # Severity label and cluster
        pdf.set_xy(_MARGIN_L + 6, y0 + 2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*color)
        cluster_display = flag.get("cluster", "").replace("_", " ").title()
        pdf.cell(
            0,
            5,
            _safe(f"[{severity}]  {cluster_display}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Flag text
        pdf.set_xy(_MARGIN_L + 6, y0 + 7)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_TEXT)
        pdf.cell(
            0,
            4,
            _safe(flag.get("flag_text", "")),
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Created date
        pdf.set_xy(_MARGIN_L + 6, y0 + 11)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(*_TEXT_DIM)
        created = flag.get("created_at", "")
        pdf.cell(
            0,
            4,
            _safe(
                f"Created: {created[:10] if created else '-'}  |  "
                f"Acknowledged: {'Yes' if flag.get('acknowledged') else 'No'}"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.set_y(y0 + card_h + 3)

    # Summary line
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_TEXT)
    total = len(risk_flags)
    critical = sum(1 for f in risk_flags if f.get("severity") == "CRITICAL")
    warning = sum(1 for f in risk_flags if f.get("severity") == "WARNING")
    info = sum(1 for f in risk_flags if f.get("severity") == "INFO")
    pdf.cell(
        0,
        6,
        _safe(f"Total: {total}  |  Critical: {critical}  |  Warning: {warning}  |  Info: {info}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _render_framework_mapping(pdf: fpdf.FPDF, mappings: list[dict], framework: str = "") -> None:
    """Framework mapping section showing disclosure codes and descriptions."""
    title = (
        f"Framework Mapping: {framework.upper()}"
        if framework
        else "Framework Mapping (All Frameworks)"
    )
    _section_heading(pdf, title)
    pdf.ln(2)

    if not mappings:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_TEXT_DIM)
        pdf.cell(
            0,
            8,
            _safe(f"No mappings found{(' for ' + framework) if framework else ''}."),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        return

    # Group by framework for display
    current_framework = ""
    for mapping in mappings:
        fw = mapping.get("framework", "").upper()
        if fw != current_framework:
            if current_framework:
                pdf.ln(3)
            current_framework = fw
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_GREEN)
            pdf.cell(0, 6, _safe(fw), new_x="LMARGIN", new_y="NEXT")

        # Disclosure row
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_TEXT)
        code = mapping.get("disclosure_code", "")
        pdf.cell(30, 5, _safe(code), new_x="RIGHT", new_y="TOP")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT_DIM)
        kpi = mapping.get("metric_name", "")
        desc = mapping.get("description", "")
        label = f"{kpi}" + (f" - {desc}" if desc else "")
        pdf.cell(0, 5, _safe(label), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)


def _render_supplier_summary(pdf: fpdf.FPDF, summary: dict) -> None:
    """Supplier summary: totals, risk distribution, response rate."""
    _section_heading(pdf, "Supplier Summary")
    pdf.ln(2)

    _kvp(pdf, "Total Suppliers", str(summary["total"]))
    _kvp(pdf, "Risk Tier A (Low)", str(summary["tier_a"]))
    _kvp(pdf, "Risk Tier B (Medium)", str(summary["tier_b"]))
    _kvp(pdf, "Risk Tier C (High)", str(summary["tier_c"]))
    _kvp(pdf, "Questionnaire Responses", str(summary["response_count"]))
    _kvp(pdf, "Response Rate", f"{summary['response_rate']}%")

    pdf.ln(4)

    # Risk distribution bar
    total = summary["total"]
    if total > 0:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_TEXT_DIM)
        pdf.cell(0, 5, _safe("Risk Tier Distribution:"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        bar_y = pdf.get_y()
        bar_h = 8
        tier_a_w = _CONTENT_W * (summary["tier_a"] / total)
        tier_b_w = _CONTENT_W * (summary["tier_b"] / total)
        tier_c_w = _CONTENT_W * (summary["tier_c"] / total)

        pdf.set_fill_color(*_GREEN)
        pdf.rect(_MARGIN_L, bar_y, tier_a_w, bar_h, "F")
        pdf.set_fill_color(*_AMBER)
        pdf.rect(_MARGIN_L + tier_a_w, bar_y, tier_b_w, bar_h, "F")
        pdf.set_fill_color(*_RED)
        pdf.rect(_MARGIN_L + tier_a_w + tier_b_w, bar_y, tier_c_w, bar_h, "F")

        pdf.set_y(bar_y + bar_h + 3)

        # Legend
        pdf.set_font("Helvetica", "", 7)
        for label, color in [("A - Low", _GREEN), ("B - Medium", _AMBER), ("C - High", _RED)]:
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color(*color)
            pdf.rect(x, y + 1, 3, 3, "F")
            pdf.set_xy(x + 4, y)
            pdf.set_text_color(*_TEXT_DIM)
            pdf.cell(25, 5, _safe(label), new_x="RIGHT", new_y="TOP")


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------

_VALID_FRAMEWORKS = {"gri", "tcfd", "csrd", "issb"}


@router.get("/compliance-report")
def generate_compliance_report(
    framework: str = Query(default=""),
    period: str = Query(default=""),
    user: dict = Depends(require_auth),
):
    """Generate and return a downloadable PDF compliance report."""
    if framework and framework.lower() not in _VALID_FRAMEWORKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework '{framework}'. "
            f"Must be one of: {', '.join(sorted(_VALID_FRAMEWORKS))}",
        )
    if period:
        import re

        date_pattern = r"^\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, period):
            raise HTTPException(
                status_code=400,
                detail="period must match format YYYY-MM-DD_YYYY-MM-DD",
            )
        start_str, end_str = period.split("_")
        try:
            _start_year, start_month, start_day = (
                int(start_str[:4]),
                int(start_str[5:7]),
                int(start_str[8:10]),
            )
            _end_year, end_month, end_day = (
                int(end_str[:4]),
                int(end_str[5:7]),
                int(end_str[8:10]),
            )
            if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
                raise ValueError("Invalid month")
            # Validate days in month (simple check)
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                raise ValueError("Invalid day")
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail="Invalid date",
            )

    # Fetch all data scoped to user's org
    org_id = user["org_id"]
    metrics = _fetch_latest_metrics(org_id=org_id)
    risk_flags = _fetch_risk_flags_ordered(org_id=org_id)
    fw_mappings = _fetch_framework_mappings(framework)
    supplier_summary = _fetch_supplier_summary(org_id=org_id)

    # Build the PDF
    pdf = _CompliancePDF()
    pdf.set_auto_page_break(auto=True, margin=22)

    # Page 1: Cover
    pdf.add_page()
    _render_cover_page(pdf)

    # Page 2: Executive Summary + Environmental Performance
    pdf.add_page()
    _render_executive_summary(pdf, metrics, risk_flags)
    pdf.ln(8)
    _render_environmental_table(pdf, metrics)

    # Page 3: Risk Flags
    pdf.add_page()
    _render_risk_flags(pdf, risk_flags)

    # Page 4: Framework Mapping
    pdf.add_page()
    _render_framework_mapping(pdf, fw_mappings, framework)

    # Supplier Summary (continues on same page if space allows, else new page)
    pdf.ln(10)
    if pdf.get_y() > _PAGE_H - 80:
        pdf.add_page()
    _render_supplier_summary(pdf, supplier_summary)

    # Output to bytes
    pdf_bytes = bytes(pdf.output())
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=esg-compliance-report.pdf",
        },
    )
