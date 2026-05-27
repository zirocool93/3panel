import { api } from "./client";

export type ClientSubscriptionRead = {
  id: number;
  tariff_id: number | null;
  tariff_name: string | null;
  status: string;
  payment_method: string | null;
  price_amount: string | null;
  currency: string | null;
  duration_days: number | null;
  traffic_limit_gb: number | null;
  device_limit: number | null;
  started_at: string | null;
  expires_at: string | null;
  subscription_token: string;
  nodes_count: number;
  admin_comment: string | null;
  created_at: string;
};

export type ClientTransactionRead = {
  id: number;
  user_id: number;
  user_display_name: string | null;
  admin_id: number | null;
  subscription_id: number | null;
  type: string;
  payment_method: string | null;
  amount: string;
  currency: string;
  balance_before: string;
  balance_after: string;
  description: string | null;
  external_id: string | null;
  created_at: string;
};

export type ClientRead = {
  id: number;
  display_name: string | null;
  telegram_id: number | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  comment: string | null;
  balance: string;
  is_blocked: boolean;
  subscriptions_count: number;
  subscriptions: ClientSubscriptionRead[];
  transactions: ClientTransactionRead[];
  created_at: string;
  updated_at: string;
};

export type ClientPayload = {
  display_name: string;
  telegram_id?: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  comment?: string;
  is_blocked?: boolean;
};

export type ClientSubscriptionPayload = {
  tariff_id: number;
  payment_method: string;
  price_amount?: string;
  currency?: string;
  duration_days?: number;
  traffic_limit_gb?: number;
  device_limit?: number;
  admin_comment?: string;
};

export type ClientBalanceAdjustPayload = {
  amount: string;
  currency: string;
  description?: string;
};

export async function listClients(): Promise<ClientRead[]> {
  const response = await api.get<ClientRead[]>("/clients");
  return response.data;
}

export async function createClient(payload: ClientPayload): Promise<ClientRead> {
  const response = await api.post<ClientRead>("/clients", payload);
  return response.data;
}

export async function updateClient(
  clientId: number,
  payload: Partial<ClientPayload>,
): Promise<ClientRead> {
  const response = await api.patch<ClientRead>(`/clients/${clientId}`, payload);
  return response.data;
}

export async function deleteClient(clientId: number): Promise<void> {
  await api.delete(`/clients/${clientId}`);
}

export async function createClientSubscription(
  clientId: number,
  payload: ClientSubscriptionPayload,
): Promise<ClientSubscriptionRead> {
  const response = await api.post<ClientSubscriptionRead>(
    `/clients/${clientId}/subscriptions`,
    payload,
  );
  return response.data;
}

export async function adjustClientBalance(
  clientId: number,
  payload: ClientBalanceAdjustPayload,
): Promise<ClientRead> {
  const response = await api.post<ClientRead>(`/clients/${clientId}/balance`, payload);
  return response.data;
}

export async function listClientTransactions(clientId: number): Promise<ClientTransactionRead[]> {
  const response = await api.get<ClientTransactionRead[]>(`/clients/${clientId}/transactions`);
  return response.data;
}

export async function listTransactions(): Promise<ClientTransactionRead[]> {
  const response = await api.get<ClientTransactionRead[]>("/transactions");
  return response.data;
}
