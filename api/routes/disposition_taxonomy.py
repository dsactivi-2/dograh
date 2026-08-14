"""Disposition taxonomy R/W — success set + labels per workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.db import db_client
from api.db.models import UserModel
from api.schemas.disposition_taxonomy import (
    DispositionTaxonomyResponse,
    DispositionTaxonomyUpdate,
    OrgDispositionSummaryResponse,
)
from api.services.auth.depends import get_user

router = APIRouter(prefix="/disposition-taxonomy", tags=["disposition-taxonomy"])


def _require_org(user: UserModel) -> int:
    if not user.selected_organization_id:
        raise HTTPException(status_code=400, detail="No organization selected")
    return int(user.selected_organization_id)


@router.get("/health")
async def disposition_taxonomy_health():
    return {"status": "ok", "module": "disposition-taxonomy"}


@router.get("/summary", response_model=OrgDispositionSummaryResponse)
async def org_disposition_summary(
    user: UserModel = Depends(get_user),
) -> OrgDispositionSummaryResponse:
    org_id = _require_org(user)
    codes = await db_client.list_org_disposition_summary(org_id)
    return OrgDispositionSummaryResponse(organization_id=org_id, codes=codes)


@router.get(
    "/workflows/{workflow_id}",
    response_model=DispositionTaxonomyResponse,
)
async def get_workflow_disposition_taxonomy(
    workflow_id: int,
    user: UserModel = Depends(get_user),
) -> DispositionTaxonomyResponse:
    org_id = _require_org(user)
    row = await db_client.get_workflow_taxonomy(workflow_id, org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow, tax = row
    return DispositionTaxonomyResponse(
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        taxonomy=tax,
    )


@router.put(
    "/workflows/{workflow_id}",
    response_model=DispositionTaxonomyResponse,
)
async def put_workflow_disposition_taxonomy(
    workflow_id: int,
    body: DispositionTaxonomyUpdate,
    user: UserModel = Depends(get_user),
) -> DispositionTaxonomyResponse:
    org_id = _require_org(user)
    row = await db_client.set_workflow_taxonomy(workflow_id, org_id, body)
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow, tax = row
    return DispositionTaxonomyResponse(
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        taxonomy=tax,
    )
