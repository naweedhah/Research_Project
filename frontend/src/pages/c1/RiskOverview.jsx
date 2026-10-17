import { Link } from 'react-router-dom';
import { ExternalLink, ShieldCheck } from 'lucide-react';
import { useApi } from '../../lib/useApi';
import { Badge, Card, CardBody, CardHeader, KeyValues, PageHeader } from '../../ui';

const C1_APP_URL = import.meta.env.VITE_C1_APP_URL || 'http://localhost:3000';

// From Component 1's GA-RGCA v3 deployment metadata.
const OUTPUTS = [
  ['Underweight', 'probability, threshold 0.09'],
  ['Stunting', 'probability, threshold 0.09'],
  ['Acute status', 'Normal / MAM / SAM'],
  ['Overall severity', 'Normal / Moderate / Severe'],
  ['Uncertainty', 'spread across the 3 ensemble networks'],
];
const VIEWS = [
  ['Growth history (2025)', 'age, height, weight, BMI, birth weight, previous status'],
  ['Socio-economic', "mother's age and education, income, family size, occupations"],
  ['Feeding', 'breastfeeding, complementary feeding, meals, dietary diversity'],
  ['Supplementation', 'Triposha, vitamins'],
];
const TRIAGE = [
  ['SAM risk', 'Priority clinical assessment — SAM risk', 'danger'],
  ['MAM risk', 'Priority clinical assessment — MAM risk', 'danger'],
  ['Underweight or stunting predicted', 'Priority clinical assessment', 'warning'],
  ['Networks disagree (high uncertainty)', 'Clinician review / closer monitoring', 'info'],
  ['Otherwise', 'Routine monitoring', 'success'],
];

export default function RiskOverview() {
  const status = useApi('/risk/status');
  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader
        component="c1"
        title="Risk assessment"
        subtitle="Predicts each child's risk of underweight, stunting and acute malnutrition a year ahead from growth history, household, feeding and supplementation information."
        actions={
          <a href={C1_APP_URL} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-c1 px-3.5 py-2 text-sm font-semibold text-white hover:bg-c1/90">
            Open clinical app <ExternalLink size={15} />
          </a>
        }
      />

      <Card>
        <CardBody className="flex flex-wrap items-center gap-3 text-sm">
          <Badge tone={status.data?.ready ? 'success' : 'neutral'}>{status.data?.ready ? 'Model service ready' : 'Clinical app runs as a separate service'}</Badge>
          <span className="text-muted">
            Child registration, visits, trajectories and reports live in Component 1's own web app ({C1_APP_URL}).
          </span>
        </CardBody>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Model: GA-RGCA v3" subtitle="Growth-anchored, reliability-gated cross-attention network; ensemble of 3" />
          <CardBody className="space-y-4">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Outputs</p>
              <KeyValues rows={OUTPUTS} />
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Input views</p>
              <KeyValues rows={VIEWS} />
            </div>
            <p className="text-xs text-muted">2026 measurements and outcome labels are never used as inputs. Research decision support; clinical confirmation required.</p>
          </CardBody>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Clinical triage" subtitle="Checked in this order; the first match decides the recommendation" />
            <CardBody className="space-y-2">
              {TRIAGE.map(([when, then, tone], i) => (
                <div key={when} className="flex items-center gap-3 rounded-lg border border-line px-3 py-2 text-sm">
                  <span className="tabular w-5 text-muted">{i + 1}</span>
                  <span className="flex-1 text-primary">{when}</span>
                  <Badge tone={tone}>{then}</Badge>
                </div>
              ))}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Kept reliable by Component 3" icon={ShieldCheck} />
            <CardBody className="space-y-2 text-sm text-muted">
              <p>
                C3 loads this model through its adapter and watches it as new screening rounds arrive: data changes, accuracy
                and calibration once outcomes are known, and subgroup performance. It proposes a verified fix only when
                reliability is actually harmed.
              </p>
              <Link to="/c3" className="inline-flex items-center gap-1 font-semibold text-c3 hover:underline">Open model health</Link>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
