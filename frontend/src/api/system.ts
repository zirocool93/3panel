import { api } from "./client";

export type AdminUpdateStatus = {
  enabled: boolean;
  running: boolean;
  ref: string;
  log_tail: string[];
};

export async function getUpdateStatus(): Promise<AdminUpdateStatus> {
  const response = await api.get<AdminUpdateStatus>("/system/updates");
  return response.data;
}

export async function startUpdate(): Promise<AdminUpdateStatus> {
  const response = await api.post<AdminUpdateStatus>("/system/updates");
  return response.data;
}

