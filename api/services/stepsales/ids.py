"""Public ID helpers for Stepsales entities."""

from __future__ import annotations

import secrets
import string


def _token(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def new_lead_id() -> str:
    return f"LEAD-{_token()}"


def new_call_outcome_id() -> str:
    return f"OUT-{_token()}"


def new_offer_id() -> str:
    return f"OFF-{_token()}"


def new_followup_id() -> str:
    return f"FU-{_token()}"


def new_appointment_id() -> str:
    return f"APT-{_token()}"


def new_payment_reference() -> str:
    return f"PAY-{_token()}"


def new_request_id() -> str:
    return f"REQ-{_token()}"
