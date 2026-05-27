import { api } from "./client";

export type TariffInboundLink = {
  id?: number;
  server_id: number;
  inbound_id: string;
  inbound_remark?: string | null;
  protocol?: string | null;
};

export type TariffRead = {
  id: number;
  name: string;
  description: string | null;
  duration_days: number;
  traffic_limit_gb: number | null;
  device_limit: number | null;
  price: string;
  currency: string;
  is_trial: boolean;
  enabled: boolean;
  is_visible: boolean;
  sort_order: number;
  inbound_links: TariffInboundLink[];
  created_at: string;
  updated_at: string;
};

export type TariffPayload = {
  name: string;
  description?: string;
  duration_days: number;
  traffic_limit_gb?: number;
  device_limit?: number;
  price: string;
  currency: string;
  is_trial: boolean;
  enabled: boolean;
  is_visible: boolean;
  sort_order: number;
  inbound_links: TariffInboundLink[];
};

export async function listTariffs(): Promise<TariffRead[]> {
  const response = await api.get<TariffRead[]>("/tariffs");
  return response.data;
}

export async function createTariff(payload: TariffPayload): Promise<TariffRead> {
  const response = await api.post<TariffRead>("/tariffs", payload);
  return response.data;
}

export async function updateTariff(
  tariffId: number,
  payload: Partial<TariffPayload>,
): Promise<TariffRead> {
  const response = await api.patch<TariffRead>(`/tariffs/${tariffId}`, payload);
  return response.data;
}
