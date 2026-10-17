import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../pages/App'
import { defaultProfile, mapRequest, profileForScenario } from '../lib/fixtures'
import { diversity, meals } from '../lib/contracts'

const status = { component: 2, test_engine_ready: true, c1_integrated: false,
  real_model_registered: false, clinical_ready: false, methods: ['bounded_search','dice','face_graph'] }
const result = { mode: 'simulated', method: 'bounded_search', banner: 'SIMULATED MODEL - NOT FOR CLINICAL USE',
  baseline: { predicted_malnutrition_type: 'Underweight', acute_status: 'Normal', severity: 'Moderate', uncertainty_flag: false,
    prediction_source: 'SIMULATED_TEST_ONLY', model_version: 'C1-SHAPED-SIMULATOR-v1', data_limitations: [] },
  candidates: [], cards: [{ rank: 1, changes: { meal_frequency: '4+ meals/day' }, explanation: 'Hypothetical simulator output',
    feasibility_status: 'feasible under supplied test assertions', professional_review_required: true }],
  rejected_or_unresolved: [], message: 'Research-test candidates require professional review', c1_integrated: false, clinical_use: false }

const fetchMock = vi.fn()
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function reply(data: unknown, statusCode = 200) {
  return { ok: statusCode >= 200 && statusCode < 300, status: statusCode,
    statusText: statusCode === 503 ? 'Unavailable' : 'OK', json: async () => data }
}
function app(path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>)
}

