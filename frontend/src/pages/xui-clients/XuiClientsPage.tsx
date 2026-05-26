import { ReloadOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Col,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
  type TableColumnsType,
} from "antd";
import axios from "axios";
import { useEffect, useMemo, useState } from "react";

import {
  listServers,
  listXuiClients,
  type ServerRead,
  type XuiClientRead,
} from "../../api/servers";
import { ru } from "../../i18n/ru";

export function XuiClientsPage() {
  const [servers, setServers] = useState<ServerRead[]>([]);
  const [selectedServerId, setSelectedServerId] = useState<number | null>(null);
  const [clients, setClients] = useState<XuiClientRead[]>([]);
  const [serversLoading, setServersLoading] = useState(false);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();

  async function refreshServers() {
    setServersLoading(true);
    try {
      const serverList = await listServers();
      setServers(serverList);
      setSelectedServerId((current) => current ?? serverList[0]?.id ?? null);
    } catch {
      setError(ru.xui.loadError);
    } finally {
      setServersLoading(false);
    }
  }

  async function refreshClients(serverId = selectedServerId) {
    if (!serverId) {
      setClients([]);
      return;
    }
    setClientsLoading(true);
    try {
      setClients(await listXuiClients(serverId));
      setError(null);
    } catch (caughtError) {
      const detail = axios.isAxiosError(caughtError) ? caughtError.response?.data?.detail : null;
      setError(detail || ru.xuiClients.loadError);
      messageApi.error(detail || ru.xuiClients.loadError);
    } finally {
      setClientsLoading(false);
    }
  }

  useEffect(() => {
    void refreshServers();
  }, []);

  useEffect(() => {
    if (selectedServerId) {
      void refreshClients(selectedServerId);
    }
  }, [selectedServerId]);

  const activeClients = useMemo(
    () => clients.filter((client) => client.enable !== false).length,
    [clients],
  );
  const totalTraffic = useMemo(
    () => clients.reduce((sum, client) => sum + client.up + client.down, 0),
    [clients],
  );

  const columns: TableColumnsType<XuiClientRead> = [
    {
      title: ru.xuiClients.columns.email,
      dataIndex: "email",
      fixed: "left",
      render: (email: string) => <Typography.Text strong>{email}</Typography.Text>,
    },
    {
      title: ru.xuiClients.columns.inbound,
      render: (_, client) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{client.inbound_remark || `#${client.inbound_id}`}</Typography.Text>
          <Typography.Text type="secondary">ID {client.inbound_id}</Typography.Text>
        </Space>
      ),
    },
    { title: ru.xuiClients.columns.protocol, dataIndex: "protocol", width: 120 },
    {
      title: ru.xuiClients.columns.status,
      dataIndex: "enable",
      width: 120,
      render: (enabled: boolean | null) => (
        <Tag color={enabled === false ? "default" : "green"}>
          {enabled === false ? ru.common.disabled : ru.common.enabled}
        </Tag>
      ),
    },
    {
      title: ru.xuiClients.columns.total,
      width: 130,
      render: (_, client) => formatBytes(client.up + client.down),
    },
    {
      title: ru.xuiClients.columns.upload,
      dataIndex: "up",
      width: 130,
      render: formatBytes,
    },
    {
      title: ru.xuiClients.columns.download,
      dataIndex: "down",
      width: 130,
      render: formatBytes,
    },
    {
      title: ru.xuiClients.columns.limit,
      dataIndex: "traffic_limit",
      width: 130,
      render: (value: number) => (value > 0 ? formatBytes(value) : ru.xuiClients.noLimit),
    },
    {
      title: ru.xuiClients.columns.expires,
      dataIndex: "expiry_time",
      width: 170,
      render: formatExpiry,
    },
    {
      title: ru.xuiClients.columns.uuid,
      dataIndex: "client_uuid",
      ellipsis: true,
      width: 220,
      render: (value: string | null) => value || ru.xuiClients.unknown,
    },
    {
      title: ru.xuiClients.columns.subId,
      dataIndex: "sub_id",
      ellipsis: true,
      width: 160,
      render: (value: string | null) => value || ru.xuiClients.unknown,
    },
  ];

  return (
    <section className="settings-page">
      {messageContext}
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>{ru.xuiClients.title}</Typography.Title>
          <Typography.Paragraph>{ru.xuiClients.description}</Typography.Paragraph>
        </div>
        <Button
          icon={<ReloadOutlined />}
          loading={clientsLoading}
          onClick={() => void refreshClients()}
        >
          {ru.xuiClients.load}
        </Button>
      </div>

      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <section className="settings-section">
        <Space className="xui-client-toolbar" wrap>
          <Typography.Text strong>{ru.xuiClients.server}</Typography.Text>
          <Select
            loading={serversLoading}
            onChange={(value) => setSelectedServerId(value)}
            options={servers.map((server) => ({
              label: `${server.name} (${server.country})`,
              value: server.id,
            }))}
            placeholder={ru.xuiClients.selectServer}
            value={selectedServerId ?? undefined}
            style={{ minWidth: 280 }}
          />
          <Button loading={serversLoading} onClick={() => void refreshServers()}>
            {ru.xui.reload}
          </Button>
        </Space>
        {servers.length === 0 && !serversLoading ? (
          <Alert message={ru.xuiClients.emptyServers} showIcon type="info" />
        ) : null}
      </section>

      <Row gutter={[16, 16]} className="xui-client-stats">
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic title={ru.xuiClients.totalClients} value={clients.length} />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic title={ru.xuiClients.activeClients} value={activeClients} />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic title={ru.xuiClients.totalTraffic} value={formatBytes(totalTraffic)} />
          </div>
        </Col>
      </Row>

      <section className="settings-section">
        <Table
          columns={columns}
          dataSource={clients}
          loading={clientsLoading}
          locale={{ emptyText: ru.xuiClients.emptyClients }}
          pagination={{ pageSize: 20 }}
          rowKey={(client) => `${client.inbound_id}:${client.email}`}
          scroll={{ x: 1500 }}
        />
      </section>
    </section>
  );
}

function formatBytes(value: number): string {
  if (!value) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const amount = value / 1024 ** index;
  return `${amount.toFixed(amount >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatExpiry(value: number | null): string {
  if (!value || value <= 0) {
    return ru.xuiClients.neverExpires;
  }
  return new Date(value).toLocaleString("ru-RU");
}
