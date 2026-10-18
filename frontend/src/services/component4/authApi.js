import { apiRequest, clearAccessToken, setAccessToken } from './httpClient';

export async function login(email, password) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: { email, password },
  });
  if (data?.access_token) setAccessToken(data.access_token);
  return data;
}

export async function register(name, email, password) {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: { name, email, password },
  });
}

export async function getMe() {
  return apiRequest('/auth/me', { auth: true });
}

export function logout() {
  clearAccessToken();
}
