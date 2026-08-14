"""Route-level tests for Stepsales sales API (mocked db_client)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import stepsales as stepsales_routes
from api.routes.stepsales import router
from api.services.auth.depends import get_user


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_user] = lambda: SimpleNamespace(
        id=1,
        email="tester@example.com",
        selected_organization_id=42,
        provider_id="test-user",
    )
    return app


def test_stepsales_health_is_public():
    client = TestClient(_make_app())
    response = client.get("/api/v1/stepsales/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["module"] == "stepsales"
    assert "MULTI_M" in body["packages"]


def test_packages_requires_org_and_returns_catalog():
    client = TestClient(_make_app())
    response = client.get("/api/v1/stepsales/packages")
    assert response.status_code == 200
    packages = response.json()
    assert len(packages) == 3
    assert {p["package_id"] for p in packages} == {"MULTI_S", "MULTI_M", "MULTI_L"}


def test_qualify_lead_route_uses_db_client(monkeypatch):
    mock = AsyncMock(
        return_value={
            "success": True,
            "lead_id": "LEAD-TEST01",
            "score": 82,
            "status": "qualified",
        }
    )
    monkeypatch.setattr(stepsales_routes.db_client, "qualify_lead", mock)
    client = TestClient(_make_app())
    response = client.post(
        "/api/v1/stepsales/leads/qualify",
        json={
            "company_name": "TechCorp GmbH",
            "contact_name": "Max Müller",
            "email": "max@techcorp.de",
            "phone": "+49301234567",
            "active_hiring": True,
            "roles_hiring_for": ["Software Engineer", "Sales Manager"],
            "urgency": "high",
            "timeline": "2 weeks",
            "budget_signal": "open",
            "interest_level": "high",
            "next_step": "send_offer",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "lead_id": "LEAD-TEST01",
        "score": 82,
        "status": "qualified",
    }
    assert mock.await_count == 1
    args, _kwargs = mock.await_args
    assert args[0] == 42


def test_call_outcome_route(monkeypatch):
    mock = AsyncMock(
        return_value={
            "success": True,
            "stored": True,
            "outcome_id": "OUT-ABC",
            "lead_id": "LEAD-001",
        }
    )
    monkeypatch.setattr(stepsales_routes.db_client, "log_call_outcome", mock)
    client = TestClient(_make_app())
    response = client.post(
        "/api/v1/stepsales/calls/outcome",
        json={
            "lead_id": "LEAD-001",
            "call_id": "CALL-001",
            "outcome": "qualified",
            "summary": "Active hiring, wants offer.",
            "interest_level": "high",
            "next_step": "send_offer",
        },
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True
    assert response.json()["outcome_id"] == "OUT-ABC"


def test_list_leads_route(monkeypatch):
    now = datetime.now(timezone.utc)
    mock = AsyncMock(
        return_value=[
            SimpleNamespace(
                lead_id="LEAD-001",
                organization_id=42,
                company_name="TechCorp GmbH",
                contact_name="Max",
                role="HR",
                email="max@techcorp.de",
                phone=None,
                active_hiring=True,
                roles_hiring_for=["Engineer"],
                urgency="high",
                timeline="2 weeks",
                budget_signal="open",
                interest_level="high",
                next_step="send_offer",
                score=82,
                status="qualified",
                created_at=now,
                updated_at=now,
            )
        ]
    )
    monkeypatch.setattr(stepsales_routes.db_client, "list_leads", mock)
    client = TestClient(_make_app())
    response = client.get("/api/v1/stepsales/leads")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["lead_id"] == "LEAD-001"
    assert body[0]["score"] == 82


def test_missing_org_returns_400():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_user] = lambda: SimpleNamespace(
        id=1,
        email="tester@example.com",
        selected_organization_id=None,
        provider_id="test-user",
    )
    client = TestClient(app)
    response = client.get("/api/v1/stepsales/packages")
    assert response.status_code == 400
    assert "organization" in response.json()["detail"].lower()
