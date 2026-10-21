const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  'http://localhost:8000';

export default API_BASE_URL;
export { API_BASE_URL };
