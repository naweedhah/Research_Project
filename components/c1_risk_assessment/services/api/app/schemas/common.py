from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def _normalize_email(value: str) -> str:
    text = value.strip()
    local, _, domain = text.partition("@")
    if not local or "." not in domain:
        raise ValueError("value is not a valid email address")
    return text.lower()


# email-validator rejects reserved TLDs such as .local, which the demo accounts use.
AppEmail = Annotated[str, AfterValidator(_normalize_email)]


def _optional_whole_number(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter a number") from exc
    if number != number:
        raise ValueError("Enter a number")
    return int(round(number))


OptionalWholeNumber = Annotated[int | None, BeforeValidator(_optional_whole_number)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: AppEmail
    password: str
    remember_me: bool = False


class UserOut(ORMModel):
    id: UUID
    email: AppEmail
    full_name: str
    qualifications: str | None = None
    experience: str | None = None
    role: str
    status: str
    facility_id: UUID
    facility_name: str | None = None
    facility_code: str | None = None
    permissions: list[str] = Field(default_factory=list)


class TokenUserResponse(BaseModel):
    user: UserOut
    csrf_token: str
    disclaimer: str


class ChildCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: date
    sex: str
    external_patient_id: str = Field(min_length=1, max_length=80)
    facility_id: UUID | None = None
    responsible_team: str = Field(min_length=1, max_length=120)
    assigned_doctor_id: UUID | None = None
    district: str | None = None
    moh_area: str | None = None
    phm_area: str | None = None
    caregiver_relationship: str = Field(min_length=1, max_length=40)
    caregiver_display_name: str | None = None
    caregiver_phone: str | None = None
    reminder_consent: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @field_validator("caregiver_phone")
    @classmethod
    def phone_format(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 9 or len(digits) > 15:
            raise ValueError("Contact number must contain 9–15 digits")
        return v.strip()


class ChildUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    date_of_birth: date | None = None
    sex: str | None = None
    responsible_team: str | None = None
    status: str | None = None
    external_patient_id: str | None = Field(default=None, min_length=1, max_length=80)
    assigned_doctor_id: UUID | None = None
    district: str | None = None
    moh_area: str | None = None
    phm_area: str | None = None
    caregiver_relationship: str | None = Field(default=None, max_length=40)
    caregiver_display_name: str | None = None
    caregiver_phone: str | None = None
    reminder_consent: bool | None = None

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @field_validator("caregiver_phone")
    @classmethod
    def phone_format(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 9 or len(digits) > 15:
            raise ValueError("Contact number must contain 9–15 digits")
        return v.strip()


class ClinicalAttentionItem(BaseModel):
    type: str
    label: str
    severity: str | None = None
    status: str | None = None


class MeasurementsSummary(BaseModel):
    weight_kg: float | None = None
    height_cm: float | None = None
    muac_cm: float | None = None
    previous_weight_kg: float | None = None
    previous_muac_cm: float | None = None


class ChildListItem(ORMModel):
    id: UUID
    pseudonymous_id: str
    full_name: str | None = None
    age_months: int
    sex: str
    responsible_team: str | None = None
    last_visit: datetime | None = None
    latest_visit_number: int | None = None
    visit_count: int = 0
    assessment_count: int = 0
    has_assessment: bool = False
    current_status: str | None = None
    predicted_malnutrition_type: str | None = None
    detected_conditions: list[str] | None = None
    severity: str | None = None
    current_risk: float | None = None
    previous_risk: float | None = None
    risk_change_pp: int | None = None
    probability_label: str = "Demo Progression Score"
    score_kind: str | None = None
    prediction_confidence: str | None = None
    risk_velocity_pp_month: float | None = None
    risk_velocity_available: bool = False
    progress: str | None = None
    progress_display: str | None = None
    progress_warning: str | None = None
    probability_history: list[float] = Field(default_factory=list)
    clinical_attention: list[ClinicalAttentionItem] = Field(default_factory=list)
    clinician_review_status: str = "NOT_REQUIRED"
    next_follow_up: date | None = None
    follow_up_status: str | None = None
    follow_up_display_status: str | None = None
    follow_up_overdue_days: int | None = None
    measurements: MeasurementsSummary | None = None
    facility_code: str | None = None
    alert_type: str | None = None
    alert_severity: str | None = None
    requires_attention: bool = False
    priority_score: int = 0
    model_is_demo: bool = False


class AnthropometricIn(BaseModel):
    age_months: float
    sex: str
    height_cm: float | None = None
    weight_kg: float | None = None
    muac_cm: float | None = None
    birth_weight_kg: float | None = None
    head_circumference_cm: float | None = None
    previous_weight_kg: float | None = None
    previous_height_cm: float | None = None


class SocioeconomicIn(BaseModel):
    wealth_proxy: str | None = None
    maternal_education: str | None = None
    paternal_education: str | None = None
    maternal_employment: str | None = None
    household_size: OptionalWholeNumber = None
    geographical_area: str | None = None
    drinking_water: str | None = None
    sanitation: str | None = None
    household_changed: bool = False


class DietaryIn(BaseModel):
    breastfeeding_status: str | None = None
    breastfeeding_duration_months: float | None = None
    complementary_feeding: bool | None = None
    dietary_diversity_score: OptionalWholeNumber = None
    meal_frequency: OptionalWholeNumber = None
    food_groups: list[str] | None = None
    micronutrient_supplementation: bool | None = None


class MaternalIn(BaseModel):
    maternal_bmi: float | None = None
    gestational_age_weeks: OptionalWholeNumber = None
    immunization_uptodate: bool | None = None
    vitamin_a: bool | None = None
    recent_diarrhoea: bool | None = None
    recent_respiratory_illness: bool | None = None
    recent_hospitalization: bool | None = None
    birth_characteristics: str | None = None


class GaRgcaContextIn(BaseModel):
    """Training-category answers for GA-RGCA. Empty means not recorded."""

    maternal_age_years: float | None = None
    maternal_education: str | None = None
    household_income_range: str | None = None
    father_occupation: str | None = None
    mother_occupation: str | None = None
    exclusive_breastfeeding: str | None = None
    breastfeeding_duration: str | None = None
    complementary_feeding_timing: str | None = None
    meal_frequency: str | None = None
    dietary_diversity: str | None = None
    triposha_supplementation: str | None = None
    vitamin_supplementation: str | None = None
    historical_mam: int | None = None
    historical_sam: int | None = None
    historical_underweight: str | None = None
    historical_stunting: str | None = None


class VisitCreate(BaseModel):
    visit_date: datetime
    visit_type: str = "follow_up"
    scheduled: bool = True
    save_as_draft: bool = False
    confirmation_attested: bool = False
    anthropometric: AnthropometricIn
    socioeconomic: SocioeconomicIn | None = None
    dietary: DietaryIn | None = None
    maternal_child_health: MaternalIn | None = None
    ga_rgca_context: GaRgcaContextIn | None = None


class VisitCorrection(BaseModel):
    visit_date: datetime
    weight_kg: float
    height_cm: float


class VisitOut(ORMModel):
    id: UUID
    child_id: UUID
    visit_number: int
    visit_date: datetime
    visit_type: str
    status: str
    scheduled: bool
    data_quality: dict | None = None


class PredictionOut(BaseModel):
    id: UUID
    visit_id: UUID
    run_number: int
    is_active: bool
    mode: str
    status_prediction: str
    severity_prediction: str
    raw_probabilities: dict
    calibrated_probabilities: dict
    primary_risk_score: float
    confidence: str
    inference_ms: float
    model_version: str
    calibration_version: str | None = None
    demo: bool


class AlertOut(ORMModel):
    id: UUID
    child_id: UUID
    pseudonymous_id: str | None = None
    type: str
    severity: str
    status: str
    message: str
    trigger_value: dict | None = None
    created_at: datetime
    acknowledged_at: datetime | None = None


class AlertPatch(BaseModel):
    notes: str | None = None
    reason: str | None = None


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    visit_id: UUID | None = None


class NoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


class ClinicianReviewCreate(BaseModel):
    assessment: str = Field(min_length=1, max_length=80)
    workflow_action: str | None = Field(default=None, max_length=80)
    clinical_note: str | None = Field(default=None, max_length=8000)
    clinician_status: str | None = Field(default=None, max_length=40)
    clinician_severity: str | None = Field(default=None, max_length=40)


class ClinicianReviewPatch(BaseModel):
    assessment: str | None = Field(default=None, max_length=80)
    workflow_action: str | None = Field(default=None, max_length=80)
    clinical_note: str | None = Field(default=None, max_length=8000)
    clinician_status: str | None = Field(default=None, max_length=40)
    clinician_severity: str | None = Field(default=None, max_length=40)


class FollowUpCreate(BaseModel):
    expected_date: date
    interval_days: int = 30
    responsible_user_id: UUID | None = None
    notes: str | None = None
    confirm: bool = True


class FollowUpPatch(BaseModel):
    expected_date: date | None = None
    status: str | None = None
    notes: str | None = None


class CounterfactualRequest(BaseModel):
    child_id: str
    visit_id: UUID
    trigger: str
    current_prediction: dict[str, Any] = Field(default_factory=dict)
    current_risk: float
    trajectory_summary: dict[str, Any] = Field(default_factory=dict)
    model_version: str


class ChildrenListSummary(BaseModel):
    children_under_monitoring: int = 0
    requiring_clinical_attention: int = 0
    awaiting_clinical_review: int = 0
    follow_up_upcoming: int = 0
    follow_up_overdue: int = 0
    model_is_demo: bool = False


class ChildrenListPage(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    summary: ChildrenListSummary


class Page(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
