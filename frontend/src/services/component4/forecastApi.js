import { apiRequest } from './httpClient';

export function getForecastBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/by-selected-month', {
    params: { year, month, district },
  });
}

export function getDistricts() {
  return apiRequest('/forecast/districts');
}

export function getOrigins() {
  return apiRequest('/forecast/origins');
}

export function getForecastStatus() {
  return apiRequest('/forecast/status');
}
