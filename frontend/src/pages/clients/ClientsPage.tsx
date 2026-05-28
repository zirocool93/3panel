import {
  DeleteOutlined,
  EditOutlined,
  IdcardOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Popconfirm,
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
  adjustClientBalance,
  createClient,
  createClientSubscription,
  deleteClient,
  deleteClientSubscription,
  listClients,
  provisionClientSubscription,
  updateClient,
  updateClientSubscription,
  type ClientPayload,
  type ClientRead,
  type ClientSubscriptionPayload,
  type ClientSubscriptionRead,
  type ClientSubscriptionNodeRead,
  type ClientTransactionRead,
} from "../../api/clients";
import { listPaymentMethods, type PaymentMethodRead } from "../../api/payments";
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

type BalanceForm = {
  client_id: number;
  amount: number;
  currency: string;
  description?: string;
};

export function ClientsPage() {
  const [clientForm] = Form.useForm<ClientForm>();
  const [subscriptionForm] = Form.useForm<SubscriptionForm>();
  const [balanceForm] = Form.useForm<BalanceForm>();
  const [clients, setClients] = useState<ClientRead[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodRead[]>([]);
  const [tariffs, setTariffs] = useState<TariffRead[]>([]);
  const [editingClient, setEditingClient] = useState<ClientRead | null>(null);
  const [editingSubscription, setEditingSubscription] = useState<{
    clientId: number;
    subscription: ClientSubscriptionRead;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingClient, setSavingClient] = useState(false);
  const [deletingClientId, setDeletingClientId] = useState<number | null>(null);
  const [deletingSubscriptionId, setDeletingSubscriptionId] = useState<number | null>(null);
  const [provisioningSubscriptionId, setProvisioningSubscriptionId] = useState<number | null>(null);
  const [savingSubscription, setSavingSubscription] = useState(false);
  const [savingBalance, setSavingBalance] = useState(false);
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

  async function refreshPaymentMethods() {
    setPaymentMethods(await listPaymentMethods());
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
      if (editingSubscription) {
        await updateClientSubscription(
          editingSubscription.clientId,
          editingSubscription.subscription.id,
          payload,
        );
        messageApi.success("Подписка обновлена.");
      } else {
        await createClientSubscription(values.client_id, payload);
        messageApi.success(ru.clients.subscriptionSuccess);
      }
      resetSubscriptionForm();
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(
        detail || (editingSubscription ? "Не удалось обновить подписку." : ru.clients.subscriptionError),
      );
    } finally {
      setSavingSubscription(false);
    }
  }

  async function submitBalance(values: BalanceForm) {
    setSavingBalance(true);
    try {
      await adjustClientBalance(values.client_id, {
        amount: String(values.amount),
        currency: values.currency || "RUB",
        description: values.description || undefined,
      });
      balanceForm.resetFields();
      balanceForm.setFieldsValue({ currency: "RUB" });
      messageApi.success("Баланс изменён.");
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || "Не удалось изменить баланс.");
    } finally {
      setSavingBalance(false);
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

  function startEditSubscription(client: ClientRead, subscription: ClientSubscriptionRead) {
    setEditingSubscription({ clientId: client.id, subscription });
    subscriptionForm.setFieldsValue({
      client_id: client.id,
      tariff_id: subscription.tariff_id || undefined,
      payment_method: subscription.payment_method || "manual",
      price_amount: subscription.price_amount ? Number(subscription.price_amount) : undefined,
      currency: subscription.currency || undefined,
      duration_days: subscription.duration_days || undefined,
      traffic_limit_gb: subscription.traffic_limit_gb || undefined,
      device_limit: subscription.device_limit || undefined,
      admin_comment: subscription.admin_comment || undefined,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetSubscriptionForm() {
    setEditingSubscription(null);
    subscriptionForm.resetFields();
    subscriptionForm.setFieldsValue({ payment_method: "manual" });
  }

  async function removeClient(client: ClientRead) {
    setDeletingClientId(client.id);
    try {
      await deleteClient(client.id);
      if (editingClient?.id === client.id) {
        resetClientForm();
      }
      messageApi.success("Клиент удалён.");
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || "Не удалось удалить клиента.");
    } finally {
      setDeletingClientId(null);
    }
  }

  async function removeSubscription(client: ClientRead, subscription: ClientSubscriptionRead) {
    setDeletingSubscriptionId(subscription.id);
    try {
      await deleteClientSubscription(client.id, subscription.id);
      if (editingSubscription?.subscription.id === subscription.id) {
        resetSubscriptionForm();
      }
      messageApi.success("Подписка удалена.");
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || "Не удалось удалить подписку.");
    } finally {
      setDeletingSubscriptionId(null);
    }
  }

  async function retryProvision(client: ClientRead, subscription: ClientSubscriptionRead) {
    setProvisioningSubscriptionId(subscription.id);
    try {
      await provisionClientSubscription(client.id, subscription.id);
      messageApi.success("Создание клиентов в 3X-UI запущено повторно.");
      await refreshClients();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || "Не удалось создать клиентов в 3X-UI.");
    } finally {
      setProvisioningSubscriptionId(null);
    }
  }

  useEffect(() => {
    clientForm.setFieldsValue({ is_blocked: false });
    subscriptionForm.setFieldsValue({ payment_method: "manual" });
    balanceForm.setFieldsValue({ currency: "RUB" });
    void refreshClients();
    void refreshTariffs();
    void refreshPaymentMethods();
  }, [balanceForm, clientForm, subscriptionForm]);

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
      width: 190,
      render: (_, client) => (
        <Space wrap>
          <Button icon={<EditOutlined />} onClick={() => startEdit(client)}>
            {ru.tariffs.actions.edit}
          </Button>
          <Popconfirm
            cancelText="Отмена"
            okButtonProps={{ danger: true, loading: deletingClientId === client.id }}
            okText="Удалить"
            onConfirm={() => void removeClient(client)}
            title="Удалить клиента и его локальные подписки?"
          >
            <Button danger icon={<DeleteOutlined />} loading={deletingClientId === client.id} />
          </Popconfirm>
        </Space>
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
        <Typography.Title level={4}>Изменить баланс</Typography.Title>
        <Alert className="page-alert" message="Для списания укажите отрицательную сумму." showIcon type="info" />
        <Form<BalanceForm>
          className="xui-form"
          form={balanceForm}
          layout="vertical"
          onFinish={submitBalance}
          requiredMark={false}
        >
          <Form.Item
            label="Клиент"
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
            label="Сумма"
            name="amount"
            rules={[{ required: true, message: ru.clients.form.required }]}
          >
            <InputNumber precision={2} />
          </Form.Item>
          <Form.Item label="Валюта" name="currency">
            <Input maxLength={16} />
          </Form.Item>
          <Form.Item className="grid-wide" label="Комментарий" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item className="form-actions">
            <Button htmlType="submit" loading={savingBalance} type="primary">
              Сохранить операцию
            </Button>
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
              disabled={Boolean(editingSubscription)}
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
              options={paymentMethods
                .filter((method) => method.enabled)
                .map((method) => ({ label: method.label, value: method.code }))}
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
            <Space wrap>
              <Button htmlType="submit" loading={savingSubscription} type="primary">
                {editingSubscription ? "Сохранить подписку" : ru.clients.subscription}
              </Button>
              {editingSubscription ? (
                <Button onClick={resetSubscriptionForm}>{ru.common.cancel}</Button>
              ) : null}
            </Space>
          </Form.Item>
        </Form>
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>{ru.clients.list}</Typography.Title>
        <Table
          columns={columns}
          dataSource={clients}
          expandable={{
            expandedRowRender: (client) =>
              renderClientDetails(
                client,
                startEditSubscription,
                removeSubscription,
                retryProvision,
                deletingSubscriptionId,
                provisioningSubscriptionId,
              ),
          }}
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

function renderClientDetails(
  client: ClientRead,
  onEditSubscription: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  onDeleteSubscription: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  onRetryProvision: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  deletingSubscriptionId: number | null,
  provisioningSubscriptionId: number | null,
) {
  return (
    <Space className="grid-wide" direction="vertical" size="large">
      {renderSubscriptions(
        client,
        onEditSubscription,
        onDeleteSubscription,
        onRetryProvision,
        deletingSubscriptionId,
        provisioningSubscriptionId,
      )}
      {renderTransactions(client)}
    </Space>
  );
}

function renderSubscriptions(
  client: ClientRead,
  onEditSubscription: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  onDeleteSubscription: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  onRetryProvision: (client: ClientRead, subscription: ClientSubscriptionRead) => void,
  deletingSubscriptionId: number | null,
  provisioningSubscriptionId: number | null,
) {
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
    {
      title: ru.clients.columns.actions,
      width: 260,
      render: (_, subscription) => (
        <Space wrap>
          <Button size="small" icon={<EditOutlined />} onClick={() => onEditSubscription(client, subscription)}>
            {ru.tariffs.actions.edit}
          </Button>
          <Button
            icon={<ReloadOutlined />}
            loading={provisioningSubscriptionId === subscription.id}
            onClick={() => onRetryProvision(client, subscription)}
            size="small"
          >
            Повторить 3X-UI
          </Button>
          <Popconfirm
            cancelText="Отмена"
            okButtonProps={{ danger: true, loading: deletingSubscriptionId === subscription.id }}
            okText="Удалить"
            onConfirm={() => onDeleteSubscription(client, subscription)}
            title="Удалить подписку и клиентов из 3X-UI?"
          >
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deletingSubscriptionId === subscription.id}
              size="small"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  return (
    <Table
      columns={columns}
      dataSource={client.subscriptions}
      expandable={{ expandedRowRender: renderSubscriptionNodes }}
      pagination={false}
      rowKey="id"
    />
  );
}

function linksForSubscription(item: {
  subscription_links?: string[];
  subscription_url: string | null;
}) {
  if (item.subscription_links?.length) {
    return item.subscription_links;
  }
  return item.subscription_url ? [item.subscription_url] : [];
}

function renderSubscriptionLinks(item: {
  subscription_links?: string[];
  subscription_url: string | null;
}) {
  const links = linksForSubscription(item);
  if (!links.length) {
    return "-";
  }
  return (
    <Space direction="vertical" size={2}>
      {links.map((link) => (
        <Typography.Link copyable href={link} key={link} target="_blank">
          {link}
        </Typography.Link>
      ))}
    </Space>
  );
}

function renderSubscriptionNodes(subscription: ClientSubscriptionRead) {
  const columns: TableColumnsType<ClientSubscriptionNodeRead> = [
    { title: "Сервер", dataIndex: "server_id" },
    { title: "Inbound", dataIndex: "inbound_id" },
    { title: "Протокол", dataIndex: "protocol" },
    { title: "Email", dataIndex: "email" },
    {
      title: "Статус",
      render: (_, node) => (
        <Tag color={node.status === "active" ? "green" : node.status === "failed" ? "red" : "default"}>
          {node.status}
        </Tag>
      ),
    },
    {
      title: "Ошибка",
      render: (_, node) =>
        node.error ? <Typography.Text type="danger">{node.error}</Typography.Text> : "—",
    },
    {
      title: "Ссылка",
      render: (_, node) => renderSubscriptionLinks(node),
    },
    {
      title: "QR",
      width: 120,
      render: (_, node) =>
        node.subscription_qr ? (
          <img alt="QR подписки" className="subscription-qr" src={node.subscription_qr} />
        ) : (
          "—"
        ),
    },
  ];
  return (
    <Space direction="vertical" size="middle">
      {linksForSubscription(subscription).length ? (
        <Space align="start" wrap>
          {renderSubscriptionLinks(subscription)}
          {subscription.subscription_qr ? (
            <img alt="QR подписки" className="subscription-qr" src={subscription.subscription_qr} />
          ) : null}
        </Space>
      ) : null}
      <Table
        columns={columns}
        dataSource={subscription.nodes}
        locale={{ emptyText: "Ноды 3X-UI пока не созданы." }}
        pagination={false}
        rowKey="id"
      />
    </Space>
  );
}

function renderTransactions(client: ClientRead) {
  if (!client.transactions.length) {
    return null;
  }
  const columns: TableColumnsType<ClientTransactionRead> = [
    { title: "Тип", dataIndex: "type" },
    { title: "Оплата", dataIndex: "payment_method" },
    {
      title: "Сумма",
      render: (_, transaction) => `${transaction.amount} ${transaction.currency}`,
    },
    { title: "До", dataIndex: "balance_before" },
    { title: "После", dataIndex: "balance_after" },
    { title: "Комментарий", dataIndex: "description" },
    { title: "Дата", render: (_, transaction) => formatDate(transaction.created_at) },
  ];
  return (
    <section>
      <Typography.Title level={5}>История оплат и списаний</Typography.Title>
      <Table columns={columns} dataSource={client.transactions} pagination={false} rowKey="id" />
    </section>
  );
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("ru-RU") : "—";
}
