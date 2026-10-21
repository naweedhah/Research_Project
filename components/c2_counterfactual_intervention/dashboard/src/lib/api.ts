import { automaticBaselineSchema, automaticResultSchema, c1BaselineV2Schema, dietScenariosV2Schema, liveCaseLibraryV2Schema, liveCaseValidationV2Schema, localProfilesSchema, localValidationSchema, manualC1ResultSchema, pricesSchema, resultSchema, standaloneResultSchema, standaloneValidationSchema, statusSchema, validationSchema, type AutomaticCaseId, type ManualC1Input, type ResearchRequest } from './contracts'

const base = (import.meta.env.VITE_API_BASE_PATH ?? '').replace(/\/$/, '')
const timeoutMs = 12000

export class ApiError extends Error {
  constructor(public kind: 'offline' | 'timeout' | 'validation' | 'unavailable' | 'invalid' | 'http', message: string) {
    super(message)
  }
}

async function call(path: string, init?: RequestInit, requestTimeoutMs = timeoutMs): Promise<unknown> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), requestTimeoutMs)
  try {
    const response = await fetch(`${base}${path}`, { ...init, signal: controller.signal })
    let body: unknown
    try { body = await response.json() } catch { throw new ApiError('invalid', 'Backend returned a non-JSON response.') }
    if (!response.ok) {
      const detail = typeof body === 'object' && body !== null && 'detail' in body ? JSON.stringify(body.detail) : response.statusText
      const kind = response.status === 422 ? 'validation' : response.status === 503 ? 'unavailable' : 'http'
      throw new ApiError(kind, `Backend HTTP ${response.status}: ${detail}`)
    }
    return body
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('timeout', 'Request timed out. Retry after checking the backend.')
    throw new ApiError('offline', 'Cannot reach the C2 backend. Start FastAPI on 127.0.0.1:8000 and retry.')
  } finally { clearTimeout(timer) }
}

export async function getStatus() {
  const parsed = statusSchema.safeParse(await call('/interventions/status'))
  if (!parsed.success) throw new ApiError('invalid', 'Backend status did not match the C2 contract.')
  return parsed.data
}

export async function generate(request: ResearchRequest) {
  const parsed = resultSchema.safeParse(await call('/interventions/c1-research', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request),
  }))
  if (!parsed.success) throw new ApiError('invalid', 'Backend result did not match the C2 research contract.')
  return parsed.data
}

export async function getValidation() {
  const parsed = validationSchema.safeParse(await call('/interventions/c1-validation'))
  if (!parsed.success) throw new ApiError('invalid', 'C1 validation response did not match its contract.')
  return parsed.data
}

export async function getPriceReferences() {
  const parsed = pricesSchema.safeParse(await call('/interventions/price-references'))
  if (!parsed.success) throw new ApiError('invalid', 'Official price response did not match its contract.')
  return parsed.data
}

export async function getAutomaticBaseline(caseId: AutomaticCaseId) {
  const parsed = automaticBaselineSchema.safeParse(await call(`/interventions/automatic-baseline?case_id=${encodeURIComponent(caseId)}`, undefined, 20000))
  if (!parsed.success) throw new ApiError('invalid', 'Genuine C1 baseline response did not match its contract.')
  return parsed.data
}

export async function getAutomaticAnalysis(input: { case_id: AutomaticCaseId; budget_lkr: string | null; budget_period: 'daily' | 'weekly' | 'monthly' }) {
  const parsed = automaticResultSchema.safeParse(await call('/interventions/automatic-analysis', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 60000))
  if (!parsed.success) throw new ApiError('invalid', `Automatic analysis response did not match its research contract at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}

export async function getStandaloneAnalysis(input: { case_id: AutomaticCaseId; budget_lkr: string | null; budget_period: 'daily' | 'weekly' | 'monthly' }) {
  const parsed = standaloneResultSchema.safeParse(await call('/interventions/standalone-analysis', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 60000))
  if (!parsed.success) throw new ApiError('invalid', `Standalone result did not match its research contract at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}

export async function getStandaloneValidation(caseId: AutomaticCaseId) {
  const parsed = standaloneValidationSchema.safeParse(await call(`/interventions/standalone-validation?case_id=${encodeURIComponent(caseId)}`, undefined, 60000))
  if (!parsed.success) throw new ApiError('invalid', `Genuine validation response did not match its contract at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}

export async function getManualC1Validation(input: ManualC1Input) {
  const parsed = manualC1ResultSchema.safeParse(await call('/interventions/manual-c1-validation', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 90000))
  if (!parsed.success) throw new ApiError('invalid', `Manual C1 result did not match its contract at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}

export async function getC1BaselineV2(input: ManualC1Input) {
  const parsed = c1BaselineV2Schema.safeParse(await call('/interventions/baseline-c1-v2', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 30000))
  if (!parsed.success) throw new ApiError('invalid', 'Original C1 assessment did not match its versioned contract.')
  return parsed.data
}

export async function getLiveCaseLibraryV2() {
  const parsed = liveCaseLibraryV2Schema.safeParse(await call('/interventions/live-case-library-v2'))
  if (!parsed.success) throw new ApiError('invalid', 'Live case library did not match its contract.')
  return parsed.data
}

export async function getLiveCaseValidationV2() {
  const parsed = liveCaseValidationV2Schema.safeParse(await call('/interventions/live-case-validation-v2', undefined, 90000))
  if (!parsed.success) throw new ApiError('invalid', 'Live C1 case results did not match their contract.')
  return parsed.data
}

export async function getDietScenariosV2(input: object) {
  const parsed = dietScenariosV2Schema.safeParse(await call('/interventions/diet-scenarios-v2', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 30000))
  if (!parsed.success) throw new ApiError('invalid', `Dietary scenario response mismatch at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}

export async function getLocalProfiles() {
  const parsed = localProfilesSchema.safeParse(await call('/interventions/local-validation-profiles'))
  if (!parsed.success) throw new ApiError('invalid', 'Local validation profiles did not match the C2 contract.')
  return parsed.data
}

export async function getLocalValidation(input: { case_id: string; budget_lkr: string | null; budget_period: 'daily' | 'weekly' | 'monthly' }) {
  const parsed = localValidationSchema.safeParse(await call('/interventions/local-validation', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 90000))
  if (!parsed.success) throw new ApiError('invalid', `Local validation result did not match its contract at ${parsed.error.issues[0]?.path.join('.') || 'root'}.`)
  return parsed.data
}
