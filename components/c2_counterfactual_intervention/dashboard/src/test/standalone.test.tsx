import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../pages/App'

const prediction = { predicted_malnutrition_type: 'Underweight', acute_status: 'Normal', severity: 'Moderate',
  uncertainty_flag: false, prediction_source: 'SIMULATED_TEST_ONLY', model_version: 'C1-SHAPED-SIMULATOR-v1', data_limitations: [] }
const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
function response(budget: string | null) {
  const plan = { title: 'Essentials example', kind: 'educational_shopping_example', rank: 1,
    food_groups: ['rice and cereals','pulses','green leafy vegetables'], group_count: 3,
    cost_period: 'weekly', budget_period: 'weekly', estimated_total_lkr: '238.48', budget_lkr: budget,
    budget_fit: budget === null ? 'unknown' : Number(budget) >= 238.48 ? 'within_budget' : 'above_budget',
    budget_remaining_lkr: budget !== null && Number(budget) >= 238.48 ? (Number(budget) - 238.48).toFixed(2) : null,
    shortfall_lkr: budget !== null && Number(budget) < 238.48 ? (238.48 - Number(budget)).toFixed(2) : null,
    price_evidence: 'fresh_reference', missing_evidence: [], ranking_reason: 'Three source-listed groups; indicative cost.',
    quantity_note: 'Illustrative purchases, not child servings.', period_note: 'Weekly example.',
    coverage_note: 'Colombo prices, local availability unknown.', guideline_scope_note: 'Broad groups only.',
    schedule_status: 'illustrative_food_pairings', schedule: days.map(day => ({ day,
      slots: [{ label: 'Morning pairing idea', foods: [{ name: 'Rice', food_group: 'rice and cereals', source_url: 'https://www.statistics.gov.lk/report.pdf' }] }],
      variety_explanation: 'Illustrative pairing, not dietary adequacy.' })),
    items: [{ food_id: 'rice', name: 'Rice', food_group: 'rice and cereals', quantity: '0.5', unit: 'kg',
      published_unit_price_lkr: '193.22', published_quantity: '1', published_unit: 'kg', indicative_cost_lkr: '96.61',
      source_title: 'Department of Census and Statistics', source_url: 'https://www.statistics.gov.lk/report.pdf',
      source_locator: 'page 3', market_coverage: 'Colombo District', observation_end: '2026-10-07', price_status: 'fresh_reference' }] }
  return { mode: 'standalone_research_test', case_id: 'synthetic_24m', input_fingerprint: 'mock-fixture-fingerprint',
    profile: { test_id: 'SYNTHETIC-C2-24M', age_months: 24, historical_height_cm: 80, historical_weight_kg: 10,
      provenance: 'fully synthetic C2 demonstration profile' },
    original_feeding: { meal_frequency: '3 meals/day', dietary_diversity: 'More than 5 varieties' }, baseline: prediction,
    methods: ['bounded_search','dice','face_graph'].map(name => ({ name, mode: 'SIMULATED_TEST_ONLY', eligible_count: 1, rejected_count: 0 })),
    cards: [{ rank: 1, changes: { meal_frequency: '4+ meals/day' }, supporting_methods: ['bounded_search','dice','face_graph'],
      prediction: { ...prediction, predicted_malnutrition_type: 'Normal' }, research_test_feasibility: 'feasible under supplied test assertions',
      fixture_affordability: 'affordable', fixture_price_scope: 'supplied_price', fixture_availability: 'available',
      status: 'Eligible in Research Test', professional_review_required: true, explanation: 'Synthetic policy passed.',
      real_world_suitability: 'unknown', real_world_availability: 'unknown', food_plans: [plan],
      food_plan_relationship: 'Educational only.' }], rejected_or_unresolved: [], food_plans: [plan],
    guidance: { age_band: '24-59 months (older-child category)', status: 'published_food_groups_only_practice_pending_review',
      reference: null, food_groups: ['rice and cereals'], quantity: null, note: 'Broad food groups only.' },
    budget: { amount_lkr: budget, period: 'weekly', provenance: 'demonstration amount' },
    clinical_use: false, c1_required: false, message: 'Research test only.' }
}
const fetchMock = vi.fn()
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('runs standalone without C1 and advances or resets an illustrative schedule', async () => {
  fetchMock.mockImplementation((url: string, init?: RequestInit) => {
    if (String(url).includes('local-validation-profiles')) return Promise.resolve({ ok: false, status: 503, json: async () => ({ detail: 'Not configured' }) })
    return Promise.resolve({ ok: true, status: 200, json: async () => response(JSON.parse(String(init?.body)).budget_lkr) })
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/research-test']}><App/></MemoryRouter></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: /Generate intervention plans/ }))
  expect(await screen.findByText('Rank #1', {}, { timeout: 10000 })).toBeInTheDocument()
  expect(screen.getByText(/Test predictor - plans are examples for professional review/)).toBeInTheDocument()
  expect(screen.getByText(/LKR 1261.52/)).toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => String(url) === '/interventions/standalone-analysis')).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'View 7-Day Plan' }))
  expect(screen.getByText('Monday')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Continue Plan/ }))
  expect(screen.getByText('Tuesday')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Mark demo day completed' }))
  expect(screen.getByText('1/7 demo days')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Reset schedule/ }))
  expect(screen.getByText('Monday')).toBeInTheDocument()
  expect(screen.getByText('0/7 demo days')).toBeInTheDocument()
  const print = vi.spyOn(window, 'print').mockImplementation(() => {})
  fireEvent.click(screen.getByRole('button', { name: 'Print Plan' }))
  await waitFor(() => expect(print).toHaveBeenCalledOnce())
  print.mockRestore()
  fireEvent.click(screen.getByRole('link', { name: /Change profile or budget/ }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Food budget LKR' }), { target: { value: '100' } })
  fireEvent.click(screen.getByRole('button', { name: /Generate intervention plans/ }))
  expect(await screen.findByText(/LKR 138.48/)).toBeInTheDocument()
  expect(screen.getByText('Rank #1')).toBeInTheDocument()
  expect(screen.getAllByText(/above budget/i).length).toBeGreaterThan(0)
}, 25000)

