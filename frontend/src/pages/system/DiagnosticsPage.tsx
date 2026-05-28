import { BugOutlined, ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Select, Space, Table, Tag, Typography, type TableColumnsType } from "antd";
import { useEffect, useState } from "react";

import { getDiagnostics, type DiagnosticCheckRead, type DiagnosticLogRead } from "../../api/system";

const serviceOptions = [
  "backend_api",
  "nginx",
  "telegram_bot",
  "worker",
  "scheduler",
  "postgres",
  "redis",
].map((service) => ({ label: service, value: service }));

export function DiagnosticsPage() {
  const [checks, setChecks] = useState<DiagnosticCheckRead[]>([]);
  const [logs, setLogs] = useState<DiagnosticLogRead[]>([]);
  const [services, setServices] = useState<string[]>([
    "backend_api",
    "nginx",
    "telegram_bot",
    "worker",
  ]);
  const [tail, setTail] = useState(120);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const result = await getDiagnostics({ services, tail });
      setChecks(result.checks);
      setLogs(result.logs);
      setError(null);
    } catch {
      setError("Не удалось загрузить диагностику.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const checkColumns: TableColumnsType<DiagnosticCheckRead> = [
    {
      title: "Проверка",
      dataIndex: "name",
      width: 180,
    },
    {
      title: "Статус",
      width: 120,
      render: (_, check) => (
        <Tag color={check.ok ? "green" : "red"}>{check.ok ? "OK" : "Ошибка"}</Tag>
      ),
    },
    {
      title: "Сообщение",
      dataIndex: "message",
    },
    {
      title: "Как исправить",
      render: (_, check) => check.fix || "—",
    },
  ];

  return (
    <section className="updates-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>
            <BugOutlined /> Диагностика
          </Typography.Title>
          <Typography.Paragraph>
            Проверки окружения и последние строки логов контейнеров для отладки ошибок.
          </Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refresh()}>
          Обновить
        </Button>
      </div>

      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}

      <section className="settings-section">
        <Typography.Title level={4}>Проверки</Typography.Title>
        <Table
          columns={checkColumns}
          dataSource={checks}
          loading={loading}
          pagination={false}
          rowKey="name"
        />
      </section>

      <section className="settings-section">
        <Typography.Title level={4}>Логи</Typography.Title>
        <Space className="diagnostics-controls" wrap>
          <Select
            mode="multiple"
            onChange={setServices}
            options={serviceOptions}
            value={services}
          />
          <Select
            onChange={setTail}
            options={[
              { label: "50 строк", value: 50 },
              { label: "120 строк", value: 120 },
              { label: "250 строк", value: 250 },
              { label: "500 строк", value: 500 },
            ]}
            value={tail}
          />
        </Space>
        <Space className="grid-wide" direction="vertical" size="middle">
          {logs.map((log) => (
            <section className="diagnostic-log" key={log.service}>
              <Typography.Title level={5}>{log.service}</Typography.Title>
              {log.error ? <Alert message={log.error} showIcon type="warning" /> : null}
              <pre>{log.lines.join("\n") || "Лог пуст."}</pre>
            </section>
          ))}
        </Space>
      </section>
    </section>
  );
}
