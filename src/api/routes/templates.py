"""Questionnaire template API — CRUD operations for ESG questionnaire templates."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, VIEWER_ROLES, EDITOR_ROLES, ADMIN_ROLES
from src.db.database import get_connection, _fetchall, _fetchone, _execute

router = APIRouter()

VALID_TIERS = {1, 2, 3, 4}


@router.get("/")
def list_templates(
    tier: Optional[int] = None,
    user: dict = Depends(require_auth),
):
    """List all active templates, optionally filtered by tier, for the user's org."""
    org_id = user["org_id"]
    conn = get_connection()
    query = "SELECT * FROM questionnaire_templates WHERE is_active = 1 AND (org_id = ? OR org_id = '')"
    params: list = [org_id]

    if tier is not None:
        query += " AND tier = ?"
        params.append(tier)

    query += " ORDER BY tier, name"
    templates = _fetchall(conn, query, tuple(params))

    for t in templates:
        t["questions"] = json.loads(t.get("questions", "[]"))

    return {"templates": templates, "total": len(templates)}


@router.get("/{template_id}")
def get_template(template_id: int, user: dict = Depends(require_auth)):
    """Get a single template by ID. Returns 404 if not found, inactive, or belongs to another org."""
    org_id = user["org_id"]
    conn = get_connection()
    template = _fetchone(
        conn,
        "SELECT * FROM questionnaire_templates WHERE id = ? AND is_active = 1 AND (org_id = ? OR org_id = '')",
        (template_id, org_id),
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    template["questions"] = json.loads(template.get("questions", "[]"))
    return template


@router.post("/")
def create_template(body: dict, user: dict = Depends(require_auth)):
    require_role(user, EDITOR_ROLES)
    """Create a new questionnaire template.

    Body must include: name, tier, questions (list of dicts with question_id and text).
    Optional: description, org_id.
    """
    if "name" not in body or not body["name"]:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    if "tier" not in body:
        raise HTTPException(status_code=400, detail="Missing required field: tier")
    if body["tier"] not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail="tier must be one of: 1, 2, 3, 4",
        )
    if "questions" not in body:
        raise HTTPException(status_code=400, detail="Missing required field: questions")

    questions = body["questions"]
    if not isinstance(questions, list):
        raise HTTPException(status_code=400, detail="questions must be a list")

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise HTTPException(
                status_code=400,
                detail=f"questions[{i}] must be a dict with question_id and text",
            )
        if "question_id" not in q:
            raise HTTPException(
                status_code=400,
                detail=f"questions[{i}] missing required field: question_id",
            )
        if "text" not in q:
            raise HTTPException(
                status_code=400,
                detail=f"questions[{i}] missing required field: text",
            )

    conn = get_connection()
    cur = _execute(
        conn,
        """
        INSERT INTO questionnaire_templates (org_id, name, description, tier, questions)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user["org_id"],
            body["name"],
            body.get("description", ""),
            body["tier"],
            json.dumps(questions),
        ),
    )

    return {"id": cur.lastrowid, "status": "created"}


@router.put("/{template_id}")
def update_template(template_id: int, body: dict, user: dict = Depends(require_auth)):
    require_role(user, EDITOR_ROLES)
    """Update a template. All fields are optional — only provided fields are changed."""
    org_id = user["org_id"]
    conn = get_connection()
    existing = _fetchone(
        conn,
        "SELECT * FROM questionnaire_templates WHERE id = ? AND is_active = 1 AND (org_id = ? OR org_id = '')",
        (template_id, org_id),
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if "tier" in body and body["tier"] not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail="tier must be one of: 1, 2, 3, 4",
        )

    if "questions" in body:
        questions = body["questions"]
        if not isinstance(questions, list):
            raise HTTPException(status_code=400, detail="questions must be a list")
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"questions[{i}] must be a dict with question_id and text",
                )
            if "question_id" not in q:
                raise HTTPException(
                    status_code=400,
                    detail=f"questions[{i}] missing required field: question_id",
                )
            if "text" not in q:
                raise HTTPException(
                    status_code=400,
                    detail=f"questions[{i}] missing required field: text",
                )

    name = body.get("name", existing["name"])
    description = body.get("description", existing["description"])
    tier = body.get("tier", existing["tier"])
    questions_json = (
        json.dumps(body["questions"])
        if "questions" in body
        else existing["questions"]
    )

    _execute(
        conn,
        """
        UPDATE questionnaire_templates
        SET name = ?, description = ?, tier = ?, org_id = ?, questions = ?
        WHERE id = ?
        """,
        (name, description, tier, org_id, questions_json, template_id),
    )

    updated = _fetchone(
        conn,
        "SELECT * FROM questionnaire_templates WHERE id = ?",
        (template_id,),
    )
    updated["questions"] = json.loads(updated.get("questions", "[]"))
    return updated


@router.delete("/{template_id}")
def delete_template(template_id: int, user: dict = Depends(require_auth)):
    require_role(user, ADMIN_ROLES)
    """Soft-delete a template by setting is_active to 0."""
    org_id = user["org_id"]
    conn = get_connection()
    existing = _fetchone(
        conn,
        "SELECT * FROM questionnaire_templates WHERE id = ? AND is_active = 1 AND (org_id = ? OR org_id = '')",
        (template_id, org_id),
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Template not found")

    _execute(
        conn,
        "UPDATE questionnaire_templates SET is_active = 0 WHERE id = ?",
        (template_id,),
    )

    return {"status": "deactivated"}
