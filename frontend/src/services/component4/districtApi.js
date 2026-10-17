import { apiRequest } from './httpClient';

export function getDistrictDetailsBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/districts/details/by-selected-month', {
    params: { year, month, district },
  });
}

export function getDistrictTrendBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/districts/trend/by-selected-month', {
    params: { year, month, district },
  });
}
