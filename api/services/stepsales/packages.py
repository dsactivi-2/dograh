"""Fixed commercial package catalog for Stepsales."""

from __future__ import annotations

from typing import TypedDict


class PackageDef(TypedDict):
    package_id: str
    name: str
    list_price: float
    description: str


PACKAGE_CATALOG: dict[str, PackageDef] = {
    "MULTI_S": {
        "package_id": "MULTI_S",
        "name": "Multiposting Paket S",
        "list_price": 790.0,
        "description": "Zusätzliche Reichweite auf ausgewählten Portalen (S).",
    },
    "MULTI_M": {
        "package_id": "MULTI_M",
        "name": "Multiposting Paket M",
        "list_price": 1490.0,
        "description": "Multiposting auf Kernportalen inkl. StepStone/Indeed-Mix (M).",
    },
    "MULTI_L": {
        "package_id": "MULTI_L",
        "name": "Multiposting Paket L",
        "list_price": 2490.0,
        "description": "Maximale Reichweite und bevorzugte Platzierungen (L).",
    },
}

MAX_DISCOUNT_PERCENT = 10.0


def get_package(package_id: str) -> PackageDef | None:
    return PACKAGE_CATALOG.get(package_id)


def list_packages() -> list[PackageDef]:
    return list(PACKAGE_CATALOG.values())


def compute_final_price(list_price: float, discount_percent: float) -> float:
    if discount_percent < 0 or discount_percent > MAX_DISCOUNT_PERCENT:
        raise ValueError(
            f"discount_percent must be between 0 and {MAX_DISCOUNT_PERCENT}"
        )
    final = list_price * (1.0 - (discount_percent / 100.0))
    return round(final, 2)
