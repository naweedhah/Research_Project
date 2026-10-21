"""Method provenance, independence and fail-closed v2 research checks."""
from copy import deepcopy

from components.c2_counterfactual_intervention.tests.test_nutrition_scenarios_v2 import request_data, run
from components.c2_counterfactual_intervention.wachter_method import optimize_test_pattern


def test_compare_all_runs_distinct_available_methods_without_c1_calls():
    data = request_data(method="compare_all")
    before = deepcopy(data)
    result = run(data)
    assert data == before
    assert result["c1_candidate_calls"] == 0
    methods = result["method_results"]
    assert list(methods) == ["bounded_search", "dice", "face_graph", "wachter"]
    assert methods["bounded_search"]["generated_count"] == 4
    assert methods["face_graph"]["generated_count"] == 4
    assert methods["dice"]["generated_count"] == methods["wachter"]["generated_count"] == 0
    assert methods["dice"]["status"].startswith("unavailable")
    assert methods["wachter"]["status"].startswith("unavailable")
    assert len(result["unresolved_or_rejected"]) == 4  # shared IDs, not eight discoveries
    assert all(set(card["generator_methods"]) == {"bounded_search", "face_graph"}
               for card in result["unresolved_or_rejected"])
    assert result["ranked_cards"] == []


def test_face_uses_paths_and_prunes_excluded_foods():
    data = request_data(method="face_graph")
    data["household"].update(allergy_status="reported", excluded_food_ids=["egg_average"])
    result = run(data)
    paths = result["method_results"]["face_graph"]["diagnostics"]["paths"]
    assert paths
    assert all(path["path_cost"] == len(path["path"]) - 1 for path in paths.values())
    assert all("egg_average" not in state for path in paths.values() for state in path["path"])
    assert result["method_results"]["face_graph"]["generated_count"] == 4
    assert all("egg_average" not in {food["food_id"] for food in card["items"]}
               for card in result["unresolved_or_rejected"])


def test_method_selection_never_falls_back_to_bounded_search():
    assert run(request_data(method="dice"))["candidate_count"] == 0
    assert run(request_data(method="wachter"))["candidate_count"] == 0
    assert run(request_data(method="bounded_search"))["candidate_count"] == 4


def test_wachter_synthetic_fixture_performs_bounded_continuous_optimization():
    first = optimize_test_pattern((0.0, 0.0))
    second = optimize_test_pattern((0.0, 0.0))
    assert first == second
    assert first["converged"] and first["iterations"] <= 100
    assert first["initializations"] == 3
    assert first["independent_fixture_target_pass"]
    assert first["nutrition_validated"] is False and first["c1_calls"] == 0
    assert first["objective_value"] < 1


def test_explicit_supervisor_software_fixture_runs_four_methods_without_fabricated_health_rank():
    result = run(request_data(method="compare_all", research_algorithm_demo=True))
    methods = result["method_results"]
    assert methods["bounded_search"]["generated_count"] == 4
    assert methods["face_graph"]["generated_count"] == 4
    assert methods["dice"]["status"] == methods["wachter"]["status"] == "synthetic_software_test_only"
    assert methods["dice"]["generated_count"] > 0
    assert methods["wachter"]["generated_count"] > 0
    assert result["software_test_ranked"][0]["title"] == "Egg and fruit example"
    assert len(result["software_test_ranked"]) == 4
    assert result["ranked_cards"] == []
    assert result["c1_candidate_calls"] == 0


def test_demo_rank_changes_with_budget_and_exclusion_without_overriding_safety():
    low = request_data(method="compare_all", research_algorithm_demo=True)
    low["household"]["budget_lkr"] = "100"
    assert run(low)["software_test_ranked"] == []
    excluded = request_data(method="compare_all", research_algorithm_demo=True)
    excluded["household"].update(allergy_status="reported", excluded_food_ids=["mysore_dhall_average"])
    result = run(excluded)
    assert all(card["title"] != "Essentials example" for card in result["software_test_ranked"])
    assert result["original_c1"] == run(low)["original_c1"]
