# Guideline evidence registry

Machine-readable fields are in `evidence_registry_v2.py`: source ID, issuer, document/title/version, official URL, verified location, age scope, criterion, verification status, retrieval date and limitation.

| Source | Verified use | Limits |
|---|---|---|
| [WHO complementary feeding guideline, 2023](https://www.who.int/publications/i/item/9789240081864) | Publication overview explicitly covers 6–23 months. | Age scope only; no individual meal count, portion or recovery rule encoded. |
| [Sri Lanka FHB Child Nutrition Unit](https://fhb.health.gov.lk/technical-units/child-nutrition) | Official index lists its 2025 English caregiver complementary-feeding booklet. | Detailed content, section and age-specific practice have not been encoded. |
| [Sri Lanka Nutrition Division resources](https://nutrition.health.gov.lk/english/resources/) | Official index lists the Food Based Dietary Guidelines practitioner handbook. | Its food-group themes are examples; individual child portions and nutritional adequacy have not been verified here. |

The bundled DCS retail references are dated main Colombo District market observations. They are not Kalmunai prices. PHM dietary-variety labels are model categories, not verified WHO Minimum Dietary Diversity observations. The new engine deliberately leaves `nutrition_adequacy` and `individual_suitability` unknown until source and professional review are supplied.
