"""Stepsales sales backend — lead, offer, payment, and follow-up operations."""

__all__ = ["StepsalesService"]


def __getattr__(name: str):
    if name == "StepsalesService":
        from api.services.stepsales.service import StepsalesService

        return StepsalesService
    raise AttributeError(name)
