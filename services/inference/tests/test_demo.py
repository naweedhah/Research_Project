"""P0 scientific integrity regression tests for DemoModelAdapter."""

from app.main import DemoModelAdapter, PredictRequest, _tri_state_contribution
from app.demo_outcomes import get_demo_outcome


def test_demo_visit_numbering_is_one_based_and_matches_outcomes():
    adapter = DemoModelAdapter()
    for visit_number, score in ((1, 0.82), (2, 0.61), (3, 0.59)):
        out = adapter.predict(PredictRequest(child_pseudonymous_id="C-1042", visit_number=visit_number))
        canonical = get_demo_outcome("C-1042", visit_number)
        assert canonical is not None
        assert out.risk_score == score == canonical[2]
        assert out.status == canonical[0]
        assert out.severity == canonical[1]
        assert out.mode == "DEMO"
        assert out.score_kind == "demo_progression_score"
        assert out.score_is_probability is False
        assert out.clinical_use is False
        assert out.prediction_task == "current_status_demo"


def test_demo_adapter_idempotent_for_canonical_child():
    adapter = DemoModelAdapter()
    a = adapter.predict(PredictRequest(child_pseudonymous_id="C-1042", visit_number=1))
    b = adapter.predict(PredictRequest(child_pseudonymous_id="C-1042", visit_number=1))
    assert a.risk_score == b.risk_score == 0.82
    assert a.status == b.status == "wasting"
    assert a.severity == b.severity == "severe"
    assert a.latent_embedding == b.latent_embedding
    assert a.confidence == "moderate"


def test_c1005_visit_four_matches_seed_narrative():
    adapter = DemoModelAdapter()
    out = adapter.predict(PredictRequest(child_pseudonymous_id="C-1005", visit_number=4))
    assert out.risk_score == 0.58
    assert out.status == "wasting"


def test_tri_state_diarrhoea_none_not_same_branch_as_false():
    true_delta, true_unknown = _tri_state_contribution(True, true_delta=0.08)
    false_delta, false_unknown = _tri_state_contribution(False, true_delta=0.08)
    none_delta, none_unknown = _tri_state_contribution(None, true_delta=0.08)
    assert true_delta == 0.08 and true_unknown is False
    assert false_delta == 0.0 and false_unknown is False
    assert none_delta == 0.0 and none_unknown is True
    assert (false_unknown, none_unknown) != (True, True)

    adapter = DemoModelAdapter()
    base = {
        "child_pseudonymous_id": "C-1999",
        "visit_number": 1,
        "anthropometric": {"weight_kg": 8, "height_cm": 72, "muac_cm": 12},
        "dietary": {"dietary_diversity_score": 3},
    }
    yes = adapter.predict(
        PredictRequest(**base, maternal_child_health={"recent_diarrhoea": True})
    )
    no = adapter.predict(
        PredictRequest(**base, maternal_child_health={"recent_diarrhoea": False})
    )
    unknown = adapter.predict(
        PredictRequest(**base, maternal_child_health={"recent_diarrhoea": None})
    )
    assert yes.risk_score != no.risk_score
    assert "recent_diarrhoea_unknown" in unknown.data_limitations
    assert "recent_diarrhoea_unknown" not in no.data_limitations


def test_demo_adapter_is_deterministic_for_heuristic_path():
    adapter = DemoModelAdapter()
    payload = PredictRequest(
        child_pseudonymous_id="C-1999",
        visit_number=1,
        anthropometric={"weight_kg": 8, "height_cm": 72, "muac_cm": 12},
    )
    a = adapter.predict(payload)
    b = adapter.predict(payload)
    assert a.risk_score == b.risk_score
    assert a.latent_embedding == b.latent_embedding
