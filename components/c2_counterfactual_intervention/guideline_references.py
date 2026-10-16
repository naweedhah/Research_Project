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
