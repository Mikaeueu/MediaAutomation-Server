import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://0.0.0.0:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

export default api;
