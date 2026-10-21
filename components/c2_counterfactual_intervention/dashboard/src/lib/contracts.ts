import { z } from 'zod'

export const meals = ['2 meals/day', '3 meals/day', '4+ meals/day'] as const
export const diversity = ['Less than 2 varieties', '2 to 5 varieties', 'More than 5 varieties'] as const
export const methods = ['bounded_search', 'dice', 'face_graph'] as const
export const scenarios = ['favorable', 'unchanged', 'worsening', 'uncertain', 'no_solution', 'unknown_availability', 'unaffordable', 'too_young'] as const

export const profileSchema = z.object({
  pseudonym: z.string().trim().regex(/^SYNTHETIC-[A-Z0-9-]{3,60}$/, 'Use a synthetic ID beginning with SYNTHETIC-; never enter a real identifier.'),
  age: z.coerce.number<number>().int().min(0).max(59),
  height: z.coerce.number<number>().finite().positive(),
  weight: z.coerce.number<number>().finite().positive(),
  meal: z.enum(meals),
  diversity: z.enum(diversity),
  method: z.enum(methods),
  scenario: z.enum(scenarios),
})
export type Profile = z.infer<typeof profileSchema>

const prediction = z.object({
  predicted_malnutrition_type: z.string(), acute_status: z.string(), severity: z.string(),
  uncertainty_flag: z.boolean(), prediction_source: z.string(), model_version: z.string(),
  data_limitations: z.array(z.string()),
})
const change = z.record(z.string(), z.string())
export const resultSchema = z.object({
  mode: z.string(), method: z.string(), banner: z.string(), baseline: prediction,
  candidates: z.array(z.object({ changes: change, candidate: prediction }).passthrough()),
  cards: z.array(z.object({
    rank: z.number(), changes: change, explanation: z.string(),
    feasibility_status: z.string(), professional_review_required: z.boolean(),
  }).passthrough()),
  rejected_or_unresolved: z.array(z.object({
    changes: change, status: z.string(), reasons: z.array(z.string()),
  }).passthrough()),
  message: z.string(), c1_integrated: z.boolean(), clinical_use: z.boolean(),
})
export type ResearchResult = z.infer<typeof resultSchema>

export const statusSchema = z.object({
  component: z.number(), test_engine_ready: z.boolean(), c1_integrated: z.boolean(),
  real_model_registered: z.boolean(), clinical_ready: z.boolean(), methods: z.array(z.string()),
})
export type EngineStatus = z.infer<typeof statusSchema>

const realPrediction = z.object({
  predicted_malnutrition_type: z.string(), acute_status: z.string(), severity: z.string(),
  underweight_probability: z.number(), stunting_probability: z.number(),
  acute_probabilities: z.record(z.string(), z.number()),
  severity_probabilities: z.record(z.string(), z.number()),
  uncertainty_flag: z.boolean(), model_version: z.string(), prediction_source: z.literal('GA-RGCA-v3'),
  prediction_task: z.string(), clinical_use: z.literal(false), data_limitations: z.array(z.string()),
})
export const validationSchema = z.object({
  banner: z.string(), fixture_provenance: z.string(), original_feeding: z.record(z.string(), z.string()),
  baseline: realPrediction,
  variants: z.array(z.object({
    changes: z.record(z.string(), z.object({ from: z.string(), to: z.string() })),
    prediction: realPrediction,
    comparison: z.object({ type_changed: z.boolean(), severity_changed: z.boolean(),
      underweight_probability_delta: z.number(), stunting_probability_delta: z.number() }),
    disposition: z.literal('unresolved_for_intervention'), reasons: z.array(z.string()),
  })),
  intervention_cards: z.array(z.never()), clinical_use: z.literal(false), limitations: z.array(z.string()),
})
export type ValidationResult = z.infer<typeof validationSchema>

export const pricesSchema = z.object({
  as_of: z.string(), banner: z.string(), limitations: z.string(),
  records: z.array(z.object({
    food_id: z.string(), commodity: z.string(), amount_lkr: z.string(), quantity: z.string(),
    unit: z.string(), source_institution: z.string(), source_url: z.string(), source_locator: z.string(),
    publication_date: z.string().nullable(), observation_start: z.string(), observation_end: z.string(),
    period_date_basis: z.string(), market_coverage: z.string(), reference_status: z.string(),
  })),
})

