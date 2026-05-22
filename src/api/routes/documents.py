"""
Documents API — Upload, list, and manage documents with expiry tracking.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, require_role
from src.db.database import get_connection, release_connection

router = APIRouter()

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads/documents")


def _doc_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "supplier_id": row.get("supplier_id"),
        "name": row["name"],
        "file_type": row["file_type"],
        "file_size": row.get("file_size"),
        "mime_type": row.get("mime_type"),
        "category": row["category"],
        "expiry_date": row.get("expiry_date"),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
        "is_expired": bool(
            row.get("expiry_date")
            and row["expiry_date"] < datetime.now(timezone.utc).isoformat()[:10]
        ),
    }


@router.get("")
def list_documents(
    category: Optional[str] = None,
    supplier_id: Optional[str] = None,
    include_expired: bool = False,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """List documents for the org, optionally filtered by category or supplier."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM documents WHERE org_id = ?"
        params = [org_id]

        if category:
            query += " AND category = ?"
            params.append(category)
        if supplier_id:
            query += " AND supplier_id = ?"
            params.append(supplier_id)
        if not include_expired:
            today = datetime.now(timezone.utc).isoformat()[:10]
            query += " AND (expiry_date IS NULL OR expiry_date >= ?)"
            params.append(today)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = conn.execute(query, params).fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) as cnt FROM documents WHERE org_id = ?"
        count_params = [org_id]
        if category:
            count_query += " AND category = ?"
            count_params.append(category)
        if supplier_id:
            count_query += " AND supplier_id = ?"
            count_params.append(supplier_id)
        if not include_expired:
            count_query += " AND (expiry_date IS NULL OR expiry_date >= ?)"
            count_params.append(today)

        total = conn.execute(count_query, count_params).fetchone()["cnt"]

        return {"documents": [_doc_to_dict(dict(r)) for r in rows], "total": total}
    finally:
        release_connection(conn)


@router.get("/{doc_id}")
def get_document(doc_id: str, user: dict = Depends(require_auth)):
    """Get a single document by ID."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND org_id = ?",
            (doc_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        return _doc_to_dict(dict(row))
    finally:
        release_connection(conn)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    supplier_id: Optional[str] = Form(None),
    category: Optional[str] = Form("certificate"),
    expiry_date: Optional[str] = Form(None),
    user: dict = Depends(require_auth),
):
    """Upload a document. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_filename = f"{doc_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    # Read and save file
    contents = await file.read()
    file_size = len(contents)

    with open(file_path, "wb") as f:
        f.write(contents)

    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO documents
               (id, org_id, supplier_id, name, file_path, file_type, file_size, mime_type,
                category, expiry_date, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                org_id,
                supplier_id,
                file.filename or "unnamed",
                file_path,
                file_ext.lstrip(".") or "unknown",
                file_size,
                file.content_type,
                category,
                expiry_date,
                now,
                user.get("email", ""),
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": doc_id, "name": file.filename, "created_at": now}


@router.delete("/{doc_id}")
def delete_document(doc_id: str, user: dict = Depends(require_auth)):
    """Delete a document. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT file_path FROM documents WHERE id = ? AND org_id = ?",
            (doc_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")

        # Delete file from disk
        file_path = row["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)

        conn.execute("DELETE FROM documents WHERE id = ? AND org_id = ?", (doc_id, org_id))
        conn.commit()
    finally:
        release_connection(conn)

    return {"deleted": True}


@router.get("/{doc_id}/download")
def download_document(doc_id: str, user: dict = Depends(require_auth)):
    """Download a document file. Requires viewer role."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT file_path, name, mime_type FROM documents WHERE id = ? AND org_id = ?",
            (doc_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        row = dict(row)

        file_path = row["file_path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="file not found on disk")

        return FileResponse(
            file_path,
            filename=row["name"],
            media_type=row.get("mime_type", "application/octet-stream"),
        )
    finally:
        release_connection(conn)


@router.get("/expiring/soon")
def expiring_documents(
    days: int = 30,
    user: dict = Depends(require_auth),
):
    """Get documents expiring within the specified number of days."""
    org_id = user["org_id"]
    from datetime import timedelta

    future_date = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()[:10]
    today = datetime.now(timezone.utc).isoformat()[:10]

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM documents
               WHERE org_id = ? AND expiry_date IS NOT NULL
               AND expiry_date >= ? AND expiry_date <= ?
               ORDER BY expiry_date ASC""",
            (org_id, today, future_date),
        ).fetchall()
        return {"documents": [_doc_to_dict(dict(r)) for r in rows], "total": len(rows)}
    finally:
        release_connection(conn)
