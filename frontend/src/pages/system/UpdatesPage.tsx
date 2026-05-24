import { Alert, Button, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";

import { getUpdateStatus, startUpdate, type AdminUpdateStatus } from "../../api/system";
import { ru } from "../../i18n/ru";

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
      setError(ru.updates.statusLoadError);
    }
  }

  async function runUpdate() {
    setLoading(true);
    try {
      setState(await startUpdate());
      messageApi.success(ru.updates.started);
    } catch {
      setError(ru.updates.startRejected);
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
      <Typography.Title level={2}>{ru.updates.title}</Typography.Title>
      <Typography.Paragraph>{ru.updates.description}</Typography.Paragraph>
      {error ? <Alert message={error} showIcon type="error" /> : null}
      {state && !state.enabled ? (
        <Alert
          message={ru.updates.disabledTitle}
          description={ru.updates.disabledDescription}
          showIcon
          type="warning"
        />
      ) : null}
      <Space className="update-actions" wrap>
        <Tag color={state?.running ? "processing" : "green"}>
          {state?.running ? ru.common.running : ru.common.ready}
        </Tag>
        <Tag>Ref: {state?.ref ?? "..."}</Tag>
        <Button disabled={!state?.enabled || state?.running} loading={loading} onClick={runUpdate}>
          {ru.updates.start}
        </Button>
        <Button onClick={() => void refresh()}>{ru.common.refresh}</Button>
      </Space>
      <div className="update-log">
        <Typography.Title level={4}>{ru.updates.lastLog}</Typography.Title>
        <pre>{state?.log_tail.join("\n") || ru.updates.emptyLog}</pre>
      </div>
    </section>
  );
}