export type ResearchRequest = {
  mode: 'simulated'; method: typeof methods[number]; simulator_case: 'favorable' | 'unchanged' | 'worsening' | 'uncertain';
  snapshot: Record<string, unknown> & { child_pseudonymous_id: string; historical_baseline: Record<string, unknown>; ga_rgca_context: Record<string, unknown> };
  context: Record<string, unknown>; policy: Record<string, unknown>; food_planning: Record<string, unknown> | null; max_cards: number;
}

export const automaticCaseIds = ['synthetic_5m', 'synthetic_24m', 'synthetic_59m'] as const
export type AutomaticCaseId = typeof automaticCaseIds[number]
const automaticPrediction = z.object({
  predicted_malnutrition_type: z.string(), acute_status: z.string(), severity: z.string(),
  underweight_probability: z.number(), stunting_probability: z.number(),
  acute_probabilities: z.record(z.string(), z.number()), severity_probabilities: z.record(z.string(), z.number()),
  uncertainty_flag: z.boolean(), model_version: z.string(), prediction_source: z.literal('GA-RGCA-v3'),
  prediction_task: z.string(), clinical_use: z.literal(false), data_limitations: z.array(z.string()),
})
const guidance = z.object({ age_band: z.string(), status: z.string(),
  reference: z.object({ institution: z.string(), title: z.string(), url: z.string(), section: z.string(), review_status: z.string().optional() }).nullable(),
  food_groups: z.array(z.string()), quantity: z.null(), note: z.string() })
export const automaticBaselineSchema = z.object({
  case_id: z.enum(automaticCaseIds), snapshot_provenance: z.string(), age_months: z.number(),
  original_feeding: z.record(z.string(), z.string()), baseline: automaticPrediction.nullable(),
  guidance, clinical_use: z.literal(false),
})
export const automaticResultSchema = automaticBaselineSchema.extend({
  mode: z.enum(['genuine_c1_model_comparison_only', 'unsupported_age_no_prediction']), model_version: z.string().nullable(),
  candidates: z.array(z.object({
    changes: z.record(z.string(), z.object({ from: z.string(), to: z.string() })),
    prediction: automaticPrediction,
    comparison: z.object({ type_changed: z.boolean(), severity_changed: z.boolean(),
      underweight_probability_delta: z.number(), stunting_probability_delta: z.number() }),
    disposition: z.string(), reasons: z.array(z.string()), method: z.literal('bounded_search'),
    rank: z.number().nullable(), food_options: z.array(z.unknown()),
    indicative_incremental_cost_lkr: z.null(), affordability: z.literal('unresolved'),
    availability: z.literal('unknown'), professional_review_required: z.literal(true),
  })),
  approved_intervention_cards: z.array(z.never()),
  shopping_examples: z.array(z.object({ title: z.string(), kind: z.literal('educational_shopping_example'), rank: z.number(),
    food_groups: z.array(z.string()), group_count: z.number(), cost_period: z.string(), budget_period: z.string(),
    estimated_total_lkr: z.string().nullable(), budget_lkr: z.string().nullable(), budget_fit: z.enum(['within_budget','above_budget','unknown']),
    price_evidence: z.string(), missing_evidence: z.array(z.string()), ranking_reason: z.string(),
    quantity_note: z.string(), period_note: z.string(), coverage_note: z.string(),
    items: z.array(z.object({ food_id: z.string(), name: z.string(), food_group: z.string(), quantity: z.string(), unit: z.string(),
      published_unit_price_lkr: z.string(), published_quantity: z.string(), published_unit: z.string(),
      indicative_cost_lkr: z.string(), source_title: z.string(), source_url: z.string(), source_locator: z.string(),
      market_coverage: z.string(), observation_end: z.string(), price_status: z.string() })) })),
  budget: z.object({ amount_lkr: z.string().nullable(), period: z.enum(['daily', 'weekly', 'monthly']),
    affordability: z.literal('unresolved') }),
  published_price_examples: z.array(z.object({ food_id: z.string(), food_name: z.string(),
    food_group: z.string(), amount_lkr: z.string(), quantity: z.string(), unit: z.string(),
    source_url: z.string(), source_locator: z.string(), market_coverage: z.string(),
    observation_start: z.string(), observation_end: z.string(), reference_status: z.string() })),
  methods: z.array(z.object({ name: z.string(), status: z.string() })),
  research_test_runs: z.array(z.object({ method: z.string(), status: z.string(),
    prediction_source: z.literal('SIMULATED_TEST_ONLY'), candidate_count: z.number(),
    approved_cards: z.literal(0), note: z.string() })),
  limitations: z.array(z.string()),
})
export type AutomaticResult = z.infer<typeof automaticResultSchema>

