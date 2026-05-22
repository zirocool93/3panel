import { api } from "./client";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type AdminMe = {
  id: number;
  email: string;
  role: "owner" | "admin" | "support" | "accountant" | "marketer";
  last_login_at: string | null;
};

export async function login(email: string, password: string): Promise<TokenPair> {
  const response = await api.post<TokenPair>("/auth/login", { email, password });
  return response.data;
}

export async function getMe(): Promise<AdminMe> {
  const response = await api.get<AdminMe>("/auth/me");
  return response.data;
}

