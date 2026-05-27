import { api } from "./client";

export type PaymentProviderCode = "manual" | "telegram_stars" | "cardlink" | "yookassa";

export type PaymentMethodRead = {
  code: PaymentProviderCode;
  label: string;
  enabled: boolean;
};

export type PaymentSettingsRead = {
  manual_payments_enabled: boolean;
  manual_payment_instructions: string | null;
  telegram_stars_enabled: boolean;
  telegram_stars_rate_rub: number | null;
  telegram_stars_invoice_title: string | null;
  telegram_stars_invoice_description: string | null;
  cardlink_enabled: boolean;
  cardlink_api_base_url: string | null;
  cardlink_shop_id: string | null;
  cardlink_api_token_set: boolean;
  cardlink_currency: string | null;
  cardlink_locale: string | null;
  cardlink_payer_pays_commission: boolean;
  cardlink_success_url: string | null;
  cardlink_fail_url: string | null;
  yookassa_enabled: boolean;
  yookassa_shop_id: string | null;
  yookassa_secret_key_set: boolean;
  yookassa_return_url: string | null;
  yookassa_currency: string | null;
};

export type PaymentSettingsUpdate = {
  manual_payments_enabled: boolean;
  manual_payment_instructions?: string;
  telegram_stars_enabled: boolean;
  telegram_stars_rate_rub?: number;
  telegram_stars_invoice_title?: string;
  telegram_stars_invoice_description?: string;
  cardlink_enabled: boolean;
  cardlink_api_base_url?: string;
  cardlink_shop_id?: string;
  cardlink_api_token?: string;
  cardlink_currency?: string;
  cardlink_locale?: string;
  cardlink_payer_pays_commission: boolean;
  cardlink_success_url?: string;
  cardlink_fail_url?: string;
  yookassa_enabled: boolean;
  yookassa_shop_id?: string;
  yookassa_secret_key?: string;
  yookassa_return_url?: string;
  yookassa_currency?: string;
};

export async function listPaymentMethods(): Promise<PaymentMethodRead[]> {
  const response = await api.get<PaymentMethodRead[]>("/payments/methods");
  return response.data;
}

export async function getPaymentSettings(): Promise<PaymentSettingsRead> {
  const response = await api.get<PaymentSettingsRead>("/payments/settings");
  return response.data;
}

export async function updatePaymentSettings(
  payload: PaymentSettingsUpdate,
): Promise<PaymentSettingsRead> {
  const response = await api.put<PaymentSettingsRead>("/payments/settings", payload);
  return response.data;
}