const standalonePrediction = z.object({ predicted_malnutrition_type: z.string(), acute_status: z.string(),
  severity: z.string(), uncertainty_flag: z.boolean(), prediction_source: z.literal('SIMULATED_TEST_ONLY'),
  model_version: z.string(), data_limitations: z.array(z.string()) })
const shoppingFood = z.object({ food_id: z.string(), name: z.string(), food_group: z.string(),
  quantity: z.string(), unit: z.string(), published_unit_price_lkr: z.string(),
  published_quantity: z.string(), published_unit: z.string(), indicative_cost_lkr: z.string(),
  source_title: z.string(), source_url: z.string(), source_locator: z.string(),
  market_coverage: z.string(), observation_end: z.string(), price_status: z.string() })
const scheduleDay = z.object({ day: z.string(), slots: z.array(z.object({ label: z.string(),
  foods: z.array(z.object({ name: z.string(), food_group: z.string(), source_url: z.string() })) })),
  variety_explanation: z.string() })
const standalonePlan = z.object({ title: z.string(), kind: z.literal('educational_shopping_example'),
  rank: z.number(), food_groups: z.array(z.string()), group_count: z.number(),
  cost_period: z.string(), budget_period: z.string(), estimated_total_lkr: z.string().nullable(),
  budget_lkr: z.string().nullable(), budget_fit: z.enum(['within_budget','above_budget','unknown']),
  budget_remaining_lkr: z.string().nullable(), shortfall_lkr: z.string().nullable(),
  price_evidence: z.string(), missing_evidence: z.array(z.string()), ranking_reason: z.string(),
  quantity_note: z.string(), period_note: z.string(), coverage_note: z.string(),
  guideline_scope_note: z.string(), schedule_status: z.string(), schedule: z.array(scheduleDay),
  items: z.array(shoppingFood) })
export const standaloneResultSchema = z.object({ mode: z.literal('standalone_research_test'),
  input_fingerprint: z.string(),
  case_id: z.enum(automaticCaseIds), profile: z.object({ test_id: z.string(), age_months: z.number(), historical_height_cm: z.number().nullable(), historical_weight_kg: z.number().nullable(), provenance: z.string() }),
  original_feeding: z.record(z.string(), z.string()).nullable(), baseline: standalonePrediction.nullable(),
  methods: z.array(z.object({ name: z.enum(methods), mode: z.literal('SIMULATED_TEST_ONLY'),
    eligible_count: z.number(), rejected_count: z.number() })),
  cards: z.array(z.object({ rank: z.number(), changes: z.record(z.string(), z.string()),
    supporting_methods: z.array(z.enum(methods)), prediction: standalonePrediction,
    research_test_feasibility: z.string(), fixture_affordability: z.string().nullable(),
    fixture_price_scope: z.string().nullable(), fixture_availability: z.string().nullable(),
    status: z.literal('Eligible in Research Test'), professional_review_required: z.literal(true),
    explanation: z.string(), real_world_suitability: z.literal('unknown'),
    real_world_availability: z.literal('unknown'), food_plans: z.array(standalonePlan),
    food_plan_relationship: z.string() })),
  rejected_or_unresolved: z.array(z.object({ method: z.enum(methods), changes: z.record(z.string(), z.string()),
    status: z.string(), reasons: z.array(z.string()) })),
  food_plans: z.array(standalonePlan), guidance, budget: z.object({ amount_lkr: z.string().nullable(),
    period: z.enum(['daily','weekly','monthly']), provenance: z.string() }),
  clinical_use: z.literal(false), c1_required: z.literal(false), message: z.string() })
