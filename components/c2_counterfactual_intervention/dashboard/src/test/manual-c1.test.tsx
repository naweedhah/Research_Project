import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../pages/App'

const fetchMock = vi.fn()
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('shows the user-entered profile, actual response fields, and model-only candidate status', async () => {
  let submitted: Record<string, unknown> = {}
  const prediction = {
    predicted_malnutrition_type: 'Underweight', acute_status: 'Normal', severity: 'Moderate',
    underweight_probability: .1025, stunting_probability: .0399,
    acute_probabilities: { Normal: .8795, MAM: .1201, SAM: .0004 },
    severity_probabilities: { normal: .1, moderate: .8, severe: .1 },
    uncertainty_flag: false, model_version: 'GA-RGCA-v3', prediction_source: 'GA-RGCA-v3',
    prediction_task: 'twelve_month_nutritional_risk', clinical_use: false, data_limitations: [],
  }
  fetchMock.mockImplementation((_url: string, init: RequestInit) => {
    submitted = JSON.parse(String(init.body))
    return Promise.resolve({ ok: true, status: 200, json: async () => ({
      mode: 'manual_genuine_c1_model_comparison', submitted_input: submitted,
      input_fingerprint: 'test-contract-fingerprint', prediction_source: 'GA-RGCA-v3',
      model_version: 'GA-RGCA-v3', prediction_task: 'twelve_month_nutritional_risk',
      baseline: prediction, candidates: [{
        changes: { meal_frequency: { from: '3 meals/day', to: '4+ meals/day' } },
        prediction: { ...prediction, underweight_probability: .11 },
        probability_delta: { underweight: .0075, stunting: 0, acute: { Normal: 0, MAM: 0, SAM: 0 } },
        model_policy_result: 'rejected', rejected_reasons: ['underweight_probability increases'],
        unresolved_reasons: ['research authorization unavailable'], only_feeding_fields_changed: true, rank: null,
      }], ranked_model_comparisons: [], food_plans: [],
      budget: { amount_lkr: '1500', period: 'weekly', affordability: 'unresolved' },
      approved_intervention_cards: [], clinical_use: false,
      limitations: ['Model differences do not establish treatment effects.'],
    }) })
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/legacy-c1-comparison']}><App/></MemoryRouter></QueryClientProvider>)
  fireEvent.change(await screen.findByRole('spinbutton', { name: 'Historical weight (kg)' }), { target: { value: '11.5' } })
  fireEvent.click(screen.getByRole('button', { name: /Analyze with C1 and C2/ }))
  expect(await screen.findByRole('heading', { name: 'Original input and C1 output' })).toBeInTheDocument()
  expect(submitted.weight_kg).toBe(11.5)
  expect(screen.getByText('What C1 returned')).toBeInTheDocument()
  expect(screen.getAllByText('10.25%').length).toBeGreaterThan(0)
  expect(screen.getByText('Model rule rejected')).toBeInTheDocument()
  expect(screen.queryByText('allow_demo=false')).not.toBeInTheDocument()
})
