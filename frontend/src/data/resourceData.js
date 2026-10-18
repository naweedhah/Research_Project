import { districts } from './districtData';

export const resourceSummary = {
  totalRequirement: 45200,
  availableStock: 38500,
  additionalRequirement: 6700,
};

export function generateDistributionPlan() {
  const priorityOrder = { High: 1, Medium: 2, Low: 3 };
  const sorted = [...districts].sort(
    (a, b) => priorityOrder[a.risk] - priorityOrder[b.risk] || b.cases - a.cases
  );

  let remaining = resourceSummary.availableStock;
  const scheduleDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

  return sorted.map((d, index) => {
    const required = d.triposha;
    const allocated = Math.min(required, Math.max(0, Math.round(remaining * (required / resourceSummary.totalRequirement) * 1.15)));
    remaining -= allocated;
    const status =
      allocated >= required
        ? 'Fulfilled'
        : allocated >= required * 0.75
          ? 'Partial'
          : 'Deficit';

    return {
      district: d.name,
      children: d.cases,
      requiredPacks: required,
      allocatedPacks: allocated,
      priority: d.risk,
      deliverySchedule: `${scheduleDays[index % 5]} Week ${Math.floor(index / 5) + 1}`,
      status,
    };
  });
}