export type StandaloneResult = z.infer<typeof standaloneResultSchema>

export const standaloneValidationSchema = z.object({
  connection: z.enum(['verified', 'not_attempted_age_inapplicable']), case_id: z.enum(automaticCaseIds), input_fingerprint: z.string(),
  profile: z.object({ test_id: z.string(), age_months: z.number(),
    historical_baseline: z.record(z.string(), z.unknown()).optional(),
    original_feeding: z.record(z.string(), z.string()).optional() }),
  baseline: realPrediction.nullable(), model_version: z.string().nullable(),
  prediction_source: z.literal('GA-RGCA-v3').nullable(), clinical_use: z.literal(false),
  candidates: z.array(z.object({ changes: z.record(z.string(), z.object({ from: z.string(), to: z.string() })),
    prediction: realPrediction, probability_delta: z.object({ underweight: z.number(), stunting: z.number(),
      acute: z.object({ Normal: z.number(), MAM: z.number(), SAM: z.number() }) }),
    model_policy_result: z.enum(['rejected', 'unresolved']), rejected_reasons: z.array(z.string()),
    unresolved_reasons: z.array(z.string()), only_feeding_fields_changed: z.literal(true) })),
  limitations: z.array(z.string()),
})
export type StandaloneValidation = z.infer<typeof standaloneValidationSchema>

export const manualC1InputSchema = z.object({
  test_id: z.string().regex(/^TEST-[0-9]{4}$/, 'Use a four-digit invented test ID such as TEST-0014.'),
  age_months: z.number().int().min(6).max(59),
  sex: z.enum(['Female', 'Male']),
  height_cm: z.number().finite().positive(), weight_kg: z.number().finite().positive(),
  birth_weight_kg: z.number().finite().positive(), household_size: z.number().int().positive(),
  maternal_age_years: z.number().int().positive(),
  maternal_education: z.enum(['No formal education', 'Below O/ Level', 'O/L passed', 'A/ Level passes', 'Degree/ diploma']),
  household_income_range: z.enum(['Less than Rs. 20,000', 'Rs.20,000 to Rs. 50,000', 'Rs. 50,000 to Rs. 100,000', 'More than Rs. 100,000']),
  father_occupation: z.enum(['Abroad', 'Government worker', 'Manual worker', 'No job', 'Private sector worker', 'Self-employed']),
  mother_occupation: z.enum(['Government worker', 'Housewife', 'Private sector worker', 'Self-employed']),
  exclusive_breastfeeding: z.enum(['Yes', 'No']),
  breastfeeding_duration: z.enum(['Less than 6 months', 'More than 6 months']),
  complementary_feeding_timing: z.enum(['Before 6 months', 'After 6 months']),
  meal_frequency: z.enum(meals), dietary_diversity: z.enum(diversity),
  triposha_supplementation: z.enum(['No', 'Yes - irregular use', 'Yes - regular use']),
  vitamin_supplementation: z.enum(['Yes', 'No']),
  historical_mam: z.boolean().nullable().optional(),
  historical_sam: z.boolean().nullable().optional(),
  historical_underweight: z.enum(['Normal', 'Moderate', 'Severe']).nullable().optional(),
  historical_stunting: z.enum(['Normal', 'Moderate', 'Severe']).nullable().optional(),
  budget_lkr: z.string().regex(/^\d+(\.\d{1,2})?$/).nullable().default(null),
  budget_period: z.enum(['daily', 'weekly', 'monthly']).default('weekly'),
})
export type ManualC1Input = z.infer<typeof manualC1InputSchema>

export const liveCaseLibraryV2Schema = z.object({
  contract_version: z.literal('c2-live-case-library-v2'),
  provenance: z.string(),
  cases: z.array(z.object({ case_id: z.string(), name: z.string(),
    input: manualC1InputSchema, food_groups: z.array(z.string()) })),
})
export type LiveCaseV2 = z.infer<typeof liveCaseLibraryV2Schema>['cases'][number]

