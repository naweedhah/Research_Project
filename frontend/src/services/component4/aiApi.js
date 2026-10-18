import { apiRequest } from './httpClient';

/**
 * POST /ai/chat
 * Body: { message, district?, year?, month? }
 */
export function sendAiChat({ message, district, year, month }) {
  const body = { message };

  if (district !== undefined && district !== null && district !== '') {
    body.district = district;
  }
  if (year !== undefined && year !== null && year !== '') {
    body.year = Number(year);
  }
  if (month !== undefined && month !== null && month !== '') {
    body.month = Number(month);
  }

  return apiRequest('/ai/chat', {
    method: 'POST',
    body,
  });
}
