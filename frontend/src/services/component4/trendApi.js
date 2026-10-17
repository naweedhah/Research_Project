import { apiRequest } from './httpClient';

export function getClinicalTrendBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/trends/clinical/by-selected-month', {
    params: { year, month, district },
  });
}