describe('dashboard research contract', () => {
  it('loads an actual C1 baseline automatically in the new primary workflow', async () => {
    const prediction = { predicted_malnutrition_type: 'Stunting', acute_status: 'Normal', severity: 'Normal',
      underweight_probability: 0.0001, stunting_probability: 0.1118,
      acute_probabilities: { Normal: 0.988, MAM: 0.0118, SAM: 0.0002 },
      severity_probabilities: { normal: 0.52, moderate: 0.45, severe: 0.03 },
      uncertainty_flag: true, model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
      prediction_task: 'twelve_month_nutritional_risk', clinical_use: false, data_limitations: [] }
    fetchMock.mockResolvedValue(reply({ case_id: 'synthetic_24m', snapshot_provenance: 'fully synthetic test case', age_months: 24,
      original_feeding: { meal_frequency: '3 meals/day', dietary_diversity: '2 to 5 varieties' },
      baseline: prediction, guidance: { age_band: '24-59 months (older-child category)', status: 'practice_pending_review',
        reference: null, food_groups: [], quantity: null, note: 'No reviewed quantity.' }, clinical_use: false }))
    app('/c1-comparison')
    expect(await screen.findByText(/GA-RGCA-v3.*genuine inference/)).toBeInTheDocument()
    expect(screen.getByText(/Original feeding:/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Generate Intervention Analysis/ })).toBeEnabled()
    expect(screen.queryByText('Approved intervention card')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/interventions/automatic-baseline?case_id=synthetic_24m', expect.anything())
  })

  it('fails closed when the automatic C1 baseline is offline', async () => {
    fetchMock.mockResolvedValue(reply({ detail: 'C1 unavailable' }, 503))
    app('/c1-comparison')
    expect(await screen.findByText('C1 baseline unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Generate Intervention Analysis/ })).toBeDisabled()
  })

  it('shows no under-six-month feeding candidate or invented C1 prediction', async () => {
    const base = { case_id: 'synthetic_24m', snapshot_provenance: 'synthetic', age_months: 24,
      original_feeding: {}, baseline: null,
      guidance: { age_band: 'under 6 months', status: 'no_complementary_feeding_candidate', reference: null,
        food_groups: [], quantity: null, note: 'No complementary-feeding counterfactual is generated.' }, clinical_use: false }
    fetchMock.mockImplementation((url: string) => Promise.resolve(reply(url.includes('automatic-analysis') ? {
      ...base, case_id: 'synthetic_5m', age_months: 5, mode: 'unsupported_age_no_prediction', model_version: null,
      candidates: [], approved_intervention_cards: [], budget: { amount_lkr: null, period: 'weekly', affordability: 'unresolved' },
      published_price_examples: [], shopping_examples: [], methods: [], research_test_runs: [], limitations: [],
    } : { ...base, case_id: 'synthetic_5m', age_months: 5 })))
    app('/c1-comparison')
    fireEvent.change(screen.getByRole('combobox', { name: 'Demonstration case' }), { target: { value: 'synthetic_5m' } })
    expect(await screen.findByText('C1 not scored: age-inapplicable feeding fields')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Generate Intervention Analysis/ }))
    expect(await screen.findByText('No permitted feeding counterfactual')).toBeInTheDocument()
    expect(screen.queryByText('Genuine C1 comparisons')).not.toBeInTheDocument()
  })
  it('opens and closes the compact navigation', async () => {
    fetchMock.mockResolvedValue(reply(status))
    app()
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    expect(screen.getByRole('button', { name: 'Close navigation' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Intervention Analysis' })).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Close navigation' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Close navigation' })).not.toBeInTheDocument())
  })

  it('shows only backend-supplied genuine model validation, with no intervention card', async () => {
    const prediction = {
      predicted_malnutrition_type: 'Stunting', acute_status: 'Normal', severity: 'Normal',
      underweight_probability: 0.0001, stunting_probability: 0.1118,
      acute_probabilities: { Normal: 0.988, MAM: 0.0118, SAM: 0.0002 },
      severity_probabilities: { normal: 0.52, moderate: 0.45, severe: 0.03 },
      uncertainty_flag: true, model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
      prediction_task: 'twelve_month_nutritional_risk', clinical_use: false, data_limitations: [],
    }
    fetchMock.mockImplementation((url: string) => Promise.resolve(reply(url.endsWith('/c1-validation') ? {
      banner: 'GENUINE C1 MODEL VALIDATION ON SYNTHETIC INPUTS', fixture_provenance: 'synthetic fixture',
      original_feeding: { meal_frequency: '3 meals/day', dietary_diversity: '2 to 5 varieties' },
      baseline: prediction, variants: [{ changes: { meal_frequency: { from: '3 meals/day', to: '4+ meals/day' } },
        prediction: { ...prediction, stunting_probability: 0.1119 },
        comparison: { type_changed: false, severity_changed: false, underweight_probability_delta: 0,
          stunting_probability_delta: 0.0001 }, disposition: 'unresolved_for_intervention',
        reasons: ['Model uncertainty requires professional review'] }], intervention_cards: [],
      clinical_use: false, limitations: ['No clinical benefit established'],
    } : status)))
    app('/model-validation')
    expect(await screen.findByText('Actual C1 comparisons')).toBeInTheDocument()
    expect(screen.getByText('Model uncertainty requires professional review')).toBeInTheDocument()
    expect(screen.getByText(/0 intervention cards/)).toBeInTheDocument()
  })

  it('does not invent a model result if C1 validation is unavailable', async () => {
    fetchMock.mockResolvedValue(reply({ detail: 'C1 model unavailable' }, 503))
    app('/model-validation')
    expect(await screen.findByText('Genuine model unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Actual C1 comparisons')).not.toBeInTheDocument()
  })

  it('shows official price geography and source without local availability claims', async () => {
    fetchMock.mockResolvedValue(reply({ as_of: '2026-10-18', banner: 'OFFICIAL COLOMBO PRICE REFERENCES',
      limitations: 'No Kalmunai market price is verified.', records: [{ food_id: 'mysore_dhall_average',
        commodity: 'Mysore Dhall - ( Average )', amount_lkr: '334.52', quantity: '1', unit: 'kg',
        source_institution: 'Department of Census and Statistics',
        source_url: 'https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-10-W1.pdf',
        source_locator: 'page 3', publication_date: null, observation_start: '2026-10-01',
        observation_end: '2026-10-07', period_date_basis: 'calendar_week_interpretation',
        market_coverage: 'Main markets in Colombo District', reference_status: 'fresh_reference' }] }))
    app('/food-price-explorer')
    expect((await screen.findAllByText('Mysore Dhall - ( Average )')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Main markets in Colombo District').length).toBeGreaterThan(0)
    expect(screen.getByText(/No Kalmunai market price is verified/)).toBeInTheDocument()
  })

  it('renders overview and actual backend status', async () => {
    fetchMock.mockResolvedValue(reply(status))
    app()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Counterfactual research')
    expect((await screen.findAllByText('Connected')).length).toBeGreaterThan(0)
    expect(screen.getByText('No authorized predictor registered')).toBeInTheDocument()
    expect(screen.getByText('Authorization pending')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/interventions/status', expect.anything())
  })

  it('maps exact categories and methods to an existing Python fixture', () => {
    const profile = defaultProfile()
    const { request, fixtureAssertionsRetained } = mapRequest({ ...profile, method: 'face_graph' })
    expect(fixtureAssertionsRetained).toBe(true)
    expect(request.method).toBe('face_graph')
    expect(request.snapshot.ga_rgca_context.meal_frequency).toBe('3 meals/day')
    expect(meals).toEqual(['2 meals/day','3 meals/day','4+ meals/day'])
    expect(diversity).toEqual(['Less than 2 varieties','2 to 5 varieties','More than 5 varieties'])
    const edited = mapRequest({ ...profile, height: 81 })
    expect(edited.fixtureAssertionsRetained).toBe(false)
    expect(edited.request.policy.approved_for_research).toBe(false)
    expect(edited.request.context.available).toEqual({ meals_per_day: null, dietary_diversity: null })
    expect(edited.request.food_planning).toBeNull()
    expect(profileForScenario('no_solution', 'dice').meal).toBe('4+ meals/day')
  })

  it('shows exact feeding options and selected method, then renders a returned card', async () => {
    fetchMock.mockImplementation((url: string) => Promise.resolve(reply(url.endsWith('/status') ? status : result)))
    app('/studio')
    expect(await screen.findByText('Ready for a research run', {}, { timeout: 15000 })).toBeInTheDocument()
    expect(screen.getByLabelText('Meal frequency')).toHaveTextContent('3 meals/day')
    expect(screen.getByLabelText('Dietary diversity')).toHaveTextContent('More than 5 varieties')
    fireEvent.click(screen.getByText('FACE-inspired Graph', { selector: 'span' }))
    fireEvent.click(screen.getByRole('button', { name: /Generate Counterfactuals/ }))
    expect(await screen.findByText('Hypothetical simulator output')).toBeInTheDocument()
    const posted = JSON.parse(fetchMock.mock.calls.find(call => String(call[0]).endsWith('/c1-research'))![1].body)
    expect(posted.method).toBe('face_graph')
    expect(screen.getByText('Professional review required', { exact: true })).toBeInTheDocument()
    expect(screen.queryByText(/\d+(\.\d+)?%/)).not.toBeInTheDocument()
  })

  it('renders backend rejection reasons and empty result without replacement cards', async () => {
    fetchMock.mockImplementation((url: string) => Promise.resolve(reply(url.endsWith('/status') ? status : {
      ...result, cards: [], candidates: [], message: 'No approved, feasible counterfactual',
      rejected_or_unresolved: [{ changes: { meal_frequency: '4+ meals/day' }, status: 'unresolved', reasons: ['local availability unknown'] }],
    })))
    app('/studio')
    await screen.findByText('Ready for a research run')
    fireEvent.click(screen.getByRole('button', { name: /Generate Counterfactuals/ }))
    expect(await screen.findByText('No eligible counterfactual returned')).toBeInTheDocument()
    expect(screen.getByText('local availability unknown')).toBeInTheDocument()
    expect(screen.queryByText('Hypothetical simulator output')).not.toBeInTheDocument()
  })

  it('shows offline and HTTP failures without fabricated results', async () => {
    fetchMock.mockRejectedValue(new TypeError('network failed'))
    app('/studio')
    expect(await screen.findByText('Backend unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Hypothetical simulator output')).not.toBeInTheDocument()
  })

  it('compares three actual API method returns on the same fixture', async () => {
    fetchMock.mockImplementation((_url: string, init?: RequestInit) => Promise.resolve(reply({ ...result, method: JSON.parse(String(init?.body)).method })))
    app('/algorithm-comparison')
    fireEvent.click(await screen.findByRole('button', { name: 'Run all three methods' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const requests = fetchMock.mock.calls.map(call => JSON.parse(String(call[1].body)))
    expect(requests.map(request => request.method)).toEqual(['bounded_search', 'dice', 'face_graph'])
    expect(requests.map(request => request.snapshot)).toEqual([requests[0].snapshot, requests[0].snapshot, requests[0].snapshot])
    expect(await screen.findAllByText('SIMULATED_TEST_ONLY', { exact: false })).toHaveLength(3)
  })

  it('calculates a published same-unit reference and searches prices', async () => {
    fetchMock.mockResolvedValue(reply({ as_of: '2026-10-18', banner: 'OFFICIAL COLOMBO PRICE REFERENCES', limitations: 'No Kalmunai price verified.', records: [
      { food_id: 'milk', commodity: 'Published milk powder pack', amount_lkr: '1200.00', quantity: '400', unit: 'g', source_institution: 'DCS', source_url: 'https://www.statistics.gov.lk/example.pdf', source_locator: 'page 3', publication_date: null, observation_start: '2026-10-01', observation_end: '2026-10-07', period_date_basis: 'calendar_week_interpretation', market_coverage: 'Main markets in Colombo District', reference_status: 'fresh_reference' },
    ] }))
    app('/food-price-explorer')
    expect(await screen.findByText('LKR 1200.00')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Calculator quantity' }), { target: { value: '800' } })
    expect(screen.getByText('LKR 2400.00')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Search food prices' }), { target: { value: 'no match' } })
    expect(screen.getByText('No records match this search.')).toBeInTheDocument()
  })

  it('handles a 503 result without fabricating a card', async () => {
    fetchMock.mockImplementation((url: string) => Promise.resolve(url.endsWith('/status') ? reply(status) : reply({ detail: 'Model unavailable' }, 503)))
    app('/studio')
    await screen.findByText('Ready for a research run')
    fireEvent.click(screen.getByRole('button', { name: /Generate Counterfactuals/ }))
    expect(await screen.findByText('Dependency unavailable (HTTP 503)')).toBeInTheDocument()
    expect(screen.queryByText('Hypothetical simulator output')).not.toBeInTheDocument()
  })

  it.each([
    [422, { detail: 'invalid profile' }, 'Request rejected (HTTP 422)'],
    [200, { cards: [{ explanation: 'not a complete contract' }] }, 'Invalid backend response'],
  ])('reports HTTP or schema failure %s', async (code, payload, title) => {
    fetchMock.mockImplementation((url: string) => Promise.resolve(url.endsWith('/status') ? reply(status) : reply(payload, code)))
    app('/studio')
    await screen.findByText('Ready for a research run')
    fireEvent.click(screen.getByRole('button', { name: /Generate Counterfactuals/ }))
    expect(await screen.findByText(title)).toBeInTheDocument()
    expect(screen.queryByText('Hypothetical simulator output')).not.toBeInTheDocument()
  })
})
