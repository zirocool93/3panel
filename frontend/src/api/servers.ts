import { api } from "./client";

export type ServerHealthStatus = "unknown" | "online" | "offline" | "degraded";

export type ServerRead = {
  id: number;
  name: string;
  provider_type: "xui";
  country: string;
  location: string | null;
  panel_url: string;
  enabled: boolean;
  max_users: number | null;
  current_users: number;
  priority: number;
  subscription_base_url: string | null;
  last_health_status: ServerHealthStatus;
  last_health_checked_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ServerCreate = {
  name: string;
  country: string;
  location?: string;
  panel_url: string;
  username?: string;
  password?: string;
  api_token?: string;
  enabled: boolean;
  max_users?: number;
  priority: number;
  subscription_base_url?: string;
};

export type ServerUpdate = Partial<ServerCreate>;

export type ServerHealthRead = {
  ok: boolean;
  status: ServerHealthStatus;
  message: string;
};

export type ServerInboundRead = {
  id: number;
  remark: string | null;
  protocol: string | null;
  enable: boolean | null;
  port: number | null;
};

export type XuiClientRead = {
  inbound_id: number;
  inbound_remark: string | null;
  protocol: string | null;
  email: string;
  client_uuid: string | null;
  sub_id: string | null;
  enable: boolean | null;
  expiry_time: number | null;
  traffic_limit: number;
  up: number;
  down: number;
  total: number;
};

export async function listServers(): Promise<ServerRead[]> {
  const response = await api.get<ServerRead[]>("/servers");
  return response.data;
}

export async function createServer(payload: ServerCreate): Promise<ServerRead> {
  const response = await api.post<ServerRead>("/servers", payload);
  return response.data;
}

export async function updateServer(
  serverId: number,
  payload: ServerUpdate,
): Promise<ServerRead> {
  const response = await api.patch<ServerRead>(`/servers/${serverId}`, payload);
  return response.data;
}

export async function checkServer(serverId: number): Promise<ServerHealthRead> {
  const response = await api.post<ServerHealthRead>(`/servers/${serverId}/check`);
  return response.data;
}

export async function listServerInbounds(serverId: number): Promise<ServerInboundRead[]> {
  const response = await api.get<ServerInboundRead[]>(`/servers/${serverId}/inbounds`);
  return response.data;
}

export async function listXuiClients(serverId: number): Promise<XuiClientRead[]> {
  const response = await api.get<XuiClientRead[]>(`/servers/${serverId}/xui-clients`);
  return response.data;
}
