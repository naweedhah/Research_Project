import { apiRequest } from './httpClient';

export function getExplainabilityBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/explainability/by-selected-month', {
    params: { year, month, district },
  });
}
