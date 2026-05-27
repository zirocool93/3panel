import { EditOutlined, ReloadOutlined, TagsOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
  type TableColumnsType,
} from "antd";
import axios from "axios";
import { useEffect, useMemo, useState } from "react";

import {
  listServerInbounds,
  listServers,
  type ServerInboundRead,
  type ServerRead,
} from "../../api/servers";
import {
  createTariff,
  listTariffs,
  updateTariff,
  type TariffInboundLink,
  type TariffPayload,
  type TariffRead,
} from "../../api/tariffs";
import { ru } from "../../i18n/ru";

type TariffForm = {
  name: string;
  description?: string;
  price: number;
  price_stars?: number;
  price_crypto?: number;
  currency: string;
  crypto_currency?: string;
  duration_days: number;
  traffic_limit_gb?: number;
  device_limit?: number;
  inbound_keys: string[];
  sort_order: number;
  is_trial: boolean;
  enabled: boolean;
  is_visible: boolean;
};

type InboundOption = {
  value: string;
  label: string;
  link: TariffInboundLink;
};

export function TariffsPage() {
  const [form] = Form.useForm<TariffForm>();
  const [tariffs, setTariffs] = useState<TariffRead[]>([]);
  const [servers, setServers] = useState<ServerRead[]>([]);
  const [inboundOptions, setInboundOptions] = useState<InboundOption[]>([]);
  const [editingTariff, setEditingTariff] = useState<TariffRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [inboundsLoading, setInboundsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();

  async function refreshTariffs() {
    setLoading(true);
    try {
      setTariffs(await listTariffs());
      setError(null);
    } catch {
      setError(ru.tariffs.loadError);
    } finally {
      setLoading(false);
    }
  }

  async function refreshInboundOptions() {
    setInboundsLoading(true);
    try {
      const serverList = await listServers();
      setServers(serverList);
      const optionGroups = await Promise.all(
        serverList.map(async (server) => {
          try {
            const inbounds = await listServerInbounds(server.id);
            return inbounds.map((inbound) => inboundToOption(server, inbound));
          } catch {
            return [];
          }
        }),
      );
      setInboundOptions(optionGroups.flat());
    } catch {
      messageApi.error(ru.tariffs.inboundLoadError);
    } finally {
      setInboundsLoading(false);
    }
  }

  async function submit(values: TariffForm) {
    setSaving(true);
    try {
      const payload: TariffPayload = {
        name: values.name,
        description: values.description || undefined,
        price: String(values.price),
        currency: values.currency || "RUB",
        prices: buildTariffPrices(values),
        duration_days: values.duration_days,
        traffic_limit_gb: values.traffic_limit_gb,
        device_limit: values.device_limit,
        inbound_links: values.inbound_keys.map((key) => inboundOptionByKey[key].link),
        sort_order: values.sort_order ?? 0,
        is_trial: values.is_trial ?? false,
        enabled: values.enabled ?? true,
        is_visible: values.is_visible ?? true,
      };
      if (editingTariff) {
        await updateTariff(editingTariff.id, payload);
        messageApi.success(ru.tariffs.updateSuccess);
      } else {
        await createTariff(payload);
        messageApi.success(ru.tariffs.createSuccess);
      }
      resetForm();
      await refreshTariffs();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || (editingTariff ? ru.tariffs.updateError : ru.tariffs.createError));
    } finally {
      setSaving(false);
    }
  }

  function startEdit(tariff: TariffRead) {
    setEditingTariff(tariff);
    form.setFieldsValue({
      name: tariff.name,
      description: tariff.description || undefined,
      price: Number(tariff.price),
      price_stars: tariffPriceAmount(tariff, "telegram_stars"),
      price_crypto: tariffPriceAmount(tariff, "crypto"),
      currency: tariff.currency,
      crypto_currency: tariffPriceCurrency(tariff, "crypto") || "USDT",
      duration_days: tariff.duration_days,
      traffic_limit_gb: tariff.traffic_limit_gb || undefined,
      device_limit: tariff.device_limit || undefined,
      inbound_keys: tariff.inbound_links.map(inboundKey),
      sort_order: tariff.sort_order,
      is_trial: tariff.is_trial,
      enabled: tariff.enabled,
      is_visible: tariff.is_visible,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() {
    setEditingTariff(null);
    form.resetFields();
    form.setFieldsValue(defaultFormValues);
  }

  useEffect(() => {
    form.setFieldsValue(defaultFormValues);
    void refreshTariffs();
    void refreshInboundOptions();
  }, [form]);

  const inboundOptionByKey = useMemo(
    () => Object.fromEntries(inboundOptions.map((option) => [option.value, option])),
    [inboundOptions],
  );

  const columns: TableColumnsType<TariffRead> = [
    {
      title: ru.tariffs.columns.name,
      dataIndex: "name",
      render: (name: string, tariff) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{name}</Typography.Text>
          {tariff.description ? (
            <Typography.Text type="secondary">{tariff.description}</Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: ru.tariffs.columns.price,
      width: 220,
      render: (_, tariff) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{`${tariff.price} ${tariff.currency}`}</Typography.Text>
          {tariff.prices
            .filter((price) => price.enabled && price.payment_method !== "manual")
            .map((price) => (
              <Typography.Text key={price.payment_method} type="secondary">
                {paymentMethodLabel(price.payment_method)}: {price.amount} {price.currency}
              </Typography.Text>
            ))}
        </Space>
      ),
    },
    {
      title: ru.tariffs.columns.duration,
      width: 110,
      render: (_, tariff) => `${tariff.duration_days} ${ru.tariffs.days}`,
    },
    {
      title: ru.tariffs.columns.traffic,
      width: 130,
      render: (_, tariff) =>
        tariff.traffic_limit_gb ? `${tariff.traffic_limit_gb} GB` : ru.tariffs.unlimited,
    },
    {
      title: ru.tariffs.columns.devices,
      width: 130,
      render: (_, tariff) => tariff.device_limit ?? ru.tariffs.unlimited,
    },
    {
      title: ru.tariffs.columns.inbounds,
      render: (_, tariff) =>
        tariff.inbound_links.length ? (
          <Space wrap>
            {tariff.inbound_links.map((link) => (
              <Tag key={`${link.server_id}:${link.inbound_id}`}>
                {serverName(link.server_id)} / {link.inbound_remark || `#${link.inbound_id}`}
              </Tag>
            ))}
          </Space>
        ) : (
          ru.tariffs.noInbounds
        ),
    },
    {
      title: ru.tariffs.columns.status,
      width: 110,
      render: (_, tariff) => (
        <Tag color={tariff.enabled ? "green" : "default"}>
          {tariff.enabled ? ru.common.enabled : ru.common.disabled}
        </Tag>
      ),
    },
    {
      title: ru.tariffs.columns.visible,
      width: 110,
      render: (_, tariff) => (
        <Tag color={tariff.is_visible ? "blue" : "default"}>
          {tariff.is_visible ? ru.tariffs.visible : ru.tariffs.hidden}
        </Tag>
      ),
    },
    {
      title: ru.tariffs.columns.actions,
      width: 150,
      render: (_, tariff) => (
        <Button icon={<EditOutlined />} onClick={() => startEdit(tariff)}>
          {ru.tariffs.actions.edit}
        </Button>
      ),
    },
  ];

  function serverName(serverId: number): string {
    return servers.find((server) => server.id === serverId)?.name || `#${serverId}`;
  }

  return (
    <section className="settings-page">
      {messageContext}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>{ru.tariffs.title}</Typography.Title>
          <Typography.Paragraph>{ru.tariffs.description}</Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshTariffs()}>
          {ru.xui.reload}
        </Button>
      </div>
      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <section className="settings-section">
        <Typography.Title level={4}>
          <TagsOutlined /> {editingTariff ? ru.tariffs.edit : ru.tariffs.add}
        </Typography.Title>
        <Form<TariffForm>
          className="xui-form"
          form={form}
          layout="vertical"
          onFinish={submit}
          requiredMark={false}
        >
          <Form.Item
            label={ru.tariffs.form.name}
            name="name"
            rules={[{ required: true, message: ru.tariffs.form.required }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label={ru.tariffs.form.priceRub}
            name="price"
            rules={[{ required: true, message: ru.tariffs.form.required }]}
          >
            <InputNumber min={0} precision={2} />
          </Form.Item>
          <Form.Item
            label={ru.tariffs.form.currency}
            name="currency"
            rules={[{ required: true, message: ru.tariffs.form.required }]}
          >
            <Input maxLength={3} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.priceStars} name="price_stars">
            <InputNumber min={0} precision={0} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.priceCrypto} name="price_crypto">
            <InputNumber min={0} precision={2} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.cryptoCurrency} name="crypto_currency">
            <Input maxLength={16} />
          </Form.Item>
          <Form.Item
            label={ru.tariffs.form.durationDays}
            name="duration_days"
            rules={[{ required: true, message: ru.tariffs.form.required }]}
          >
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.trafficLimitGb} name="traffic_limit_gb">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.deviceLimit} name="device_limit">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item
            className="grid-wide"
            label={ru.tariffs.form.inbounds}
            name="inbound_keys"
            rules={[{ required: true, message: ru.tariffs.form.required }]}
          >
            <Select
              loading={inboundsLoading}
              mode="multiple"
              options={inboundOptions.map(({ value, label }) => ({ value, label }))}
            />
          </Form.Item>
          <Form.Item className="grid-wide" label={ru.tariffs.form.description} name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.sortOrder} name="sort_order">
            <InputNumber precision={0} />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.isTrial} name="is_trial" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.enabled} name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label={ru.tariffs.form.visible} name="is_visible" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item className="form-actions">
            <Space wrap>
              <Button htmlType="submit" loading={saving} type="primary">
                {ru.common.save}
              </Button>
              {editingTariff ? <Button onClick={resetForm}>{ru.common.cancel}</Button> : null}
            </Space>
          </Form.Item>
        </Form>
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>{ru.tariffs.list}</Typography.Title>
        <Table
          columns={columns}
          dataSource={tariffs}
          loading={loading}
          locale={{ emptyText: ru.tariffs.empty }}
          pagination={{ pageSize: 10 }}
          rowKey="id"
          scroll={{ x: 1300 }}
        />
      </section>
    </section>
  );
}

