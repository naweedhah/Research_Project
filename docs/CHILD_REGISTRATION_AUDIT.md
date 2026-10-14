# Child Registration & Baseline Assessment Audit

Audit date: 2026-08-22  
Scope: separation of **Register Child** (identity/admin) from **Baseline V0** (multimodal assessment).

## Current problems → corrections

| Problem | File(s) | Why wrong | Correction |
|---------|---------|-----------|------------|
| Registration redirected straight to visit wizard | `register-child-modal.tsx` | Collapsed registration + assessment | Redirect to child profile with success banner; V0 started explicitly |
| Missing operational identity fields | `ChildCreate`, `Child` model | Only pseudonymous ID + DOB | Added encrypted `full_name`, required hospital ID, care assignment, location |
| Caregiver relationship default `"mother"` | `schemas/common.py`, modal | Silent default | Required select from config |
| No facility-scoped hospital ID uniqueness | `children.py` | Duplicate MRNs possible | `external_patient_id_hash` + unique index per facility |
| Inference invented missing measurements | `inference/app/main.py` | weight=8, height=70, muac=12 defaults | Require weight/height; no silent defaults |
| `immunization_uptodate` default `true` | `visits/new/page.tsx` | Unknown treated as Yes | Tri-state Yes/No/Unknown/Not assessed |
| Medical booleans default `false` | visit wizard checkboxes | Unchecked = No | Tri-state selects; submit `null` for unknown |
| `SocioeconomicIn.household_changed` default `True` | `schemas/common.py` | Conflicts with carry-forward UI | Default `False` |
| Sex editable on visit | visit wizard step 1 | Should load from profile | Read-only from child record |
| Age manually entered | visit wizard | Should be visit_date − DOB | Auto-calculated read-only |
| Profile showed metrics before V0 | `child-profile-dashboard.tsx` | Fake clinical picture | "Not available" until baseline exists |
| Clinician review before assessment | `child/[childId]/page.tsx` | No prediction to review | Hidden until baseline completed |
| Prediction at registration | N/A (already correct) | — | Verified: POST `/children` does not run inference |

## Remaining research-dependent items

- Structured clinician review entity (currently clinical notes)
- Full food-group picker in dietary step (schema supports; UI partial)
- WHO z-score engine (out of C1 scope)
- PHM area master data (optional free text + demo MOH lists)
- Tri-state DB columns (currently `null` in API for unknown)

## Workflow after fix

```text
Register Child (modal) → Child Profile (no assessment) → Start Baseline V0 → Wizard → AI Assessment → Clinician Review
```
