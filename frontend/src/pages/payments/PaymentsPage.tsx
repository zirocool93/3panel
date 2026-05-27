import {
  BankOutlined,
  CreditCardOutlined,
  DollarOutlined,
  ReloadOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { Alert, Button, Form, Input, InputNumber, Space, Switch, Typography, message } from "antd";
import axios from "axios";
import { useEffect, useState } from "react";

import {
  getPaymentSettings,
  updatePaymentSettings,
  type PaymentSettingsRead,
  type PaymentSettingsUpdate,
} from "../../api/payments";
import { ru } from "../../i18n/ru";

type PaymentSettingsForm = {
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

export function PaymentsPage() {
  const [form] = Form.useForm<PaymentSettingsForm>();
  const [settings, setSettings] = useState<PaymentSettingsRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();
  const telegramStarsEnabled = Form.useWatch("telegram_stars_enabled", form);
  const cardlinkEnabled = Form.useWatch("cardlink_enabled", form);
  const yookassaEnabled = Form.useWatch("yookassa_enabled", form);

  async function refreshSettings() {
    setLoading(true);
    try {
      const loaded = await getPaymentSettings();
      setSettings(loaded);
      form.setFieldsValue({
        manual_payments_enabled: loaded.manual_payments_enabled,
        manual_payment_instructions: loaded.manual_payment_instructions || undefined,
        telegram_stars_enabled: loaded.telegram_stars_enabled,
        telegram_stars_rate_rub: loaded.telegram_stars_rate_rub || undefined,
        telegram_stars_invoice_title: loaded.telegram_stars_invoice_title || undefined,
        telegram_stars_invoice_description:
          loaded.telegram_stars_invoice_description || undefined,
        cardlink_enabled: loaded.cardlink_enabled,
        cardlink_api_base_url: loaded.cardlink_api_base_url || "https://cardlink.link",
        cardlink_shop_id: loaded.cardlink_shop_id || undefined,
        cardlink_api_token: undefined,
        cardlink_currency: loaded.cardlink_currency || "RUB",
        cardlink_locale: loaded.cardlink_locale || "ru",
        cardlink_payer_pays_commission: loaded.cardlink_payer_pays_commission,
        cardlink_success_url: loaded.cardlink_success_url || undefined,
        cardlink_fail_url: loaded.cardlink_fail_url || undefined,
        yookassa_enabled: loaded.yookassa_enabled,
        yookassa_shop_id: loaded.yookassa_shop_id || undefined,
        yookassa_secret_key: undefined,
        yookassa_return_url: loaded.yookassa_return_url || undefined,
        yookassa_currency: loaded.yookassa_currency || "RUB",
      });
      setError(null);
    } catch {
      setError(ru.payments.loadError);
    } finally {
      setLoading(false);
    }
  }

  async function submit(values: PaymentSettingsForm) {
    setSaving(true);
    try {
      const payload: PaymentSettingsUpdate = {
        manual_payments_enabled: values.manual_payments_enabled,
        manual_payment_instructions: values.manual_payment_instructions || undefined,
        telegram_stars_enabled: values.telegram_stars_enabled,
        telegram_stars_rate_rub: values.telegram_stars_rate_rub,
        telegram_stars_invoice_title: values.telegram_stars_invoice_title || undefined,
        telegram_stars_invoice_description:
          values.telegram_stars_invoice_description || undefined,
        cardlink_enabled: values.cardlink_enabled,
        cardlink_api_base_url: values.cardlink_api_base_url || undefined,
        cardlink_shop_id: values.cardlink_shop_id || undefined,
        cardlink_currency: values.cardlink_currency || "RUB",
        cardlink_locale: values.cardlink_locale || "ru",
        cardlink_payer_pays_commission: values.cardlink_payer_pays_commission,
        cardlink_success_url: values.cardlink_success_url || undefined,
        cardlink_fail_url: values.cardlink_fail_url || undefined,
        yookassa_enabled: values.yookassa_enabled,
        yookassa_shop_id: values.yookassa_shop_id || undefined,
        yookassa_return_url: values.yookassa_return_url || undefined,
        yookassa_currency: values.yookassa_currency || "RUB",
      };
      if (values.cardlink_api_token) {
        payload.cardlink_api_token = values.cardlink_api_token;
      }
      if (values.yookassa_secret_key) {
        payload.yookassa_secret_key = values.yookassa_secret_key;
      }

      const updated = await updatePaymentSettings(payload);
      setSettings(updated);
      form.setFieldsValue({ cardlink_api_token: undefined, yookassa_secret_key: undefined });
      messageApi.success(ru.payments.saveSuccess);
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.payments.saveError);
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
          <Typography.Title level={2}>{ru.payments.title}</Typography.Title>
          <Typography.Paragraph>{ru.payments.description}</Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshSettings()}>
          {ru.common.refresh}
        </Button>
      </div>
      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <Form<PaymentSettingsForm>
        className="xui-form"
        form={form}
        layout="vertical"
        onFinish={submit}
        requiredMark={false}
      >
        <section className="settings-section grid-wide">
          <Typography.Title level={4}>
            <DollarOutlined /> {ru.payments.manualSection}
          </Typography.Title>
          <Form.Item
            label={ru.payments.form.manualEnabled}
            name="manual_payments_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            className="grid-wide"
            label={ru.payments.form.manualInstructions}
            name="manual_payment_instructions"
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </section>

        <section className="settings-section grid-wide">
          <Typography.Title level={4}>
            <StarOutlined /> {ru.payments.telegramStarsSection}
          </Typography.Title>
          <Form.Item
            label={ru.payments.form.telegramStarsEnabled}
            name="telegram_stars_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.telegramStarsRate}
            name="telegram_stars_rate_rub"
            rules={[{ required: telegramStarsEnabled, message: ru.payments.form.required }]}
          >
            <InputNumber disabled={!telegramStarsEnabled} min={1} precision={0} />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.telegramStarsTitle}
            name="telegram_stars_invoice_title"
          >
            <Input disabled={!telegramStarsEnabled} placeholder="VPN подписка" />
          </Form.Item>
          <Form.Item
            className="grid-wide"
            label={ru.payments.form.telegramStarsDescription}
            name="telegram_stars_invoice_description"
          >
            <Input.TextArea disabled={!telegramStarsEnabled} rows={3} />
          </Form.Item>
        </section>

        <section className="settings-section grid-wide">
          <Typography.Title level={4}>
            <CreditCardOutlined /> {ru.payments.cardlinkSection}
          </Typography.Title>
          {settings?.cardlink_api_token_set ? (
            <Alert className="page-alert" message={ru.payments.cardlinkSecretHint} showIcon />
          ) : null}
          <Form.Item
            label={ru.payments.form.cardlinkEnabled}
            name="cardlink_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.cardlinkApiBaseUrl}
            name="cardlink_api_base_url"
            rules={[{ required: cardlinkEnabled, message: ru.payments.form.required }]}
          >
            <Input disabled={!cardlinkEnabled} placeholder="https://cardlink.link" />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.cardlinkShopId}
            name="cardlink_shop_id"
            rules={[{ required: cardlinkEnabled, message: ru.payments.form.required }]}
          >
            <Input disabled={!cardlinkEnabled} />
          </Form.Item>
          <Form.Item label={ru.payments.form.cardlinkApiToken} name="cardlink_api_token">
            <Input.Password autoComplete="off" disabled={!cardlinkEnabled} />
          </Form.Item>
          <Form.Item label={ru.payments.form.currency} name="cardlink_currency">
            <Input disabled={!cardlinkEnabled} maxLength={3} placeholder="RUB" />
          </Form.Item>
          <Form.Item label={ru.payments.form.cardlinkLocale} name="cardlink_locale">
            <Input disabled={!cardlinkEnabled} placeholder="ru" />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.cardlinkPayerPaysCommission}
            name="cardlink_payer_pays_commission"
            valuePropName="checked"
          >
            <Switch disabled={!cardlinkEnabled} />
          </Form.Item>
          <Form.Item label={ru.payments.form.cardlinkSuccessUrl} name="cardlink_success_url">
            <Input disabled={!cardlinkEnabled} placeholder="https://example.com/payment/success" />
          </Form.Item>
          <Form.Item label={ru.payments.form.cardlinkFailUrl} name="cardlink_fail_url">
            <Input disabled={!cardlinkEnabled} placeholder="https://example.com/payment/fail" />
          </Form.Item>
        </section>

        <section className="settings-section grid-wide">
          <Typography.Title level={4}>
            <BankOutlined /> {ru.payments.yookassaSection}
          </Typography.Title>
          {settings?.yookassa_secret_key_set ? (
            <Alert className="page-alert" message={ru.payments.yookassaSecretHint} showIcon />
          ) : null}
          <Form.Item
            label={ru.payments.form.yookassaEnabled}
            name="yookassa_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.yookassaShopId}
            name="yookassa_shop_id"
            rules={[{ required: yookassaEnabled, message: ru.payments.form.required }]}
          >
            <Input disabled={!yookassaEnabled} />
          </Form.Item>
          <Form.Item label={ru.payments.form.yookassaSecretKey} name="yookassa_secret_key">
            <Input.Password autoComplete="off" disabled={!yookassaEnabled} />
          </Form.Item>
          <Form.Item
            label={ru.payments.form.yookassaReturnUrl}
            name="yookassa_return_url"
            rules={[{ required: yookassaEnabled, message: ru.payments.form.required }]}
          >
            <Input disabled={!yookassaEnabled} placeholder="https://example.com/payment/return" />
          </Form.Item>
          <Form.Item label={ru.payments.form.currency} name="yookassa_currency">
            <Input disabled={!yookassaEnabled} maxLength={3} placeholder="RUB" />
          </Form.Item>
        </section>

        <section className="settings-section grid-wide">
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
