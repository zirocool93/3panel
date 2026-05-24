import {
  ApiOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
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
  checkServer,
  createServer,
  listServerInbounds,
  listServers,
  type ServerCreate,
  type ServerInboundRead,
  type ServerRead,
} from "../../api/servers";
import { ru } from "../../i18n/ru";

type ServerForm = {
  name: string;
  country: string;
  location?: string;
  panel_url: string;
  username?: string;
  password?: string;
  api_token?: string;
  subscription_base_url?: string;
  max_users?: number;
  priority: number;
  enabled: boolean;
};

const statusColor: Record<ServerRead["last_health_status"], string> = {
  unknown: "default",
  online: "green",
  offline: "red",
  degraded: "orange",
};

export function XuiSettingsPage() {
  const [form] = Form.useForm<ServerForm>();
  const [servers, setServers] = useState<ServerRead[]>([]);
  const [inbounds, setInbounds] = useState<ServerInboundRead[]>([]);
  const [selectedServer, setSelectedServer] = useState<ServerRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [inboundsLoading, setInboundsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();

  async function refreshServers() {
    setLoading(true);
    try {
      setServers(await listServers());
      setError(null);
    } catch {
      setError(ru.xui.loadError);
    } finally {
      setLoading(false);
    }
  }

  async function submit(values: ServerForm) {
    setSaving(true);
    try {
      const payload: ServerCreate = {
        name: values.name,
        country: values.country,
        location: values.location || undefined,
        panel_url: values.panel_url,
        username: values.username || undefined,
        password: values.password || undefined,
        api_token: values.api_token || undefined,
        subscription_base_url: values.subscription_base_url || undefined,
        max_users: values.max_users,
        priority: values.priority ?? 100,
        enabled: values.enabled ?? true,
      };
      await createServer(payload);
      form.resetFields();
      form.setFieldsValue({ enabled: true, priority: 100 });
      messageApi.success(ru.xui.createSuccess);
      await refreshServers();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.xui.createError);
    } finally {
      setSaving(false);
    }
  }

  async function runCheck(server: ServerRead) {
    setCheckingId(server.id);
    try {
      const result = await checkServer(server.id);
      if (result.ok) {
        messageApi.success(result.message || ru.xui.checkSuccess);
      } else {
        messageApi.error(result.message || ru.xui.checkError);
      }
      await refreshServers();
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.xui.checkError);
    } finally {
      setCheckingId(null);
    }
  }

  async function openInbounds(server: ServerRead) {
    setSelectedServer(server);
    setInboundsLoading(true);
    try {
      setInbounds(await listServerInbounds(server.id));
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      messageApi.error(detail || ru.xui.inboundsError);
      setInbounds([]);
    } finally {
      setInboundsLoading(false);
    }
  }

  useEffect(() => {
    form.setFieldsValue({ enabled: true, priority: 100 });
    void refreshServers();
  }, [form]);

  const serverColumns: TableColumnsType<ServerRead> = [
    {
      title: ru.xui.columns.name,
      dataIndex: "name",
      render: (name: string, server) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{name}</Typography.Text>
          <Typography.Text type="secondary">{server.location || server.panel_url}</Typography.Text>
        </Space>
      ),
    },
    { title: ru.xui.columns.country, dataIndex: "country", width: 120 },
    {
      title: ru.xui.columns.users,
      width: 120,
      render: (_, server) => `${server.current_users}/${server.max_users ?? "∞"}`,
    },
    { title: ru.xui.columns.priority, dataIndex: "priority", width: 110 },
    {
      title: ru.xui.columns.status,
      dataIndex: "last_health_status",
      width: 150,
      render: (status: ServerRead["last_health_status"]) => (
        <Tag color={statusColor[status]}>{ru.xui.status[status]}</Tag>
      ),
    },
    {
      title: ru.xui.columns.enabled,
      dataIndex: "enabled",
      width: 110,
      render: (enabled: boolean) => (
        <Tag color={enabled ? "green" : "default"}>
          {enabled ? ru.common.enabled : ru.common.disabled}
        </Tag>
      ),
    },
    {
      title: ru.xui.columns.actions,
      width: 220,
      render: (_, server) => (
        <Space wrap>
          <Button
            icon={<CheckCircleOutlined />}
            loading={checkingId === server.id}
            onClick={() => void runCheck(server)}
          >
            {ru.xui.actions.check}
          </Button>
          <Button icon={<ApiOutlined />} onClick={() => void openInbounds(server)}>
            {ru.xui.actions.inbounds}
          </Button>
        </Space>
      ),
    },
  ];

  const inboundColumns: TableColumnsType<ServerInboundRead> = [
    { title: ru.xui.columns.inboundId, dataIndex: "id", width: 90 },
    { title: ru.xui.columns.remark, dataIndex: "remark" },
    { title: ru.xui.columns.protocol, dataIndex: "protocol", width: 140 },
    { title: ru.xui.columns.port, dataIndex: "port", width: 110 },
    {
      title: ru.xui.columns.enabled,
      dataIndex: "enable",
      width: 110,
      render: (enabled: boolean | null) =>
        enabled === null ? "—" : enabled ? ru.common.yes : ru.common.no,
    },
  ];

  return (
    <section className="settings-page">
      {messageContext}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>{ru.xui.title}</Typography.Title>
          <Typography.Paragraph>{ru.xui.description}</Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshServers()}>
          {ru.xui.reload}
        </Button>
      </div>

      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <section className="settings-section">
        <Typography.Title level={4}>
          <CloudServerOutlined /> {ru.xui.addServer}
        </Typography.Title>
        <Form<ServerForm>
          className="xui-form"
          form={form}
          layout="vertical"
          onFinish={submit}
          requiredMark={false}
        >
          <Form.Item
            label={ru.xui.form.name}
            name="name"
            rules={[{ required: true, message: ru.xui.form.required }]}
          >
            <Input placeholder="Germany 1" />
          </Form.Item>
          <Form.Item
            label={ru.xui.form.country}
            name="country"
            rules={[{ required: true, message: ru.xui.form.required }]}
          >
            <Input placeholder="DE" />
          </Form.Item>
          <Form.Item label={ru.xui.form.location} name="location">
            <Input placeholder="Frankfurt" />
          </Form.Item>
          <Form.Item
            label={ru.xui.form.panelUrl}
            name="panel_url"
            rules={[{ required: true, message: ru.xui.form.required }, { type: "url", message: ru.xui.form.url }]}
          >
            <Input placeholder="https://xui.example.com" />
          </Form.Item>
          <Form.Item label={ru.xui.form.username} name="username">
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item label={ru.xui.form.password} name="password">
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item label={ru.xui.form.apiToken} name="api_token">
            <Input.Password autoComplete="off" />
          </Form.Item>
          <Form.Item
            label={ru.xui.form.subscriptionBaseUrl}
            name="subscription_base_url"
            rules={[{ type: "url", message: ru.xui.form.url }]}
          >
            <Input placeholder="https://sub.example.com" />
          </Form.Item>
          <Form.Item label={ru.xui.form.maxUsers} name="max_users">
            <InputNumber min={1} />
          </Form.Item>
          <Form.Item label={ru.xui.form.priority} name="priority">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item label={ru.xui.form.enabled} name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item className="form-actions">
            <Button htmlType="submit" loading={saving} type="primary">
              {ru.common.save}
            </Button>
          </Form.Item>
        </Form>
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>{ru.xui.serverList}</Typography.Title>
        <Table
          columns={serverColumns}
          dataSource={servers}
          loading={loading}
          locale={{ emptyText: ru.xui.emptyServers }}
          pagination={{ pageSize: 10 }}
          rowKey="id"
          scroll={{ x: 980 }}
        />
      </section>

      {selectedServer ? (
        <section className="settings-section">
          <Typography.Title level={4}>
            {ru.xui.inboundList}: {selectedServer.name}
          </Typography.Title>
          <Table
            columns={inboundColumns}
            dataSource={inbounds}
            loading={inboundsLoading}
            pagination={false}
            rowKey="id"
          />
        </section>
      ) : null}
    </section>
  );
}
