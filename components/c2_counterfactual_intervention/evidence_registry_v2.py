"""Publication-level evidence registry for the dietary scenario workflow.

Only the WHO age scope is promoted to an automated rule. Other documents are
listed for traceability while their individual practice/portion rules await
section-level review.
"""
from copy import deepcopy

EVIDENCE = (
    {
        "source_id": "WHO-CF-2023", "issuing_organization": "World Health Organization",
        "document_title": "WHO Guideline for complementary feeding of infants and young children 6-23 months of age",
        "document_year": 2023, "version": "ISBN 978-92-4-008186-4",
        "official_url": "https://www.who.int/publications/i/item/9789240081864",
        "verified_section_or_page": "publication overview", "age_min_months": 6,
        "age_max_months": 23, "criterion_id": "complementary_feeding_age_scope",
        "criterion_description": "The publication explicitly covers complementary feeding at ages 6-23 months.",
        "verification_status": "verified_publication_scope_only",
        "retrieval_date": "2026-10-19",
        "limitations": "No individual meal count, portion, nutrient-adequacy or treatment rule extracted.",
    },
    {
        "source_id": "FHB-CF-2025", "issuing_organization": "Sri Lanka Family Health Bureau",
        "document_title": "Booklet on complementary feeding for caregivers - E English",
        "document_year": 2025, "version": "publication listing",
        "official_url": "https://fhb.health.gov.lk/technical-units/child-nutrition",
        "verified_section_or_page": "Child Nutrition Unit publications index",
        "age_min_months": None, "age_max_months": None,
        "criterion_id": "practice_details_pending_review",
        "criterion_description": "Official resource is listed; no individual practice rule is encoded.",
        "verification_status": "index_verified_content_unreviewed",
        "retrieval_date": "2026-10-19",
        "limitations": "Publication age scope, detailed recommendations and portions require source review.",
    },
    {
        "source_id": "MOH-FBDG-HANDBOOK", "issuing_organization": "Sri Lanka Ministry of Health Nutrition Division",
        "document_title": "Food Based Dietary Guidelines for Sri Lankans - Practitioner's Handbook",
        "document_year": None, "version": "resources listing",
        "official_url": "https://nutrition.health.gov.lk/english/resources/",
        "verified_section_or_page": "Nutrition Division resources index",
        "age_min_months": None, "age_max_months": None,
        "criterion_id": "food_group_examples_not_adequacy",
        "criterion_description": "Food groups are examples only; no individual nutrient criterion is encoded.",
        "verification_status": "index_verified_practice_unreviewed",
        "retrieval_date": "2026-10-19",
        "limitations": "Do not apply 6-23 month WHO scope to ages 24-59 or infer dietary adequacy from variety labels.",
    },
)


def registry() -> list[dict]:
    return deepcopy(list(EVIDENCE))
