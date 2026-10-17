"""Traceable publication metadata, not automatic clinical feeding rules."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GuidelineReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution: str
    document: str
    edition: str
    url: str
    min_age_months: int | None = None
    max_age_months: int | None = None
    concept: str
    food_groups: tuple[str, ...] = ()
    exact_section: str
    restrictions: str
    review_status: Literal["published_scope_only", "index_only", "expert_approved"]

    def applies_to_age(self, age_months: int) -> bool:
        return (self.min_age_months is not None and self.max_age_months is not None
                and self.min_age_months <= age_months <= self.max_age_months)


REFERENCES = (
    GuidelineReference(
        institution="World Health Organization",
        document="WHO Guideline for complementary feeding of infants and young children 6–23 months of age",
        edition="2023", url="https://www.who.int/publications/i/item/9789240081864",
        min_age_months=6, max_age_months=23, concept="complementary feeding scope",
        exact_section="publication page, Overview",
        restrictions="Scope only. No automatic meal frequency, diversity score, or individual suitability rule.",
        review_status="published_scope_only"),
    GuidelineReference(
        institution="Sri Lanka Family Health Bureau",
        document="Booklet on complementary feeding for caregivers - E",
        edition="January 2025",
        url="https://fhb.health.gov.lk/resources/2025-booklet-on-complementary-feeding-for-caregivers-e-en",
        concept="child feeding resource listed by Child Nutrition Unit",
        exact_section="publication landing page; PDF section not reviewed",
        restrictions="Age range and practice details require document review before use as a rule.",
        review_status="index_only"),
    GuidelineReference(
        institution="Sri Lanka Ministry of Health Nutrition Division",
        document="Food Based Dietary Guidelines for Sri Lankans – Practitioner’s Handbook",
        edition="2021", url="https://nutrition.health.gov.lk/english/resources/",
        concept="national dietary guideline resource",
        exact_section="resources index; handbook section not reviewed",
        restrictions="General guidance cannot be converted to an age-specific child rule without review.",
        review_status="index_only"),
)


def applicable_references(age_months: int) -> tuple[GuidelineReference, ...]:
    return tuple(reference for reference in REFERENCES if reference.applies_to_age(age_months))


# The child food-group table is indexed in the Ministry handbook (page 102).
# These are group names only. Serving counts in the table do not establish an
# individual child's portion, model-category transition, or food suitability.
HANDBOOK_CHILD_GROUPS = (
    "rice and cereals", "vegetables", "green leafy vegetables", "pulses",
    "eggs", "fish", "fruits",
)
HANDBOOK_REFERENCE = {
    "institution": "Sri Lanka Ministry of Health Nutrition Division",
    "title": "Food Based Dietary Guidelines for Sri Lankans - Practitioner's Handbook",
    "url": "https://nutrition.health.gov.lk/wp-content/uploads/2026/07/FBDG-Practitioners-Handbook-Final-English.pdf",
    "section": "FBDG 2 (p. 19), FBDG 3 (p. 25), FBDG 4 (p. 36), FBDG 16 (p. 94), FBDG 17 (p. 106); chapter start pages in contents",
    "review_status": "published_group_scope_only; individual practice and portion review pending",
}


def research_guidance_for_age(age_months: int) -> dict:
    """Return traceable group scope, never an approved child feeding plan."""
    if not 0 <= age_months <= 59:
        raise ValueError("age outside 0-59 month cohort")
    if age_months < 6:
        return {"age_band": "under 6 months", "status": "no_complementary_feeding_candidate",
                "reference": None, "food_groups": [], "quantity": None,
                "note": "No complementary-feeding counterfactual is generated for this age band."}
    band = ("6-8 months" if age_months <= 8 else "9-11 months" if age_months <= 11 else
            "12-23 months" if age_months <= 23 else "24-59 months (older-child category)")
    return {"age_band": band, "status": "published_food_groups_only_practice_pending_review",
            "reference": HANDBOOK_REFERENCE.copy(), "food_groups": list(HANDBOOK_CHILD_GROUPS),
            "quantity": None,
            "note": "The official handbook identifies complementary feeding after six months and child food-group themes. These broad group examples do not establish age-specific portions, model-category transitions or individual suitability."}
