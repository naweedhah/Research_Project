import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../pages/App'
import { initialInput } from '../pages/ManualC1Validation'

const fetchMock = vi.fn()
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('uses C1 once for the original input and never re-scores candidates or budget refreshes', async () => {
  const assessment = { model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
    predicted_malnutrition_type: 'Stunting', severity: 'Moderate', uncertainty_flag: false,
    clinical_use: false, input_fingerprint: 'original-hash', provenance: 'live_c1_baseline' }
  const prediction = { ...assessment, acute_status: 'Normal', underweight_probability: .1,
    stunting_probability: .2, acute_probabilities: { Normal: .8, MAM: .19, SAM: .01 },
    severity_probabilities: { normal: .2, moderate: .7, severe: .1 },
    prediction_task: 'twelve_month_nutritional_risk', data_limitations: [] }
  let baselineCalls = 0
  let scenarioCalls = 0
  fetchMock.mockImplementation((url: string, init: RequestInit) => {
    if (url === '/interventions/live-case-library-v2') return Promise.resolve({ ok: true, status: 200, json: async () => ({
      contract_version: 'c2-live-case-library-v2', provenance: 'invented inputs', cases: [{
        case_id: 'TEST-0015', name: '16-month lower measurements',
        input: { ...initialInput, test_id: 'TEST-0015', age_months: 16,
          meal_frequency: '2 meals/day', dietary_diversity: 'Less than 2 varieties' },
        food_groups: ['rice and cereals'],
      }],
    }) })
    if (url === '/interventions/live-case-validation-v2') return Promise.resolve({ ok: true, status: 200, json: async () => ({
      mode: 'live_c1_invented_case_validation', c1_calls: 1, allow_demo: false, clinical_use: false,
      observed_categories: ['Underweight'], unobserved_categories: ['MAM', 'Normal', 'SAM', 'Stunting'],
      cases: [{ case_id: 'TEST-0015', input_name: '16-month lower measurements',
        model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
        c1_predicted_category: 'Underweight', c1_severity: 'Moderate',
        c1_uncertainty_flag: true, assessment_review_needed: true,
        c2_candidate_count: 2, c2_research_test_rank_count: 1,
        c2_verified_feasible_count: 0, c2_status: 'research_test' }],
    }) })
    if (url === '/interventions/baseline-c1-v2') {
      baselineCalls++
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ assessment, prediction,
        c1_calls: 1, feeding_provenance: 'unverified', limitations: ['Invented input.'] }) })
    }
    scenarioCalls++
    const submitted = JSON.parse(String(init.body))
    expect(submitted.original_c1).toEqual(assessment)
    expect(submitted.method).toBe('compare_all')
    return Promise.resolve({ ok: true, status: 200, json: async () => ({
      contract_version: 'c2-diet-scenarios-v2', original_c1: assessment,
      original_c1_unchanged: true, c1_candidate_calls: 0,
      feeding_baseline: submitted.feeding, age_months: 24, candidate_count: 2,
      ranked_cards: [], unresolved_or_rejected: [{ candidate_id: 'food-option-1', generator_methods: ['bounded_search', 'face_graph'],
        title: 'Essentials example', status: 'evidence_incomplete', current_food_groups: [],
        proposed_food_groups: ['rice and cereals', 'pulses'], additional_groups: ['pulses'],
        reference_cost_lkr: '238.48', cost_period: 'weekly', reference_budget_fit: 'within_budget',
        items: [{ food_id: 'rice', name: 'Rice', food_group: 'rice and cereals', quantity: '0.5000', unit: 'kg', indicative_cost_lkr: '96.61', source_url: 'https://example.com', observation_end: '2026-10-01', market_coverage: 'Colombo' },
          { food_id: 'egg', name: 'Egg', food_group: 'eggs', quantity: '6.0000', unit: 'piece', indicative_cost_lkr: '226.62', source_url: 'https://example.com', observation_end: '2026-10-01', market_coverage: 'Colombo' }], schedule: ['Monday', 'Tuesday'].map(day => ({ day, slots: [
          { label: 'Morning pairing idea', foods: [{ name: 'Rice' }, { name: 'Egg' }] }] })), checks: [{ criterion: 'nutrition_adequacy', state: 'unknown',
          reason: 'No verified portions', evidence_source: null }], rank: null, limitations: [] },
        { candidate_id: 'food-option-2', title: 'Varied foods example', status: 'evidence_incomplete',
          current_food_groups: [], proposed_food_groups: ['fish'], additional_groups: ['fish'],
          reference_cost_lkr: '1713.08', cost_period: 'weekly', reference_budget_fit: 'above_budget',
          items: [], schedule: [], checks: [], rank: null, limitations: [] }],
      referral_notice: 'Seek professional assessment', ranking_trace: { status: 'engineering_design_not_official_ranking_rule',
        order: ['safety', 'cost'], note: 'Unresolved stays unranked' },
      method: 'compare_all', method_results: {
        bounded_search: { status: 'executed', generated_count: 1, independently_validated_count: 1,
          verified_ranked_count: 0, rejected_or_unresolved_count: 1, runtime_ms: 0.1,
          diagnostics: { enumerated: 1 } },
        face_graph: { status: 'executed', generated_count: 1, independently_validated_count: 1,
          verified_ranked_count: 0, rejected_or_unresolved_count: 1, runtime_ms: 0.2,
          diagnostics: { paths: { 'food-option-1': { path: [[], ['rice'], ['rice', 'egg']] } } } },
        dice: { status: 'unavailable_real_nutrition_target', generated_count: 0, independently_validated_count: 0,
          verified_ranked_count: 0, rejected_or_unresolved_count: 0, runtime_ms: 0.1,
          diagnostics: { reason: 'No validated nutrition target.' } },
      },
      software_test_ranked: [{ candidate_id: 'food-option-1', rank: 1, title: 'Essentials example',
        generator_methods: ['bounded_search', 'face_graph'], reference_cost_lkr: '238.48', scope: 'research_test' }],
      clinical_use: false, limitations: ['No C1 candidate predictions.'],
    }) })
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/analysis']}><App/></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByRole('textbox', { name: 'Test case ID' })).toHaveValue('TEST-0014')
  fireEvent.click(await screen.findByRole('button', { name: 'Verify all cases with live C1' }))
  expect(await screen.findByRole('heading', { name: 'Results from this live C1 run' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'Underweight' })).toBeInTheDocument()
  fireEvent.click(await screen.findByRole('button', { name: 'Generate dietary scenarios' }))
  expect(await screen.findByRole('heading', { name: 'Essentials example' })).toBeInTheDocument()
  expect(screen.queryByText(/Assessment review needed before using food examples/)).not.toBeInTheDocument()
  expect(screen.queryByText(/Research-test ordering compares indicative shopping cost/)).not.toBeInTheDocument()
  expect(screen.queryByText('Feeding information provenance')).not.toBeInTheDocument()
  expect(screen.queryByText('Allergy or restriction status')).not.toBeInTheDocument()
  expect(screen.queryByText('Professional nutrition review is needed before using any food option.')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Counterfactual algorithm comparison' })).not.toBeInTheDocument()
  expect(screen.queryByText('Research evidence and limitations')).not.toBeInTheDocument()
  expect(screen.queryByText('Baseline and feature policy')).not.toBeInTheDocument()
  expect(screen.queryByText(/C2 made 0 candidate prediction calls/)).not.toBeInTheDocument()
  expect(screen.queryByText(/Costs use regional reference prices and household purchase quantities/)).not.toBeInTheDocument()
  expect(screen.queryByText(/Selected counts show options included/)).not.toBeInTheDocument()
  expect(screen.getByText('Generated by: Bounded Search, FACE Graph')).toBeInTheDocument()
  expect(screen.getByText('500 g to purchase · LKR 96.61')).toBeInTheDocument()
  expect(screen.getByText('6 piece to purchase · LKR 226.62')).toBeInTheDocument()
  expect(screen.queryByText('Needs more information')).not.toBeInTheDocument()
  expect(screen.getByText('Within budget').parentElement).toHaveClass('bg-emerald-50')
  expect(screen.getByText('Above budget').parentElement).toHaveClass('bg-rose-50')
  fireEvent.click(screen.getByText('See food pairing ideas'))
  expect(screen.getAllByText('Morning pairing idea: Rice, Egg')).toHaveLength(1)
  expect(baselineCalls).toBe(1)
  expect(scenarioCalls).toBe(1)
  fireEvent.change(screen.getByRole('textbox', { name: 'Reported food budget (LKR)' }), { target: { value: '2000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Generate dietary scenarios' }))
  expect(await screen.findByRole('heading', { name: 'Essentials example' })).toBeInTheDocument()
  expect(baselineCalls).toBe(1)
  expect(scenarioCalls).toBe(2)
  fireEvent.click(screen.getByRole('button', { name: /16-month lower measurements/ }))
  expect(screen.getByRole('spinbutton', { name: 'Age (months)' })).toHaveValue(16)
  fireEvent.click(screen.getByRole('button', { name: 'Generate dietary scenarios' }))
  expect(await screen.findByRole('heading', { name: 'Essentials example' })).toBeInTheDocument()
  expect(baselineCalls).toBe(2)
  expect(scenarioCalls).toBe(3)
})
