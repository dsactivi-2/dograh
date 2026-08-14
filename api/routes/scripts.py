"""Script library + prompt search + definition diff."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.db import db_client
from api.db.models import UserModel
from api.schemas.script_library import (
    DefinitionDiffResponse,
    PromptSearchHit,
    PromptSearchResponse,
    ScriptEntryCreate,
    ScriptEntryResponse,
    ScriptEntryUpdate,
    ScriptListResponse,
)
from api.services.auth.depends import get_user
from api.services.script_library.diff import diff_definition_prompts

router = APIRouter(prefix="/scripts", tags=["scripts"])


def _require_org(user: UserModel) -> int:
    if not user.selected_organization_id:
        raise HTTPException(status_code=400, detail="No organization selected")
    return int(user.selected_organization_id)


async def _to_response(entry) -> ScriptEntryResponse:
    emails = await db_client.owner_emails_map([entry.owner_user_id])
    wf_name = await db_client.get_workflow_name(
        entry.workflow_id, organization_id=entry.organization_id
    )
    return ScriptEntryResponse(
        id=entry.id,
        organization_id=entry.organization_id,
        workflow_id=entry.workflow_id,
        workflow_name=wf_name or "",
        definition_id=entry.definition_id,
        title=entry.title,
        description=entry.description or "",
        tags=list(entry.tags or []),
        owner_user_id=entry.owner_user_id,
        owner_email=emails.get(entry.owner_user_id),
        approval_status=entry.approval_status,
        approved_by_user_id=entry.approved_by_user_id,
        approved_at=entry.approved_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/health")
async def scripts_health():
    return {"status": "ok", "module": "scripts"}


@router.get("", response_model=ScriptListResponse)
async def list_scripts(
    workflow_id: Optional[int] = Query(None),
    approval_status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    owner_user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(get_user),
) -> ScriptListResponse:
    org_id = _require_org(user)
    rows, total = await db_client.list_script_entries(
        org_id,
        workflow_id=workflow_id,
        approval_status=approval_status,
        tag=tag,
        owner_user_id=owner_user_id,
        page=page,
        limit=limit,
    )
    items = [await _to_response(r) for r in rows]
    return ScriptListResponse(total=total, items=items)


@router.post("", response_model=ScriptEntryResponse)
async def create_script(
    body: ScriptEntryCreate,
    user: UserModel = Depends(get_user),
) -> ScriptEntryResponse:
    org_id = _require_org(user)
    try:
        entry = await db_client.create_script_entry(
            organization_id=org_id,
            workflow_id=body.workflow_id,
            title=body.title,
            owner_user_id=user.id,
            description=body.description,
            tags=body.tags,
            definition_id=body.definition_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return await _to_response(entry)


@router.get("/search/prompts", response_model=PromptSearchResponse)
async def search_prompts(
    q: str = Query(..., min_length=1, max_length=200),
    workflow_id: Optional[int] = Query(None),
    limit: int = Query(40, ge=1, le=100),
    user: UserModel = Depends(get_user),
) -> PromptSearchResponse:
    org_id = _require_org(user)
    hits_raw = await db_client.search_prompts_fts(
        org_id, q, workflow_id=workflow_id, limit=limit
    )
    hits = [PromptSearchHit(**h) for h in hits_raw]
    return PromptSearchResponse(query=q, total=len(hits), hits=hits)


@router.get("/diff", response_model=DefinitionDiffResponse)
async def definition_diff(
    definition_a: int = Query(..., description="First definition id"),
    definition_b: int = Query(..., description="Second definition id"),
    user: UserModel = Depends(get_user),
) -> DefinitionDiffResponse:
    org_id = _require_org(user)
    a = await db_client.get_definition_for_org(definition_a, org_id)
    b = await db_client.get_definition_for_org(definition_b, org_id)
    if a is None or b is None:
        raise HTTPException(status_code=404, detail="One or both definitions not found")
    def_a, wf_a = a
    def_b, wf_b = b
    changes = diff_definition_prompts(def_a.workflow_json, def_b.workflow_json)
    summary = {
        "added": sum(1 for c in changes if c.change == "added"),
        "removed": sum(1 for c in changes if c.change == "removed"),
        "changed": sum(1 for c in changes if c.change == "changed"),
    }
    return DefinitionDiffResponse(
        definition_a_id=definition_a,
        definition_b_id=definition_b,
        workflow_id_a=wf_a.id,
        workflow_id_b=wf_b.id,
        changes=changes,
        summary=summary,
    )


@router.get("/{entry_id}", response_model=ScriptEntryResponse)
async def get_script(
    entry_id: int,
    user: UserModel = Depends(get_user),
) -> ScriptEntryResponse:
    org_id = _require_org(user)
    entry = await db_client.get_script_entry(entry_id, org_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Script entry not found")
    return await _to_response(entry)


@router.patch("/{entry_id}", response_model=ScriptEntryResponse)
async def update_script(
    entry_id: int,
    body: ScriptEntryUpdate,
    user: UserModel = Depends(get_user),
) -> ScriptEntryResponse:
    org_id = _require_org(user)
    try:
        entry = await db_client.update_script_entry(
            entry_id,
            org_id,
            title=body.title,
            description=body.description,
            tags=body.tags,
            definition_id=body.definition_id,
            approval_status=body.approval_status,
            actor_user_id=user.id,
            actor_is_superuser=bool(user.is_superuser),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    if entry is None:
        raise HTTPException(status_code=404, detail="Script entry not found")
    return await _to_response(entry)


@router.delete("/{entry_id}")
async def delete_script(
    entry_id: int,
    user: UserModel = Depends(get_user),
):
    org_id = _require_org(user)
    entry = await db_client.get_script_entry(entry_id, org_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Script entry not found")
    # owner or superuser
    if entry.owner_user_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Only owner or superuser can delete")
    await db_client.delete_script_entry(entry_id, org_id)
    return {"ok": True, "id": entry_id}
