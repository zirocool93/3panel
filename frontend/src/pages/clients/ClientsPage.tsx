import { EditOutlined, IdcardOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
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
import { useEffect, useState } from "react";

import {
  createClient,
  createClientSubscription,
  listClients,
  updateClient,
  type ClientPayload,
  type ClientRead,
  type ClientSubscriptionPayload,
  type ClientSubscriptionRead,
} from "../../api/clients";
import { listTariffs, type TariffRead } from "../../api/tariffs";
import { ru } from "../../i18n/ru";

type ClientForm = {
  display_name: string;
  telegram_id?: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  comment?: string;
  is_blocked: boolean;
};

type SubscriptionForm = {
  client_id: number;
  tariff_id: number;
  payment_method: string;
  price_amount?: number;
  currency?: string;
  duration_days?: number;
  traffic_limit_gb?: number;
  device_limit?: number;
  admin_comment?: string;
};

export function ClientsPage() {
  const [clientForm] = Form.useForm<ClientForm>();
  const [subscriptionForm] = Form.useForm<SubscriptionForm>();
  const [clients, setClients] = useState<ClientRead[]>([]);
  const [tariffs, setTariffs] = useState<TariffRead[]>([]);
  const [editingClient, setEditingClient] = useState<ClientRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingClient, setSavingClient] = useState(false);
  const [savingSubscription, setSavingSubscription] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();

  async function refreshClients() {
    setLoading(true);
    try {
      setClients(await listClients());
      setError(null);
    } catch {
      setError(ru.clients.loadError);
    } finally {
      setLoading(false);
    }
  }

  async function refreshTariffs() {
    setTariffs(await listTariffs());
  }

  async function submitClient(values: ClientForm) {
    setSavingClient(true);
    try {
      const payload: ClientPayload = {
        display_name: values.display_name,
        telegram_id: values.telegram_id,
        username: values.username || undefined,
        first_name: values.first_name || undefined,
        last_name: values.last_name || undefined,
        comment: values.comment || undefined,
        is_blocked: values.is_blocked,
      };
      if (editingClient) {
        await updateClient(editingClient.id, payload);
        messageApi.success(ru.clients.updateSuccess);
      } else {
        await createClient(payload);
        messageApi.success(ru.clients.createSuccess);
      }
      resetClientForm();
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || (editingClient ? ru.clients.updateError : ru.clients.createError));
    } finally {
      setSavingClient(false);
    }
  }

  async function submitSubscription(values: SubscriptionForm) {
    setSavingSubscription(true);
    try {
      const payload: ClientSubscriptionPayload = {
        tariff_id: values.tariff_id,
        payment_method: values.payment_method,
        price_amount: values.price_amount !== undefined ? String(values.price_amount) : undefined,
        currency: values.currency || undefined,
        duration_days: values.duration_days,
        traffic_limit_gb: values.traffic_limit_gb,
        device_limit: values.device_limit,
        admin_comment: values.admin_comment || undefined,
      };
      await createClientSubscription(values.client_id, payload);
      subscriptionForm.resetFields();
      subscriptionForm.setFieldsValue({ payment_method: "manual" });
      messageApi.success(ru.clients.subscriptionSuccess);
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.clients.subscriptionError);
    } finally {
      setSavingSubscription(false);
    }
  }

  function startEdit(client: ClientRead) {
    setEditingClient(client);
    clientForm.setFieldsValue({
      display_name: client.display_name || "",
      telegram_id: client.telegram_id || undefined,
      username: client.username || undefined,
      first_name: client.first_name || undefined,
      last_name: client.last_name || undefined,
      comment: client.comment || undefined,
      is_blocked: client.is_blocked,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetClientForm() {
    setEditingClient(null);
    clientForm.resetFields();
    clientForm.setFieldsValue({ is_blocked: false });
  }

  useEffect(() => {
    clientForm.setFieldsValue({ is_blocked: false });
    subscriptionForm.setFieldsValue({ payment_method: "manual" });
    void refreshClients();
    void refreshTariffs();
  }, [clientForm, subscriptionForm]);

  const columns: TableColumnsType<ClientRead> = [
    {
      title: ru.clients.columns.client,
      render: (_, client) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{client.display_name || client.username || `#${client.id}`}</Typography.Text>
          {client.username ? <Typography.Text type="secondary">@{client.username}</Typography.Text> : null}
        </Space>
      ),
    },
    {
      title: ru.clients.columns.telegram,
      width: 150,
      render: (_, client) => client.telegram_id || "—",
    },
    { title: ru.clients.columns.balance, dataIndex: "balance", width: 120 },
    { title: ru.clients.columns.subscriptions, dataIndex: "subscriptions_count", width: 120 },
    {
      title: ru.clients.columns.status,
      width: 120,
      render: (_, client) => (
        <Tag color={client.is_blocked ? "red" : "green"}>
          {client.is_blocked ? ru.common.disabled : ru.common.enabled}
        </Tag>
      ),
    },
    { title: ru.clients.columns.comment, dataIndex: "comment" },
    {
      title: ru.clients.columns.actions,
      width: 150,
      render: (_, client) => (
        <Button icon={<EditOutlined />} onClick={() => startEdit(client)}>
          {ru.tariffs.actions.edit}
        </Button>
      ),
    },
  ];

  return (
    <section className="settings-page">
      {messageContext}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>{ru.clients.title}</Typography.Title>
          <Typography.Paragraph>{ru.clients.description}</Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshClients()}>
          {ru.xui.reload}
        </Button>
      </div>
      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <section className="settings-section">
        <Typography.Title level={4}>
          <IdcardOutlined /> {editingClient ? ru.clients.edit : ru.clients.add}
        </Typography.Title>
        <Alert className="page-alert" message={ru.clients.manualHint} showIcon type="info" />
        <Form<ClientForm>
          className="xui-form"
          form={clientForm}
          layout="vertical"
          onFinish={submitClient}
          requiredMark={false}
        >
          <Form.Item
            label={ru.clients.form.displayName}
            name="display_name"
            rules={[{ required: true, message: ru.clients.form.required }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label={ru.clients.form.telegramId} name="telegram_id">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item label={ru.clients.form.username} name="username">
            <Input />
          </Form.Item>
          <Form.Item label={ru.clients.form.firstName} name="first_name">
            <Input />
          </Form.Item>
          <Form.Item label={ru.clients.form.lastName} name="last_name">
            <Input />
          </Form.Item>
          <Form.Item label={ru.clients.form.blocked} name="is_blocked" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item className="grid-wide" label={ru.clients.form.comment} name="comment">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item className="form-actions">
            <Space wrap>
              <Button htmlType="submit" loading={savingClient} type="primary">
                {ru.common.save}
              </Button>
              {editingClient ? <Button onClick={resetClientForm}>{ru.common.cancel}</Button> : null}
            </Space>
          </Form.Item>
        </Form>
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>
          <PlusOutlined /> {ru.clients.subscription}
        </Typography.Title>
        <Form<SubscriptionForm>
          className="xui-form"
          form={subscriptionForm}
          layout="vertical"
          onFinish={submitSubscription}
          requiredMark={false}
        >
          <Form.Item
            label={ru.clients.subscriptionForm.client}
            name="client_id"
            rules={[{ required: true, message: ru.clients.form.required }]}
          >
            <Select
              options={clients.map((client) => ({
                label: client.display_name || client.username || `#${client.id}`,
                value: client.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            label={ru.clients.subscriptionForm.tariff}
            name="tariff_id"
            rules={[{ required: true, message: ru.clients.form.required }]}
          >
            <Select options={tariffs.map((tariff) => ({ label: tariff.name, value: tariff.id }))} />
          </Form.Item>
          <Form.Item
            label={ru.clients.subscriptionForm.paymentMethod}
            name="payment_method"
            rules={[{ required: true, message: ru.clients.form.required }]}
          >
            <Select
              options={[
                { label: ru.clients.paymentMethods.manual, value: "manual" },
                { label: ru.clients.paymentMethods.balance, value: "balance" },
                { label: ru.clients.paymentMethods.telegram_stars, value: "telegram_stars" },
                { label: ru.clients.paymentMethods.cryptobot, value: "cryptobot" },
              ]}
            />
          </Form.Item>
          <Form.Item label={ru.clients.subscriptionForm.priceAmount} name="price_amount">
            <InputNumber min={0} precision={2} />
          </Form.Item>
          <Form.Item label={ru.clients.subscriptionForm.currency} name="currency">
            <Input maxLength={3} placeholder="RUB" />
          </Form.Item>
          <Form.Item label={ru.clients.subscriptionForm.durationDays} name="duration_days">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item label={ru.clients.subscriptionForm.trafficLimitGb} name="traffic_limit_gb">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item label={ru.clients.subscriptionForm.deviceLimit} name="device_limit">
            <InputNumber min={1} precision={0} />
          </Form.Item>
          <Form.Item className="grid-wide" label={ru.clients.subscriptionForm.comment} name="admin_comment">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item className="form-actions">
            <Button htmlType="submit" loading={savingSubscription} type="primary">
              {ru.clients.subscription}
            </Button>
          </Form.Item>
        </Form>
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>{ru.clients.list}</Typography.Title>
        <Table
          columns={columns}
          dataSource={clients}
          expandable={{ expandedRowRender: renderSubscriptions }}
          loading={loading}
          locale={{ emptyText: ru.clients.empty }}
          pagination={{ pageSize: 10 }}
          rowKey="id"
          scroll={{ x: 1100 }}
        />
      </section>
    </section>
  );
}

function renderSubscriptions(client: ClientRead) {
  if (!client.subscriptions.length) {
    return <Typography.Text type="secondary">{ru.clients.noSubscriptions}</Typography.Text>;
  }
  const columns: TableColumnsType<ClientSubscriptionRead> = [
    { title: ru.clients.columns.tariff, dataIndex: "tariff_name" },
    { title: ru.clients.columns.payment, dataIndex: "payment_method" },
    {
      title: ru.tariffs.columns.price,
      render: (_, subscription) =>
        subscription.price_amount ? `${subscription.price_amount} ${subscription.currency}` : "—",
    },
    {
      title: ru.tariffs.columns.duration,
      render: (_, subscription) => subscription.duration_days || "—",
    },
    {
      title: ru.tariffs.columns.traffic,
      render: (_, subscription) =>
        subscription.traffic_limit_gb ? `${subscription.traffic_limit_gb} GB` : ru.tariffs.unlimited,
    },
    { title: ru.clients.columns.expires, render: (_, subscription) => formatDate(subscription.expires_at) },
    { title: ru.clients.columns.nodes, dataIndex: "nodes_count" },
  ];
  return <Table columns={columns} dataSource={client.subscriptions} pagination={false} rowKey="id" />;
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}