export const liveCaseValidationV2Schema = z.object({
  mode: z.literal('live_c1_invented_case_validation'), c1_calls: z.number(),
  allow_demo: z.literal(false), clinical_use: z.literal(false),
  observed_categories: z.array(z.string()), unobserved_categories: z.array(z.string()),
  cases: z.array(z.object({ case_id: z.string(), input_name: z.string(),
    model_version: z.literal('GA-RGCA-v3'), prediction_source: z.literal('GA-RGCA-v3'),
    c1_predicted_category: z.enum(['Normal','Underweight','Stunting','MAM','SAM']),
    c1_severity: z.enum(['Normal','Moderate','Severe']), c1_uncertainty_flag: z.boolean(),
    assessment_review_needed: z.boolean(), c2_candidate_count: z.number(),
    c2_research_test_rank_count: z.number(), c2_verified_feasible_count: z.number(),
    c2_status: z.string(),
  })),
})
export type LiveCaseValidationV2 = z.infer<typeof liveCaseValidationV2Schema>

const manualC1Candidate = z.object({
  changes: z.record(z.string(), z.object({ from: z.string(), to: z.string() })),
  prediction: realPrediction.nullable(),
  probability_delta: z.object({ underweight: z.number(), stunting: z.number(),
    acute: z.object({ Normal: z.number(), MAM: z.number(), SAM: z.number() }) }).nullable(),
  model_policy_result: z.enum(['rejected', 'unresolved']),
  rejected_reasons: z.array(z.string()), unresolved_reasons: z.array(z.string()),
  only_feeding_fields_changed: z.literal(true), rank: z.number().nullable(),
})
export const manualC1ResultSchema = z.object({
  mode: z.literal('manual_genuine_c1_model_comparison'),
  submitted_input: manualC1InputSchema,
  input_fingerprint: z.string(), prediction_source: z.literal('GA-RGCA-v3'),
  model_version: z.literal('GA-RGCA-v3'), prediction_task: z.literal('twelve_month_nutritional_risk'),
  baseline: realPrediction,
  candidates: z.array(manualC1Candidate),
  ranked_model_comparisons: z.array(manualC1Candidate),
  food_plans: z.array(standalonePlan),
  budget: z.object({ amount_lkr: z.string().nullable(), period: z.enum(['daily', 'weekly', 'monthly']), affordability: z.literal('unresolved') }),
  approved_intervention_cards: z.array(z.never()), clinical_use: z.literal(false),
  limitations: z.array(z.string()),
})
export type ManualC1Result = z.infer<typeof manualC1ResultSchema>

export const c1BaselineV2Schema = z.object({
  assessment: z.object({ model_version: z.string(), prediction_source: z.literal('GA-RGCA-v3'),
    predicted_malnutrition_type: z.enum(['Normal','Underweight','Stunting','MAM','SAM']),
    severity: z.enum(['Normal','Moderate','Severe']), uncertainty_flag: z.boolean(),
    clinical_use: z.literal(false), input_fingerprint: z.string(),
    provenance: z.literal('live_c1_baseline') }),
  prediction: realPrediction, c1_calls: z.literal(1), feeding_provenance: z.literal('unverified'),
  limitations: z.array(z.string()),
})
export type C1BaselineV2 = z.infer<typeof c1BaselineV2Schema>

const scenarioCheck = z.object({ criterion: z.string(), state: z.enum(['pass','fail','unknown']),
  reason: z.string(), evidence_source: z.string().nullable() })