it('keeps research-test cards when optional genuine C1 verification is offline', async () => {
  fetchMock.mockImplementation((url: string, init: RequestInit) => {
    if (String(url).includes('local-validation-profiles')) return Promise.resolve({ ok: false, status: 503,
      json: async () => ({ detail: 'Not configured' }) })
    if (String(url).includes('standalone-validation')) return Promise.resolve({ ok: false, status: 503,
      json: async () => ({ detail: 'C1 inference URL is unconfigured' }) })
    return Promise.resolve({ ok: true, status: 200,
      json: async () => response(JSON.parse(String(init.body)).budget_lkr) })
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/research-test']}><App/></MemoryRouter></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: /Generate intervention plans/ }))
  expect(await screen.findByText('Rank #1')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Real GA-RGCA Validation Evidence/ }))
  expect(await screen.findByText(/C1 unavailable — standalone plans remain available/)).toBeInTheDocument()
  expect(screen.getByText('Rank #1')).toBeInTheDocument()
}, 15000)

it('shows a local model-only comparison with its food option without approving it', async () => {
  // Contract stub only; the live C1 end-to-end check is run separately.
  const real = { predicted_malnutrition_type: 'Underweight', acute_status: 'Normal', severity: 'Moderate',
    uncertainty_flag: false, prediction_source: 'GA-RGCA-v3', model_version: 'GA-RGCA-v3',
    underweight_probability: 0.1025, stunting_probability: 0.0399,
    acute_probabilities: { Normal: 0.8795, MAM: 0.1201, SAM: 0.0004 },
    severity_probabilities: { normal: 0.1, moderate: 0.8, severe: 0.1 },
    prediction_task: 'twelve_month_nutritional_risk', clinical_use: false, data_limitations: [] }
  const candidate = { changes: { dietary_diversity: { from: 'Less than 2 varieties', to: '2 to 5 varieties' } },
    prediction: { ...real, predicted_malnutrition_type: 'Normal', underweight_probability: 0.0612 },
    probability_delta: { underweight: -0.0413, stunting: -0.0033, MAM: -0.007, SAM: 0 },
    model_rule_pass: true, reasons: [], improvement_signal: true, mixed_tradeoff: false,
    worsening_signal: false, adjacent_policy_transition: true, only_feeding_fields_changed: true,
    research_authorized: false, clinical_use: false }
  const plan = response('500').food_plans[0]
  const local = { mode: 'local_phm_model_validation', case_id: 'PHM-LOCAL-0118',
    source_sha256: 'fixture-hash', input_fingerprint: 'fixture-input-hash',
    profile: { age_months: 16, sex: 'Female', historical_height_cm: 74, historical_weight_kg: 7.7,
      original_feeding: { meal_frequency: '3 meals/day', dietary_diversity: 'Less than 2 varieties' },
      provenance: 'local research contract fixture' },
    baseline: real, candidates: [candidate], model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
    cards: [{ rank: 1, candidate, food_plans: [plan], status: 'Passed model comparison only — unresolved' }],
    food_plans: [plan], guidance: response('500').guidance,
    budget: { amount_lkr: '500', period: 'weekly', provenance: 'user-entered test amount' },
    research_authorized: false, clinical_use: false, limitations: ['Not approved for intervention.'] }
  fetchMock.mockImplementation((url: string) => {
    if (String(url).includes('local-validation-profiles')) return Promise.resolve({ ok: true, status: 200,
      json: async () => ({ available: true, source_sha256: 'fixture-hash', scanned_profiles: 1,
        profiles: [{ case_id: 'PHM-LOCAL-0118', age_months: 16, model_status: 'model_rule_signal',
          source_label: 'Linked PHM research record', feeding_provenance: 'unverified' }], limitations: 'Research only.' }) })
    if (String(url).endsWith('/interventions/local-validation')) return Promise.resolve({ ok: true, status: 200,
      json: async () => local })
    if (String(url).endsWith('/interventions/standalone-analysis')) return Promise.resolve({ ok: true, status: 200,
      json: async () => response('500') })
    return Promise.resolve({ ok: false, status: 404, json: async () => ({ detail: 'Unexpected call' }) })
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/research-test']}><App/></MemoryRouter></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Local C1 validation profiles' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Food budget LKR' }), { target: { value: '500' } })
  fireEvent.click(screen.getByRole('button', { name: 'Validate with real C1' }))
  expect(await screen.findByText(/Model-rule-passing comparisons \(1\)/)).toBeInTheDocument()
  expect(screen.getByText(/No intervention is authorized/)).toBeInTheDocument()
  expect(screen.queryByText('allow_demo=false')).not.toBeInTheDocument()
  expect(screen.getByText('Genuine model response')).toBeInTheDocument()
  expect(screen.getByText(/Illustrative 7-day food option/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next example day' }))
  expect(screen.getByText(/Tuesday · day 2\/7/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'View standalone research-test plans' }))
  fireEvent.click(screen.getByRole('button', { name: /Generate intervention plans/ }))
  expect(await screen.findByText('Rank #1')).toBeInTheDocument()
}, 15000)
