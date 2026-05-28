import { api } from "./client";

export type AdminUpdateStatus = {
  enabled: boolean;
  running: boolean;
  ref: string;
  log_tail: string[];
};

export type DiagnosticCheckRead = {
  name: string;
  ok: boolean;
  message: string;
  fix: string | null;
};

export type DiagnosticLogRead = {
  service: string;
  lines: string[];
  error: string | null;
};

export type DiagnosticsRead = {
  checks: DiagnosticCheckRead[];
  logs: DiagnosticLogRead[];
};

export type TelegramSettingsRead = {
  bot_username: string | null;
  bot_token_set: boolean;
  admin_telegram_id: string | null;
  socks5_enabled: boolean;
  socks5_host: string | null;
  socks5_port: number | null;
  socks5_username_set: boolean;
  admin_email: string;
};

export type TelegramSettingsUpdate = {
  bot_username?: string;
  bot_token?: string;
  admin_telegram_id?: string;
  socks5_enabled: boolean;
  socks5_host?: string;
  socks5_port?: number;
  socks5_username?: string;
  socks5_password?: string;
  admin_email?: string;
  current_password?: string;
  new_password?: string;
};

export type TelegramTestMessageResult = {
  ok: boolean;
  message: string;
};

export async function getUpdateStatus(): Promise<AdminUpdateStatus> {
  const response = await api.get<AdminUpdateStatus>("/system/updates");
  return response.data;
}

export async function startUpdate(): Promise<AdminUpdateStatus> {
  const response = await api.post<AdminUpdateStatus>("/system/updates");
  return response.data;
}

export async function getDiagnostics(params?: {
  services?: string[];
  tail?: number;
}): Promise<DiagnosticsRead> {
  const response = await api.get<DiagnosticsRead>("/system/diagnostics", {
    params: {
      services: params?.services,
      tail: params?.tail,
    },
    paramsSerializer: { indexes: null },
  });
  return response.data;
}

export async function getTelegramSettings(): Promise<TelegramSettingsRead> {
  const response = await api.get<TelegramSettingsRead>("/system/telegram-settings");
  return response.data;
}

export async function updateTelegramSettings(
  payload: TelegramSettingsUpdate,
): Promise<TelegramSettingsRead> {
  const response = await api.put<TelegramSettingsRead>("/system/telegram-settings", payload);
  return response.data;
}

export async function sendTelegramTestMessage(): Promise<TelegramTestMessageResult> {
  const response = await api.post<TelegramTestMessageResult>(
    "/system/telegram-settings/test-message",
  );
  return response.data;
}
