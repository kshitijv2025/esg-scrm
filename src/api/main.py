"""
ESG+SCRM Platform API — FastAPI backend backed by SQLite.
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware.auth import require_auth
from src.api.routes import dashboard, evidence, frameworks, questionnaires, suppliers, reports, risk, scope3
from src.api.routes import auth, emission_factors, alerts, audit, upload, templates, reports_pdf, whatsapp, ml
from src.db.database import get_connection, release_connection
from src.db.seed import seed

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


class PrettyJSONResponse(JSONResponse):
    """JSON responses with 2-space indentation for readability."""

    def render(self, content) -> bytes:
        return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")


_etl_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize and seed database, start MQTT + ETL loop. Shutdown: cleanup."""
    global _etl_task

    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) as cnt FROM metrics").fetchone()["cnt"]
    finally:
        release_connection(conn)
    if count == 0:
        seed()
        from src.db.seed_emission_factors import seed_emission_factors
        from src.db.seed_alert_thresholds import seed_alert_thresholds
        seed_emission_factors()
        seed_alert_thresholds()
        try:
            from src.db.seed_framework_mappings import seed_framework_mappings
            seed_framework_mappings()
        except ImportError:
            pass
        from src.db.seed_templates import seed_templates
        seed_templates()

    factory_id = os.environ.get("MQTT_FACTORY_ID", "factory_bd_001")

    from src.orchestration.etl import start_mqtt_consumer, stop_mqtt_consumer, etl_loop
    try:
        start_mqtt_consumer(factory_id=factory_id)
    except Exception as e:
        logger.warning("main.mqtt_unavailable error=%s — continuing without MQTT", e)

    _etl_task = asyncio.create_task(etl_loop(interval=60, factory_id=factory_id))

    yield

    if _etl_task:
        _etl_task.cancel()
        try:
            await _etl_task
        except asyncio.CancelledError:
            pass
    stop_mqtt_consumer()


cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000")

app = FastAPI(
    title="ESG+SCRM Platform",
    description="Supply Chain ESG Data Collection & Evidence Vault",
    version="0.2.0",
    default_response_class=PrettyJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", dependencies=[Depends(require_auth)])
app.include_router(evidence.router, prefix="/api/evidence", dependencies=[Depends(require_auth)])
app.include_router(frameworks.router, prefix="/api/frameworks", dependencies=[Depends(require_auth)])
app.include_router(questionnaires.router, prefix="/api/questionnaires", dependencies=[Depends(require_auth)])
app.include_router(suppliers.router, prefix="/api/suppliers", dependencies=[Depends(require_auth)])
app.include_router(reports.router, prefix="/api/reports", dependencies=[Depends(require_auth)])
app.include_router(risk.router, prefix="/api/risk", dependencies=[Depends(require_auth)])
app.include_router(scope3.router, prefix="/api/scope3", dependencies=[Depends(require_auth)])
app.include_router(emission_factors.router, prefix="/api/emission-factors", dependencies=[Depends(require_auth)])
app.include_router(alerts.router, prefix="/api/alerts", dependencies=[Depends(require_auth)])
app.include_router(audit.router, prefix="/api/audit", dependencies=[Depends(require_auth)])
app.include_router(upload.router, prefix="/api/upload", dependencies=[Depends(require_auth)])
app.include_router(templates.router, prefix="/api/templates", dependencies=[Depends(require_auth)])
app.include_router(reports_pdf.router, prefix="/api/reports", dependencies=[Depends(require_auth)])
app.include_router(whatsapp.router, prefix="/api/whatsapp", dependencies=[Depends(require_auth)])
app.include_router(whatsapp.webhook_router, prefix="/api/whatsapp")
app.include_router(ml.router, prefix="/api/ml", dependencies=[Depends(require_auth)])
app.include_router(auth.router, prefix="/api/auth")

from src.realtime.alerts import ws_alerts_endpoint
app.websocket("/ws/alerts")(ws_alerts_endpoint)


@app.get("/api/health")
def health():
    from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter
    erp_status = SAPBusinessOneAdapter().health_check()

    return {
        "status": "ok",
        "version": "0.2.0",
        "erp": erp_status,
    }


@app.get("/api/org", dependencies=[Depends(require_auth)])
def org_info(user: dict = Depends(require_auth)):
    conn = get_connection()
    try:
        org = conn.execute(
            "SELECT id, name, industry FROM organizations WHERE id = ?",
            (user["org_id"],),
        ).fetchone()
    finally:
        release_connection(conn)

    if not org:
        return {"id": user["org_id"], "name": "Unknown", "industry": ""}

    return {
        "id": org["id"],
        "name": org["name"],
        "industry": org.get("industry", ""),
    }
