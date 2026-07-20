import axios from "axios";

export const SESSION_TOKEN_KEY = "fanora.session";

export const api = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      typeof window !== "undefined" &&
      error.response?.status === 401 &&
      !String(error.config?.url || "").includes("/auth/web3auth")
    ) {
      window.localStorage.removeItem(SESSION_TOKEN_KEY);
    }
    return Promise.reject(error);
  },
);
