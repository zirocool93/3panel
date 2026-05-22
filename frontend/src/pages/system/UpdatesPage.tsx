import { Alert, Button, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";

import { getUpdateStatus, startUpdate, type AdminUpdateStatus } from "../../api/system";

export function UpdatesPage() {
  const [state, setState] = useState<AdminUpdateStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageApi, messageContext] = message.useMessage();

  async function refresh() {
    try {
      setState(await getUpdateStatus());
      setError(null);
    } catch {
      setError("Не удалось получить статус обновления.");
    }
  }

  async function runUpdate() {
    setLoading(true);
    try {
      setState(await startUpdate());
      messageApi.success("Обновление запущено.");
    } catch {
      setError("Запуск обновления отклонён. Проверьте права owner и настройки deployment.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="updates-page">
      {messageContext}
      <Typography.Title level={2}>Обновление</Typography.Title>
      <Typography.Paragraph>
        Админка запускает только настроенный deployment ref. Перед обновлением скрипт делает backup
        PostgreSQL, применяет миграции и перезапускает Compose.
      </Typography.Paragraph>
      {error ? <Alert message={error} showIcon type="error" /> : null}
      {state && !state.enabled ? (
        <Alert
          message="Обновление из админки выключено"
          description="Включите ADMIN_UPDATES_ENABLED=true на сервере после настройки docker.sock и deployment mounts."
          showIcon
          type="warning"
        />
      ) : null}
      <Space className="update-actions" wrap>
        <Tag color={state?.running ? "processing" : "green"}>
          {state?.running ? "Выполняется" : "Готово"}
        </Tag>
        <Tag>Ref: {state?.ref ?? "..."}</Tag>
        <Button disabled={!state?.enabled || state?.running} loading={loading} onClick={runUpdate}>
          Запустить обновление
        </Button>
        <Button onClick={() => void refresh()}>Обновить статус</Button>
      </Space>
      <div className="update-log">
        <Typography.Title level={4}>Последний лог</Typography.Title>
        <pre>{state?.log_tail.join("\n") || "Лог обновлений пока пуст."}</pre>
      </div>
    </section>
  );
}

