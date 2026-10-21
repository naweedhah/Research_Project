import { CircleHelp } from 'lucide-react'

export function ResearchNotice({ kind = 'test' }: { kind?: 'test' | 'model' | 'price' }) {
  const text = {
    test: ['Research-test mode', 'C2 method outputs use a synthetic test predictor. Cards are hypothetical software results and require professional review. Genuine C1 inference is shown only on the model-validation screen.'],
    model: ['Genuine C1 inference · demonstration inputs', 'The loaded GA-RGCA-v3 model scores invented feeding profiles with its demo fallback disabled. This comparison does not establish a treatment effect or authorize an intervention. Professional review is required.'],
    price: ['Published Colombo reference', 'DCS values describe published Colombo District market observations. Kalmunai availability, household affordability, serving suitability and clinical eligibility remain unverified.'],
  }[kind]
  return <details className="research-notice"><summary><CircleHelp size={16}/><strong>{text[0]}</strong><span>Read research boundary</span></summary><p>{text[1]}</p></details>
}