const scenarioCandidate = z.object({ candidate_id: z.string(), title: z.string(),
  generator_methods: z.array(z.string()).optional(),
  status: z.enum(['verified_feasible','evidence_incomplete','rejected']),
  current_food_groups: z.array(z.string()), proposed_food_groups: z.array(z.string()),
  additional_groups: z.array(z.string()), reference_cost_lkr: z.string().nullable(),
  cost_period: z.string(), reference_budget_fit: z.string(),
  items: z.array(z.object({ food_id: z.string(), name: z.string(), food_group: z.string(),
    quantity: z.string(), unit: z.string(), indicative_cost_lkr: z.string(),
    source_url: z.string(), observation_end: z.string(), market_coverage: z.string() }).passthrough()),
  schedule: z.array(z.object({ day: z.string(), slots: z.array(z.object({ label: z.string(),
    foods: z.array(z.object({ name: z.string() }).passthrough()) })) }).passthrough()),
  checks: z.array(scenarioCheck), rank: z.number().nullable(), limitations: z.array(z.string()),
}).passthrough()
export const dietScenariosV2Schema = z.object({
  contract_version: z.literal('c2-diet-scenarios-v2'), original_c1: c1BaselineV2Schema.shape.assessment,
  original_c1_unchanged: z.literal(true), c1_candidate_calls: z.literal(0),
  feeding_baseline: z.object({ meal_frequency: z.string(), dietary_diversity: z.string(),
    food_groups: z.array(z.string()), provenance: z.string() }),
  age_months: z.number(), candidate_count: z.number(), ranked_cards: z.array(scenarioCandidate),
  unresolved_or_rejected: z.array(scenarioCandidate), referral_notice: z.string().nullable(),
  ranking_trace: z.object({ status: z.string(), order: z.array(z.string()), note: z.string() }),
  method: z.enum(['dice','face_graph','wachter','bounded_search','compare_all']).optional(),
  method_results: z.record(z.string(), z.object({ status: z.string(), generated_count: z.number(),
    independently_validated_count: z.number(), verified_ranked_count: z.number(),
    rejected_or_unresolved_count: z.number(), runtime_ms: z.number(),
    diagnostics: z.record(z.string(), z.unknown()) })).optional(),
  software_test_ranked: z.array(z.object({ candidate_id: z.string(), rank: z.number(),
    title: z.string(), generator_methods: z.array(z.string()), reference_cost_lkr: z.string().nullable(),
    scope: z.string() })).optional(),
  clinical_use: z.literal(false), limitations: z.array(z.string()),
}).passthrough()
export type DietScenariosV2 = z.infer<typeof dietScenariosV2Schema>

export const localProfilesSchema = z.object({ available: z.literal(true), source_sha256: z.string(),
  scanned_profiles: z.number(), profiles: z.array(z.object({ case_id: z.string(), age_months: z.number(),
    model_status: z.string(), source_label: z.string(), feeding_provenance: z.string() })),
  limitations: z.string() })
export type LocalProfiles = z.infer<typeof localProfilesSchema>

const localCandidate = z.object({
  changes: z.record(z.string(), z.object({ from: z.string(), to: z.string() })),
  prediction: realPrediction,
  probability_delta: z.object({ underweight: z.number(), stunting: z.number(), MAM: z.number(), SAM: z.number() }),
  model_rule_pass: z.boolean(), reasons: z.array(z.string()),
  improvement_signal: z.boolean(), mixed_tradeoff: z.boolean(), worsening_signal: z.boolean(),
  adjacent_policy_transition: z.boolean(), only_feeding_fields_changed: z.literal(true),
  research_authorized: z.literal(false), clinical_use: z.literal(false),
})
export const localValidationSchema = z.object({ mode: z.literal('local_phm_model_validation'),
  case_id: z.string(), source_sha256: z.string(), input_fingerprint: z.string(),
  profile: z.object({ age_months: z.number(), sex: z.string().nullable(),
    historical_height_cm: z.number(), historical_weight_kg: z.number(),
    original_feeding: z.record(z.string(), z.string()), provenance: z.string() }),
  baseline: realPrediction, candidates: z.array(localCandidate),
  model_version: z.literal('GA-RGCA-v3'), prediction_source: z.literal('GA-RGCA-v3'),
  cards: z.array(z.object({ rank: z.number(), candidate: localCandidate,
    food_plans: z.array(standalonePlan), status: z.string() })),
  food_plans: z.array(standalonePlan), guidance,
  budget: z.object({ amount_lkr: z.string().nullable(), period: z.enum(['daily','weekly','monthly']), provenance: z.string() }),
  research_authorized: z.literal(false), clinical_use: z.literal(false), limitations: z.array(z.string()),
})
export type LocalValidation = z.infer<typeof localValidationSchema>
