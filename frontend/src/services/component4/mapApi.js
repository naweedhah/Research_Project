import { apiRequest } from './httpClient';

export function getPriorityMapBySelectedMonth({ year, month }) {
  return apiRequest('/forecast/map/priority/by-selected-month', {
    params: { year, month },
  });
}

export function getMapBoundaries() {
  return apiRequest('/forecast/map/boundaries');
}
