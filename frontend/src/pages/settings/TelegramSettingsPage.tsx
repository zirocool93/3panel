import { LockOutlined, ReloadOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, InputNumber, Space, Switch, Typography, message } from "antd";
import axios from "axios";
import { useEffect, useState } from "react";

import {
  getTelegramSettings,
  updateTelegramSettings,
  type TelegramSettingsRead,
  type TelegramSettingsUpdate,
} from "../../api/system";
import { ru } from "../../i18n/ru";

type TelegramSettingsForm = {
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

export function TelegramSettingsPage() {
  const [form] = Form.useForm<TelegramSettingsForm>();
  const [settings, setSettings] = useState<TelegramSettingsRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();
  const socks5Enabled = Form.useWatch("socks5_enabled", form);

  async function refreshSettings() {
    setLoading(true);
    try {
      const loaded = await getTelegramSettings();
      setSettings(loaded);
      form.setFieldsValue({
        bot_username: loaded.bot_username || undefined,
        bot_token: undefined,
        admin_telegram_id: loaded.admin_telegram_id || undefined,
        socks5_enabled: loaded.socks5_enabled,
        socks5_host: loaded.socks5_host || undefined,
        socks5_port: loaded.socks5_port || undefined,
        socks5_username: undefined,
        socks5_password: undefined,
        admin_email: loaded.admin_email,
        current_password: undefined,
        new_password: undefined,
      });
      setError(null);
    } catch {
      setError(ru.telegramSettings.loadError);
    } finally {
      setLoading(false);
    }
  }

  async function submit(values: TelegramSettingsForm) {
    setSaving(true);
    try {
      const payload: TelegramSettingsUpdate = {
        bot_username: values.bot_username || undefined,
        admin_telegram_id: values.admin_telegram_id || undefined,
        socks5_enabled: values.socks5_enabled ?? false,
        socks5_host: values.socks5_enabled ? values.socks5_host || undefined : undefined,
        socks5_port: values.socks5_enabled ? values.socks5_port : undefined,
        admin_email: values.admin_email || undefined,
        current_password: values.current_password || undefined,
        new_password: values.new_password || undefined,
      };
      if (values.bot_token) {
        payload.bot_token = values.bot_token;
      }
      if (values.socks5_username) {
        payload.socks5_username = values.socks5_username;
      }
      if (values.socks5_password) {
        payload.socks5_password = values.socks5_password;
      }

      const updated = await updateTelegramSettings(payload);
      setSettings(updated);
      form.setFieldsValue({
        bot_token: undefined,
        socks5_username: undefined,
        socks5_password: undefined,
        current_password: undefined,
        new_password: undefined,
      });
      messageApi.success(ru.telegramSettings.saveSuccess);
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.telegramSettings.saveError);
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void refreshSettings();
  }, []);

  return (
    <section className="settings-page">
      {messageContext}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>{ru.telegramSettings.title}</Typography.Title>
          <Typography.Paragraph>{ru.telegramSettings.description}</Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshSettings()}>
          {ru.common.refresh}
        </Button>
      </div>

      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <Form<TelegramSettingsForm>
        className="xui-form"
        form={form}
        layout="vertical"
        onFinish={submit}
        requiredMark={false}
      >
        <section className="settings-section">
          <Typography.Title level={4}>
            <RobotOutlined /> {ru.telegramSettings.botSection}
          </Typography.Title>
          {settings?.bot_token_set ? (
            <Alert className="page-alert" message={ru.telegramSettings.tokenHint} showIcon />
          ) : null}
          <Form.Item label={ru.telegramSettings.form.botUsername} name="bot_username">
            <Input placeholder="my_vpn_bot" />
          </Form.Item>
          <Form.Item label={ru.telegramSettings.form.botToken} name="bot_token">
            <Input.Password autoComplete="off" placeholder="123456:ABC..." />
          </Form.Item>
          <Form.Item label={ru.telegramSettings.form.adminTelegramId} name="admin_telegram_id">
            <Input placeholder="123456789" />
          </Form.Item>
        </section>

        <section className="settings-section">
          <Typography.Title level={4}>
            <LockOutlined /> {ru.telegramSettings.proxySection}
          </Typography.Title>
          <Form.Item
            label={ru.telegramSettings.form.socks5Enabled}
            name="socks5_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label={ru.telegramSettings.form.socks5Host}
            name="socks5_host"
            rules={[
              {
                required: socks5Enabled,
                message: ru.telegramSettings.form.required,
              },
            ]}
          >
            <Input disabled={!socks5Enabled} placeholder="127.0.0.1" />
          </Form.Item>
          <Form.Item
            label={ru.telegramSettings.form.socks5Port}
            name="socks5_port"
            rules={[
              {
                required: socks5Enabled,
                message: ru.telegramSettings.form.required,
              },
            ]}
          >
            <InputNumber disabled={!socks5Enabled} max={65535} min={1} />
          </Form.Item>
          {settings?.socks5_username_set ? (
            <Alert className="page-alert" message={ru.telegramSettings.proxySecretHint} showIcon />
          ) : null}
          <Form.Item label={ru.telegramSettings.form.socks5Username} name="socks5_username">
            <Input autoComplete="off" disabled={!socks5Enabled} />
          </Form.Item>
          <Form.Item label={ru.telegramSettings.form.socks5Password} name="socks5_password">
            <Input.Password autoComplete="off" disabled={!socks5Enabled} />
          </Form.Item>
        </section>

        <section className="settings-section">
          <Typography.Title level={4}>
            <UserOutlined /> {ru.telegramSettings.adminSection}
          </Typography.Title>
          <Form.Item
            label={ru.telegramSettings.form.adminEmail}
            name="admin_email"
            rules={[{ type: "email", message: ru.telegramSettings.form.email }]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item label={ru.telegramSettings.form.currentPassword} name="current_password">
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item label={ru.telegramSettings.form.newPassword} name="new_password">
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </section>

        <section className="settings-section">
          <Form.Item className="form-actions">
            <Space wrap>
              <Button htmlType="submit" loading={saving} type="primary">
                {ru.common.save}
              </Button>
            </Space>
          </Form.Item>
        </section>
      </Form>
    </section>
  );
}
