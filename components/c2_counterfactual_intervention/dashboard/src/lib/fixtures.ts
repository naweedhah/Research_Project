import favorable from '../fixtures/favorable.json'
import unchanged from '../fixtures/unchanged.json'
import worsening from '../fixtures/worsening.json'
import uncertain from '../fixtures/uncertain.json'
import noSolution from '../fixtures/no_solution.json'
import unknownAvailability from '../fixtures/unknown_availability.json'
import unaffordable from '../fixtures/unaffordable.json'
import tooYoung from '../fixtures/too_young.json'
import type { Profile, ResearchRequest } from './contracts'

const fixtures = { favorable, unchanged, worsening, uncertain, no_solution: noSolution,
  unknown_availability: unknownAvailability, unaffordable, too_young: tooYoung } as const

export function fixtureFor(scenario: Profile['scenario']): ResearchRequest {
  return structuredClone(fixtures[scenario]) as ResearchRequest
}

export function defaultProfile(): Profile {
  const source = fixtureFor('favorable')
  return { pseudonym: source.snapshot.child_pseudonymous_id,
    age: Number(source.snapshot.historical_baseline.age_months),
    height: Number(source.snapshot.historical_baseline.height_cm),
    weight: Number(source.snapshot.historical_baseline.weight_kg),
    meal: source.snapshot.ga_rgca_context.meal_frequency as Profile['meal'],
    diversity: source.snapshot.ga_rgca_context.dietary_diversity as Profile['diversity'],
    method: 'bounded_search', scenario: 'favorable' }
}

export function profileForScenario(scenario: Profile['scenario'], method: Profile['method']): Profile {
  const source = fixtureFor(scenario)
  return { pseudonym: source.snapshot.child_pseudonymous_id,
    age: Number(source.snapshot.historical_baseline.age_months),
    height: Number(source.snapshot.historical_baseline.height_cm),
    weight: Number(source.snapshot.historical_baseline.weight_kg),
    meal: source.snapshot.ga_rgca_context.meal_frequency as Profile['meal'],
    diversity: source.snapshot.ga_rgca_context.dietary_diversity as Profile['diversity'],
    method, scenario }
}

export function mapRequest(profile: Profile): { request: ResearchRequest; fixtureAssertionsRetained: boolean } {
  const request = fixtureFor(profile.scenario)
  const fixture = request.snapshot
  const unchanged = profile.age === Number(fixture.historical_baseline.age_months) &&
    profile.height === Number(fixture.historical_baseline.height_cm) &&
    profile.weight === Number(fixture.historical_baseline.weight_kg) &&
    profile.meal === fixture.ga_rgca_context.meal_frequency &&
    profile.diversity === fixture.ga_rgca_context.dietary_diversity
  request.method = profile.method
  request.snapshot.child_pseudonymous_id = profile.pseudonym
  request.snapshot.historical_baseline.age_months = profile.age
  request.snapshot.historical_baseline.height_cm = profile.height
  request.snapshot.historical_baseline.weight_kg = profile.weight
  request.snapshot.ga_rgca_context.meal_frequency = profile.meal
  request.snapshot.ga_rgca_context.dietary_diversity = profile.diversity
  request.snapshot.provenance = unchanged ? 'fully synthetic October 22 software fixture' : 'user-edited synthetic test profile; feasibility unverified'
  // Fixture assertions apply only to its exact synthetic profile. Edits cannot inherit approvals.
  if (!unchanged) {
    for (const key of ['available', 'practical', 'age_suitable', 'eligible', 'clinically_suitable', 'transition_justified']) {
      request.context[key] = { meals_per_day: null, dietary_diversity: null }
    }
    request.context.budget_units = null
    request.food_planning = null
    request.policy.approved_for_research = false
  }
  return { request, fixtureAssertionsRetained: unchanged }
}