const defaultFormValues: Partial<TariffForm> = {
  currency: "RUB",
  crypto_currency: "USDT",
  duration_days: 30,
  inbound_keys: [],
  sort_order: 0,
  is_trial: false,
  enabled: true,
  is_visible: true,
};

function inboundToOption(server: ServerRead, inbound: ServerInboundRead): InboundOption {
  const link = {
    server_id: server.id,
    inbound_id: String(inbound.id),
    inbound_remark: inbound.remark,
    protocol: inbound.protocol,
  };
  return {
    value: inboundKey(link),
    label: `${server.name} / ${inbound.remark || `#${inbound.id}`} (${inbound.protocol || "?"})`,
    link,
  };
}

function buildTariffPrices(values: TariffForm) {
  const prices = [
    {
      payment_method: "manual",
      amount: String(values.price),
      currency: values.currency || "RUB",
      enabled: true,
    },
    {
      payment_method: "balance",
      amount: String(values.price),
      currency: values.currency || "RUB",
      enabled: true,
    },
    {
      payment_method: "cardlink",
      amount: String(values.price),
      currency: values.currency || "RUB",
      enabled: true,
    },
    {
      payment_method: "yookassa",
      amount: String(values.price),
      currency: values.currency || "RUB",
      enabled: true,
    },
  ];
  if (values.price_stars !== undefined) {
    prices.push({
      payment_method: "telegram_stars",
      amount: String(values.price_stars),
      currency: "XTR",
      enabled: true,
    });
  }
  if (values.price_crypto !== undefined) {
    prices.push({
      payment_method: "crypto",
      amount: String(values.price_crypto),
      currency: values.crypto_currency || "USDT",
      enabled: true,
    });
  }
  return prices;
}

function tariffPriceAmount(tariff: TariffRead, paymentMethod: string): number | undefined {
  const price = tariff.prices.find((item) => item.payment_method === paymentMethod);
  return price ? Number(price.amount) : undefined;
}

function tariffPriceCurrency(tariff: TariffRead, paymentMethod: string): string | undefined {
  return tariff.prices.find((item) => item.payment_method === paymentMethod)?.currency;
}

function paymentMethodLabel(paymentMethod: string): string {
  const labels: Record<string, string> = {
    balance: "Баланс",
    cardlink: "Cardlink",
    yookassa: "ЮKassa",
    telegram_stars: "Stars",
    crypto: "Крипта",
  };
  return labels[paymentMethod] || paymentMethod;
}

function inboundKey(link: Pick<TariffInboundLink, "server_id" | "inbound_id">): string {
  return `${link.server_id}:${link.inbound_id}`;
}
