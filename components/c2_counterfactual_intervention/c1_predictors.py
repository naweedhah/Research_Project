"""Isolated C1-shaped simulator and fail-closed genuine inference HTTP adapter."""
import os
from typing import Any

import httpx

from .c1_compat import C1Output, C1Snapshot, DIVERSITY, MEALS


class C1PredictionUnavailable(RuntimeError):
    pass


def parse_c1_output(raw: dict[str, Any], *, real: bool, expected_version: str) -> C1Output:
    try:
        detail = raw["calibrated_probabilities"]["ga_rgca"]
        snapshot = detail.get("input_snapshot")
        output = C1Output(
            underweight_probability=detail["underweight_probability"],
            stunting_probability=detail["stunting_probability"],
            acute_probabilities={"Normal": detail["normal_acute_probability"],
                                 "MAM": detail["mam_probability"], "SAM": detail["sam_probability"]},
            predicted_malnutrition_type=detail["predicted_malnutrition_type"],
            acute_status=detail["acute_status"], severity=raw["severity"],
            severity_probabilities=detail["severity_probabilities"],
            uncertainty_flag=detail["uncertainty_flag"], model_version=raw["model_version"],
            calibration_version=raw["calibration_version"],
            feature_schema_version=raw["feature_schema_version"],
            prediction_source=raw["prediction_source"], prediction_task=raw["prediction_task"],
            score_kind=raw["score_kind"], score_is_probability=raw["score_is_probability"],
            score_is_calibrated=raw["score_is_calibrated"], clinical_use=raw["clinical_use"],
            data_limitations=raw["data_limitations"], mode=raw["mode"], input_snapshot=snapshot,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise C1PredictionUnavailable("C1 response is incomplete or invalid") from exc
    if real and (output.prediction_source != "GA-RGCA-v3" or output.mode != "PYTORCH" or
                 output.model_version != expected_version or output.score_kind != "highest_condition_probability" or
                 not output.score_is_probability or output.score_is_calibrated or
                 raw.get("status") != output.predicted_malnutrition_type or
                 detail.get("severity") != output.severity):
        raise C1PredictionUnavailable("C1 response is demo, incompatible, or has invalid score semantics")
    return output


class SimulatedC1Predictor:
    """Arbitrary deterministic fixture, never a real GA-RGCA model or treatment effect."""
    source = "SIMULATED_TEST_ONLY"

    def __init__(self, scenario: str = "favorable"):
        if scenario not in {"favorable", "unchanged", "worsening", "uncertain"}:
            raise ValueError("unknown simulator scenario")
        self.scenario = scenario

    def predict(self, snapshot: C1Snapshot, changes: dict[str, str] | None = None) -> C1Output:
        context = snapshot.predict_payload(changes)["ga_rgca_context"]
        m, d = MEALS.index(context["meal_frequency"]), DIVERSITY.index(context["dietary_diversity"])
        score = m + d
        if changes and self.scenario == "unchanged":
            score = MEALS.index(snapshot.ga_rgca_context["meal_frequency"]) + DIVERSITY.index(snapshot.ga_rgca_context["dietary_diversity"])
        elif changes and self.scenario == "worsening":
            score = max(0, MEALS.index(snapshot.ga_rgca_context["meal_frequency"]) +
                        DIVERSITY.index(snapshot.ga_rgca_context["dietary_diversity"]) - 1)
        if score <= 1:
            kind, acute, severity = "SAM", "SAM", "Severe"
            acute_probs = {"Normal": .10, "MAM": .15, "SAM": .75}
        elif score == 2:
            kind, acute, severity = "MAM", "MAM", "Moderate"
            acute_probs = {"Normal": .20, "MAM": .65, "SAM": .15}
        elif score == 3:
            kind, acute, severity = "Underweight", "Normal", "Moderate"
            acute_probs = {"Normal": .80, "MAM": .15, "SAM": .05}
        else:
            kind, acute, severity = "Normal", "Normal", "Normal"
            acute_probs = {"Normal": .90, "MAM": .08, "SAM": .02}
        if score == 0:
            kind = "Stunting"
        underweight = (.70, .62, .55, .46, .30)[score]
        stunting = (.72, .68, .60, .50, .35)[score]
        uncertainty = bool(changes and self.scenario == "uncertain")
        if uncertainty:
            # Fixture can exercise an unresolved candidate without changing probabilities.
            severity = "Moderate"
        severity_probs = {"normal": .1, "moderate": .2, "severe": .7} if severity == "Severe" else (
            {"normal": .2, "moderate": .7, "severe": .1} if severity == "Moderate" else
            {"normal": .8, "moderate": .15, "severe": .05})
        return C1Output(underweight_probability=underweight, stunting_probability=stunting,
                        acute_probabilities=acute_probs, predicted_malnutrition_type=kind,
                        acute_status=acute, severity=severity, severity_probabilities=severity_probs,
                        uncertainty_flag=uncertainty, model_version="C1-SHAPED-SIMULATOR-v1",
                        calibration_version="simulated-uncalibrated-v1",
                        feature_schema_version=snapshot.feature_schema_version,
                        prediction_source=self.source, prediction_task="twelve_month_nutritional_risk",
                        score_kind="arbitrary_simulator_fixture", score_is_probability=False,
                        score_is_calibrated=False, clinical_use=False, data_limitations=["SIMULATED MODEL - NOT FOR CLINICAL USE"],
                        mode="SIMULATED")


class RealC1HttpPredictor:
    source = "GA-RGCA-v3"

    def __init__(self, base_url: str | None = None, token: str | None = None, timeout: float = 5.0):
        self.base_url = (base_url or os.getenv("C1_INFERENCE_URL") or "").rstrip("/")
        self.token = token or os.getenv("C1_INFERENCE_TOKEN")
        self.timeout = min(max(timeout, .5), 10.0)
        if not self.base_url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
            raise C1PredictionUnavailable("C1 inference URL is unconfigured or insecure")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def verify(self, snapshot: C1Snapshot):
        try:
            with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
                health = client.get(self.base_url + "/health")
                info = client.get(self.base_url + "/model-info")
            if health.status_code != 200 or info.status_code != 200:
                raise C1PredictionUnavailable("C1 health or model-info unavailable")
            h, i = health.json(), info.json()
            if (not h.get("ga_rgca_loaded") or not i.get("ga_rgca_loaded") or
                i.get("prediction_source") != self.source or i.get("model_version") != snapshot.model_version):
                raise C1PredictionUnavailable("genuine C1 model artifacts/version not verified")
        except (httpx.HTTPError, ValueError) as exc:
            raise C1PredictionUnavailable("C1 service verification failed") from exc

    def predict(self, snapshot: C1Snapshot, changes: dict[str, str] | None = None) -> C1Output:
        self.verify(snapshot)
        payload = snapshot.predict_payload(changes)
        try:
            with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
                response = client.post(self.base_url + "/predict", json=payload)
            if response.status_code != 200:
                raise C1PredictionUnavailable(f"C1 prediction unavailable (HTTP {response.status_code})")
            raw = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise C1PredictionUnavailable("C1 prediction request failed") from exc
        result = parse_c1_output(raw, real=True, expected_version=snapshot.model_version)
        if result.feature_schema_version != snapshot.feature_schema_version or result.calibration_version != "ga-rgca-v3-binary-calibrators":
            raise C1PredictionUnavailable("C1 schema or calibration version mismatch")
        recorded = result.input_snapshot or {}
        values = recorded.get("values") or {}
        for feature in ("Meal_Frequency_per_Day", "Dietary_Diversity"):
            expected = payload["ga_rgca_context"]["meal_frequency" if feature.startswith("Meal") else "dietary_diversity"]
            if values.get(feature) != expected:
                raise C1PredictionUnavailable("C1 feature snapshot disagrees with requested feeding category")
        for key, value in (("Hist_2025_Height_cm", payload["historical_baseline"]["height_cm"]),
                           ("Hist_2025_Weight_kg", payload["historical_baseline"]["weight_kg"]),
                           ("Hist_2025_Age_months", payload["historical_baseline"]["age_months"])):
            if values.get(key) != value:
                raise C1PredictionUnavailable("C1 historical feature snapshot disagrees with request")
        return result
