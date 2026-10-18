import { apiRequest } from './httpClient';

export function getResourcesBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/resources/by-selected-month', {
    params: { year, month, district },
  });
}
