"""Explicit C1 handoff point; no real predictor is registered by this repository."""
from .contracts import PredictorCompatibilityError, PredictorContract
from .predictor import Predictor

_real_predictor: Predictor | None = None
_c1_integration_verified = False


def register_real_predictor(predictor: Predictor, *, integration_verified: bool = False) -> None:
    global _real_predictor, _c1_integration_verified
    contract = getattr(predictor, "contract", None)
    if not isinstance(contract, PredictorContract) or contract.mode != "real":
        raise PredictorCompatibilityError("only a contracted real predictor may be registered")
    _real_predictor = predictor
    _c1_integration_verified = integration_verified


def get_real_predictor() -> Predictor | None:
    return _real_predictor


def c1_integration_verified() -> bool:
    return _real_predictor is not None and _c1_integration_verified
