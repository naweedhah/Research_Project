import { apiRequest } from './httpClient';

export function getWarnings(params = {}) {
  return apiRequest('/forecast/warnings/', { params });
}

export function getWarningSummary() {
  return apiRequest('/forecast/warnings/summary');
}

export function sendWarningReport() {
  return apiRequest('/email/send-warning-report', {
    method: 'POST',
    auth: true,
  });
}
