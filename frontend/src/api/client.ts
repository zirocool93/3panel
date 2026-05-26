import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { authStore } from "../store/auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
});

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _authRetry?: boolean;
};

let refreshPromise: Promise<string> | null = null;

api.interceptors.request.use((config) => {
  const accessToken = authStore.getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    if (!shouldRefresh(error, originalRequest)) {
      return Promise.reject(error);
    }

    const refreshToken = authStore.getRefreshToken();
    if (!refreshToken || !originalRequest) {
      handleExpiredSession();
      return Promise.reject(error);
    }

    originalRequest._authRetry = true;
    try {
      const accessToken = await refreshAccessToken(refreshToken);
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      handleExpiredSession();
      return Promise.reject(refreshError);
    }
  },
);

function shouldRefresh(error: AxiosError, request?: RetriableRequestConfig): boolean {
  return Boolean(
    error.response?.status === 401 &&
      request &&
      !request._authRetry &&
      !request.url?.includes("/auth/login") &&
      !request.url?.includes("/auth/refresh"),
  );
}

async function refreshAccessToken(refreshToken: string): Promise<string> {
  refreshPromise ??= api
    .post("/auth/refresh", { refresh_token: refreshToken })
    .then((response) => {
      authStore.setTokens(response.data);
      return response.data.access_token as string;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

function handleExpiredSession(): void {
  authStore.clear();
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}
