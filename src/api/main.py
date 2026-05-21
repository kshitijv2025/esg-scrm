"""
ESG+SCRM Platform API — FastAPI backend backed by SQLite.
"""
import asyncio
import json
import logging
import os
import shutil
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware.auth import require_auth
from src.api.middleware.audit import AuditMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes import (
    admin,
    alerts,
    audit,
    auth,
    buyer_portal,
    corrective_actions,
    compliance,
    dashboard,
    documents,
    emission_factors,
    evidence,
    export,
    frameworks,
    ml,
    onboarding,
    questionnaires,
    reports,
    reports_pdf,
    risk,
    scheduled_reports,
    scope3,
    suppliers,
    templates,
    tier2,
    tier3,
    trust,
    upload,
    water,
    webhooks,
    whatsapp,
)
from src.db.database import get_connection, release_connection
from src.db.seed import seed

load_dotenv()

# Initialize Sentry error monitoring
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastAPIIntegration
    from sentry_sdk.integrations.sqlite import SQLiteIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastAPIIntegration(transaction_style="url"),
            SQLiteIntegration(),
        ],
        environment=os.environ.get("ENVIRONMENT", "development"),
        release=os.environ.get("APP_VERSION", "0.2.0"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
    logger.info("sentry.initialized dsn=%s", SENTRY_DSN[:20] + "...")

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
        from src.db.seed_alert_thresholds import seed_alert_thresholds
        from src.db.seed_emission_factors import seed_emission_factors
        seed_emission_factors()
        seed_alert_thresholds()
        try:
            from src.db.seed_framework_mappings import seed_framework_mappings
            seed_framework_mappings()
        except ImportError:
            pass
        from src.db.seed_templates import seed_templates
        seed_templates()
        from src.db.seed_country_risk import seed_country_risk
        seed_country_risk()

    factory_id = os.environ.get("MQTT_FACTORY_ID", "factory_bd_001")

    from src.orchestration.etl import etl_loop, start_mqtt_consumer, stop_mqtt_consumer
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

app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(dashboard.router, prefix="/api/dashboard", dependencies=[Depends(require_auth)])
app.include_router(evidence.router, prefix="/api/evidence", dependencies=[Depends(require_auth)])
app.include_router(evidence.auditor_router, prefix="/api/evidence")
app.include_router(frameworks.router, prefix="/api/frameworks", dependencies=[Depends(require_auth)])
app.include_router(questionnaires.router, prefix="/api/questionnaires", dependencies=[Depends(require_auth)])
app.include_router(tier2.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(tier3.router, prefix="/api", dependencies=[Depends(require_auth)])
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
app.include_router(export.router, prefix="/api/export", dependencies=[Depends(require_auth)])
app.include_router(whatsapp.router, prefix="/api/whatsapp", dependencies=[Depends(require_auth)])
app.include_router(whatsapp.webhook_router, prefix="/api/whatsapp")
app.include_router(ml.router, prefix="/api/ml", dependencies=[Depends(require_auth)])
app.include_router(water.router, prefix="/api/water", dependencies=[Depends(require_auth)])
app.include_router(trust.router, prefix="/api/trust", dependencies=[Depends(require_auth)])
app.include_router(auth.router, prefix="/api/auth")
app.include_router(admin.router, prefix="/api/admin", dependencies=[Depends(require_auth)])

# Phase D: New routes
app.include_router(corrective_actions.router, prefix="/api/corrective-actions", dependencies=[Depends(require_auth)])
app.include_router(documents.router, prefix="/api/documents", dependencies=[Depends(require_auth)])
app.include_router(compliance.router, prefix="/api/compliance", dependencies=[Depends(require_auth)])
app.include_router(scheduled_reports.router, prefix="/api/reports/scheduled", dependencies=[Depends(require_auth)])
app.include_router(webhooks.router, prefix="/api/webhooks", dependencies=[Depends(require_auth)])
app.include_router(buyer_portal.router, prefix="/api/access", dependencies=[Depends(require_auth)])
app.include_router(buyer_portal.public_router, prefix="/api/buyer-portal")  # Public token-based route
app.include_router(onboarding.router, prefix="/api/onboarding", dependencies=[Depends(require_auth)])

from src.realtime.alerts import ws_alerts_endpoint

app.websocket("/ws/alerts")(ws_alerts_endpoint)

# Alias route: spec says /api/metrics/intensity, implementation uses /api/dashboard/intensity
metrics_router = APIRouter()
@metrics_router.get("/intensity")
def metrics_intensity_alias(user: dict = Depends(require_auth)):
    from src.api.routes.dashboard import emission_intensity
    return emission_intensity(user)

app.include_router(metrics_router, prefix="/api/metrics", dependencies=[Depends(require_auth)])


@app.get("/api/health")
def health():
    from src.db.database import get_connection, release_connection

    db_url = os.environ.get("DATABASE_URL", "")
    is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")

    # Database health check
    db_healthy = False
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        release_connection(conn)
        db_healthy = True
    except Exception:
        pass

    # Postgres-specific health check
    postgres_healthy = None
    if is_postgres:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            conn.close()
            postgres_healthy = True
        except Exception:
            postgres_healthy = False

    # Disk space check
    disk_healthy = True
    try:
        usage = shutil.disk_usage("/")
        disk_healthy = usage.used / usage.total < 0.90
    except Exception:
        pass

    # SAP B1 connector health check
    sap_b1_healthy = None
    sap_b1_info = {}
    try:
        from src.connectors.sap_b1_adapter import SAPBusinessOneAdapter
        sap_b1_info = SAPBusinessOneAdapter().health_check()
        sap_b1_healthy = sap_b1_info.get("connected", False)
    except Exception:
        sap_b1_healthy = False

    components = {
        "database": "healthy" if db_healthy else "unhealthy",
    }
    if is_postgres:
        components["postgres"] = "healthy" if postgres_healthy else "unhealthy"
    if sap_b1_healthy is not None:
        components["sap_b1"] = "healthy" if sap_b1_healthy else "degraded"

    checks = {
        "db_connection": db_healthy,
        "disk_space": disk_healthy,
        "version": "0.2.0",
    }
    if sap_b1_healthy is not None:
        checks["sap_b1_connected"] = sap_b1_healthy

    response = {
        "status": "ok" if (db_healthy and disk_healthy) else "degraded",
        "version": "0.2.0",
        "components": components,
        "checks": checks,
    }
    if sap_b1_info and not sap_b1_info.get("connected"):
        response["sap_b1_error"] = sap_b1_info.get("error", "unknown")

    return response


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
