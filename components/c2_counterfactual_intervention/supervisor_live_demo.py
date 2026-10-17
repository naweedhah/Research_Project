"""Automated October supervisor demo: real-model validation versus test methods."""

import argparse
import json
from datetime import date
from decimal import Decimal

import httpx

from .supervisor_demo import demo_request, official_price_demo


def run(*, c1_url: str, c2_url: str) -> dict:
    with httpx.Client(timeout=60) as client:
        health = client.get(c1_url + "/health")
        info = client.get(c1_url + "/model-info")
        health.raise_for_status()
        info.raise_for_status()
        if not (health.json().get("ga_rgca_loaded") and info.json().get("ga_rgca_loaded")):
            raise RuntimeError("genuine C1 model is not loaded")

        validation = client.get(c2_url + "/interventions/c1-validation")
        validation.raise_for_status()
        real = validation.json()
        if (real["baseline"]["prediction_source"] != "GA-RGCA-v3"
                or real["intervention_cards"] or len(real["variants"]) != 3
                or any(row["prediction"]["prediction_source"] != "GA-RGCA-v3"
                       for row in real["variants"])):
            raise RuntimeError("C1 validation provenance or no-card boundary failed")

        methods = {}
        for method in ("bounded_search", "dice", "face_graph"):
            response = client.post(c2_url + "/interventions/c1-research",
                                   json=demo_request(method).model_dump(mode="json"))
            response.raise_for_status()
            body = response.json()
            if body["baseline"]["prediction_source"] != "SIMULATED_TEST_ONLY":
                raise RuntimeError(f"{method} test output provenance changed")
            methods[method] = {"mode": body["mode"], "cards": len(body["cards"]),
                               "rejected_or_unresolved": len(body["rejected_or_unresolved"])}

        empty = client.post(c2_url + "/interventions/c1-research",
                            json=demo_request(scenario="no_solution").model_dump(mode="json"))
        empty.raise_for_status()
        if empty.json()["cards"]:
            raise RuntimeError("no-solution test unexpectedly returned a card")

        prices = client.get(c2_url + "/interventions/price-references")
        prices.raise_for_status()
        price_rows = prices.json()["records"]
        reference = official_price_demo(food_id="mysore_dhall_average", quantity=Decimal("100"),
                                        unit="g", as_of=date.today())["official_reference"]
        if (not any(row["food_id"] == "mysore_dhall_average" for row in price_rows)
                or reference["indicative_reference_cost_lkr"] != "33.452"):
            raise RuntimeError("official reference conversion changed")

        blocked_request = demo_request().model_copy(update={"mode": "real"}).model_dump(mode="json")
        blocked = client.post(c2_url + "/interventions/c1-research", json=blocked_request)
        if blocked.status_code not in (401, 503):
            raise RuntimeError(f"unexpected real-mode gate response: HTTP {blocked.status_code}")

    return {
        "c1": {"loaded": True, "model_version": info.json()["model_version"],
               "clinical_use": info.json()["clinical_use"]},
        "real_model_validation": {
            "fixture_provenance": real["fixture_provenance"],
            "original_feeding": real["original_feeding"],
            "baseline": real["baseline"],
            "variants": real["variants"],
            "intervention_cards": 0,
        },
        "research_test_methods": methods,
        "no_solution_cards": 0,
        "official_price_reference": reference,
        "official_price_record_count": len(price_rows),
        "real_recommendation_gate_http": blocked.status_code,
        "real_recommendations": "BLOCKED: no approved policy, authorization or verified food feasibility",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live C1/C2 supervisor demonstration")
    parser.add_argument("--c1-url", default="http://127.0.0.1:8001")
    parser.add_argument("--c2-url", default="http://127.0.0.1:8000")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(c1_url=args.c1_url.rstrip("/"), c2_url=args.c2_url.rstrip("/")),
                     indent=None if args.compact else 2))


if __name__ == "__main__":
    main()
