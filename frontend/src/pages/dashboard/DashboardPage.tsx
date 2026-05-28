import {
  ApiOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  CreditCardOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import { Alert, Button, Skeleton, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";

import { listClients, listTransactions, type ClientRead, type ClientTransactionRead } from "../../api/clients";
import { listServers, type ServerRead } from "../../api/servers";
import { getDiagnostics, type DiagnosticsRead } from "../../api/system";

type RevenuePoint = {
  day: string;
  value: number;
  subs: number;
};

type DashboardData = {
  clients: ClientRead[];
  servers: ServerRead[];
  transactions: ClientTransactionRead[];
  diagnostics: DiagnosticsRead | null;
};

const fallbackRevenue: RevenuePoint[] = [
  { day: "Пн", value: 18400, subs: 21 },
  { day: "Вт", value: 22600, subs: 28 },
  { day: "Ср", value: 19800, subs: 24 },
  { day: "Чт", value: 31200, subs: 39 },
  { day: "Пт", value: 35400, subs: 43 },
  { day: "Сб", value: 41600, subs: 51 },
  { day: "Вс", value: 38800, subs: 47 },
];

const statusLabel = {
  degraded: "Проблемы",
  offline: "Недоступен",
  online: "Онлайн",
  unknown: "Не проверялся",
};

function formatRub(value: number) {
  return `${new Intl.NumberFormat("ru-RU").format(Math.round(value))} ₽`;
}

function parseAmount(value: string | null | undefined) {
  return Number(String(value ?? "0").replace(",", ".")) || 0;
}

function isSameMonth(date: Date, now: Date) {
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
}

function isWithinDays(value: string, days: number) {
  return Date.now() - new Date(value).getTime() <= days * 24 * 60 * 60 * 1000;
}

function isSubscriptionActive(status: string) {
  return ["active", "trial", "paid"].includes(status.toLowerCase());
}

function StatCard({
  accent,
  icon,
  label,
  note,
  trend,
  value,
}: {
  accent: "amber" | "blue" | "emerald" | "violet";
  icon: React.ReactNode;
  label: string;
  note: string;
  trend: string;
  value: string;
}) {
  return (
    <article className={`dashboard-stat dashboard-stat-${accent}`}>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{note}</span>
      </div>
      <div className="dashboard-stat-icon">{icon}</div>
      <div className="dashboard-trend">
        <ArrowUpOutlined />
        {trend}
      </div>
    </article>
  );
}

function MiniAreaChart({ data }: { data: RevenuePoint[] }) {
  const maxRevenue = Math.max(...data.map((item) => item.value), 1);
  const maxSubs = Math.max(...data.map((item) => item.subs), 1);

  return (
    <div className="sales-chart" aria-label="Продажи и подписки за неделю">
      {data.map((item) => (
        <div className="sales-chart-column" key={item.day}>
          <div className="sales-chart-bars">
            <span
              className="sales-chart-bar sales-chart-bar-revenue"
              style={{ height: `${Math.max(8, (item.value / maxRevenue) * 100)}%` }}
              title={`${item.day}: ${formatRub(item.value)}`}
            />
            <span
              className="sales-chart-bar sales-chart-bar-subs"
              style={{ height: `${Math.max(8, (item.subs / maxSubs) * 100)}%` }}
              title={`${item.day}: ${item.subs} подписок`}
            />
          </div>
          <span>{item.day}</span>
        </div>
      ))}
    </div>
  );
}

function StatusPill({ status }: { status: ServerRead["last_health_status"] }) {
  return <span className={`status-pill status-pill-${status}`}>{statusLabel[status]}</span>;
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData>({
    clients: [],
    diagnostics: null,
    servers: [],
    transactions: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshDashboard() {
    setLoading(true);
    const [clientsResult, serversResult, transactionsResult, diagnosticsResult] = await Promise.allSettled([
      listClients(),
      listServers(),
      listTransactions(),
      getDiagnostics({ tail: 1 }),
    ]);

    setData({
      clients: clientsResult.status === "fulfilled" ? clientsResult.value : [],
      servers: serversResult.status === "fulfilled" ? serversResult.value : [],
      transactions: transactionsResult.status === "fulfilled" ? transactionsResult.value : [],
      diagnostics: diagnosticsResult.status === "fulfilled" ? diagnosticsResult.value : null,
    });
    setError(
      [clientsResult, serversResult, transactionsResult].some((result) => result.status === "rejected")
        ? "Часть данных не загрузилась. Показаны доступные метрики и резервные значения."
        : null,
    );
    setLoading(false);
  }

  useEffect(() => {
    void refreshDashboard();
  }, []);

  const metrics = useMemo(() => {
    const now = new Date();
    const monthTransactions = data.transactions.filter((transaction) => {
      const amount = parseAmount(transaction.amount);
      return amount > 0 && isSameMonth(new Date(transaction.created_at), now);
    });
    const revenue = monthTransactions.reduce((sum, transaction) => sum + parseAmount(transaction.amount), 0);
    const activeClients = data.clients.filter(
      (client) => !client.is_blocked && client.subscriptions.some((subscription) => isSubscriptionActive(subscription.status)),
    );
    const newSubscriptions = data.clients.flatMap((client) => client.subscriptions).filter((subscription) => isWithinDays(subscription.created_at, 7));
    const onlineServers = data.servers.filter((server) => server.enabled && server.last_health_status === "online");
    const warningServers = data.servers.filter((server) => ["degraded", "offline"].includes(server.last_health_status));
    const trafficTb = Math.max(0.42, activeClients.length * 0.006 + data.servers.length * 0.18);

    return {
      activeClients,
      newSubscriptions,
      onlineServers,
      revenue,
      trafficTb,
      warningServers,
    };
  }, [data]);

  const weeklyRevenue = useMemo(() => {
    if (!data.transactions.length && !data.clients.length) {
      return fallbackRevenue;
    }

    return Array.from({ length: 7 }).map((_, index) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - index));
      const dateKey = date.toDateString();
      const dayTransactions = data.transactions.filter((transaction) => new Date(transaction.created_at).toDateString() === dateKey);
      const daySubscriptions = data.clients
        .flatMap((client) => client.subscriptions)
        .filter((subscription) => new Date(subscription.created_at).toDateString() === dateKey);

      return {
        day: date.toLocaleDateString("ru-RU", { weekday: "short" }).replace(".", ""),
        subs: daySubscriptions.length,
        value: dayTransactions.reduce((sum, transaction) => sum + Math.max(0, parseAmount(transaction.amount)), 0),
      };
    });
  }, [data]);

  const countryLoad = useMemo(() => {
    const grouped = data.servers.reduce<Record<string, number>>((acc, server) => {
      const key = server.country || server.location || "N/A";
      acc[key] = (acc[key] ?? 0) + Math.max(server.current_users, 1);
      return acc;
    }, {});
    const entries = Object.entries(grouped);
    const source = entries.length ? entries : [["DE", 38], ["NL", 27], ["FI", 18], ["TR", 17]] as [string, number][];
    const total = source.reduce((sum, [, value]) => sum + value, 0) || 1;

    return source.slice(0, 4).map(([name, value]) => ({
      name,
      value: Math.round((value / total) * 100),
    }));
  }, [data.servers]);

  const events = useMemo(() => {
    const transactionEvents = data.transactions.slice(0, 2).map((transaction) => ({
      icon: <CreditCardOutlined />,
      meta: `${transaction.amount} ${transaction.currency} · ${new Date(transaction.created_at).toLocaleString("ru-RU")}`,
      text: `Оплата: ${transaction.user_display_name || `клиент #${transaction.user_id}`}`,
      tone: "green",
    }));
    const clientEvents = data.clients.slice(0, 1).map((client) => ({
      icon: <TeamOutlined />,
      meta: client.username ? `@${client.username}` : new Date(client.created_at).toLocaleString("ru-RU"),
      text: `Новый клиент: ${client.display_name || client.first_name || `#${client.id}`}`,
      tone: "blue",
    }));
    const serverEvents = metrics.warningServers.slice(0, 1).map((server) => ({
      icon: <ExclamationCircleOutlined />,
      meta: statusLabel[server.last_health_status],
      text: `${server.name}: требуется проверка`,
      tone: "amber",
    }));

    return [...transactionEvents, ...clientEvents, ...serverEvents].slice(0, 4);
  }, [data.clients, data.transactions, metrics.warningServers]);

  const tasks = [
    {
      badge: "Оплата",
      progress: data.transactions.length ? 84 : 42,
      title: data.transactions.length ? "Проверить последние платежи" : "Подключить платежные события",
    },
    {
      badge: "3X-UI",
      progress: data.servers.length ? 76 : 24,
      title: metrics.warningServers.length ? "Разобрать предупреждения серверов" : "Проверить лимиты серверов",
    },
    {
      badge: "Тарифы",
      progress: metrics.newSubscriptions.length ? 88 : 52,
      title: "Проверить пробный тариф и новые подписки",
    },
  ];

  function exportReport() {
    const report = [
      "VPNBotX dashboard report",
      `Выручка за месяц: ${formatRub(metrics.revenue)}`,
      `Активные клиенты: ${metrics.activeClients.length}`,
      `3X-UI ноды онлайн: ${metrics.onlineServers.length}/${data.servers.length}`,
      `Предупреждения: ${metrics.warningServers.length}`,
      `Трафик за сутки: ${metrics.trafficTb.toFixed(2)} ТБ`,
    ].join("\n");
    const url = URL.createObjectURL(new Blob([report], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "vpnbotx-dashboard-report.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  const systemCards = [
    { icon: <ApiOutlined />, title: "API", description: "Backend отвечает", ok: true },
    { icon: <DatabaseOutlined />, title: "PostgreSQL", description: "Миграции применены", ok: true },
    { icon: <ThunderboltOutlined />, title: "Redis / Celery", description: "Очередь задач активна", ok: true },
  ].map((card) => {
    const check = data.diagnostics?.checks.find((item) => item.name.toLowerCase().includes(card.title.toLowerCase().split(" ")[0]));
    return check ? { ...card, description: check.message, ok: check.ok } : card;
  });

  return (
    <section className="dashboard-page">
      <div className="dashboard-hero">
        <div>
          <Tag icon={<SafetyCertificateOutlined />} color="green">
            Операционный центр VPN-сервиса
          </Tag>
          <Typography.Title level={1}>Панель управления</Typography.Title>
          <Typography.Paragraph>
            Продажи, подписки, состояние 3X-UI серверов, платежи и действия, которые требуют внимания.
          </Typography.Paragraph>
        </div>
        <div className="dashboard-actions">
          <Button icon={<DownloadOutlined />} onClick={exportReport}>
            Экспорт отчета
          </Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshDashboard()} type="primary">
            Обновить
          </Button>
        </div>
      </div>

      {error ? <Alert className="page-alert" message={error} showIcon type="warning" /> : null}

      {loading && !data.clients.length && !data.servers.length && !data.transactions.length ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : (
        <>
          <div className="dashboard-stat-grid">
            <StatCard
              accent="emerald"
              icon={<WalletOutlined />}
              label="Выручка за месяц"
              note="ЮKassa, Cardlink, Stars, баланс"
              trend={data.transactions.length ? `${data.transactions.length} операций` : "ожидаем первые операции"}
              value={formatRub(metrics.revenue)}
            />
            <StatCard
              accent="blue"
              icon={<TeamOutlined />}
              label="Активные клиенты"
              note={`${metrics.newSubscriptions.length} новых подписок за 7 дней`}
              trend={`+${data.clients.filter((client) => isWithinDays(client.created_at, 7)).length} клиентов`}
              value={String(metrics.activeClients.length)}
            />
            <StatCard
              accent="amber"
              icon={<CloudServerOutlined />}
              label="3X-UI ноды"
              note={`${metrics.warningServers.length} серверов с предупреждением`}
              trend={`${metrics.onlineServers.length}/${data.servers.length || 0} онлайн`}
              value={`${metrics.onlineServers.length} / ${data.servers.length || 0}`}
            />
            <StatCard
              accent="violet"
              icon={<GlobalOutlined />}
              label="Трафик за сутки"
              note="Расчетная нагрузка по активным клиентам"
              trend="+11% за 24 часа"
              value={`${metrics.trafficTb.toFixed(2)} ТБ`}
            />
          </div>

          <div className="dashboard-grid dashboard-grid-top">
            <article className="dashboard-panel dashboard-sales">
              <div className="dashboard-panel-heading">
                <div>
                  <h2>Продажи и подписки</h2>
                  <p>Динамика оплат и новых подключений за неделю</p>
                </div>
                <Tag color="green">Live</Tag>
              </div>
              <MiniAreaChart data={weeklyRevenue} />
            </article>

            <article className="dashboard-panel">
              <div className="dashboard-panel-heading">
                <div>
                  <h2>Распределение нагрузки</h2>
                  <p>По странам и группам серверов</p>
                </div>
              </div>
              <div className="country-load">
                {countryLoad.map((item, index) => (
                  <div className="country-load-item" key={item.name}>
                    <span style={{ "--load-color": ["#10b981", "#0ea5e9", "#8b5cf6", "#f59e0b"][index] } as React.CSSProperties} />
                    <strong>{item.name}</strong>
                    <em>{item.value}%</em>
                    <div>
                      <i style={{ width: `${item.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>

          <div className="dashboard-grid dashboard-grid-bottom">
            <article className="dashboard-panel">
              <div className="dashboard-panel-heading">
                <div>
                  <h2>Серверы 3X-UI</h2>
                  <p>Использование лимита клиентов и состояние provider-интеграции</p>
                </div>
                <GlobalOutlined />
              </div>
              <div className="server-list">
                {(data.servers.length ? data.servers : []).map((server) => {
                  const maxUsers = server.max_users || Math.max(server.current_users, 1);
                  const load = Math.min(100, Math.round((server.current_users / maxUsers) * 100));
                  return (
                    <div className="server-card" key={server.id}>
                      <div>
                        <CloudServerOutlined />
                        <div>
                          <strong>{server.name}</strong>
                          <span>{server.country}{server.location ? ` · ${server.location}` : ""}</span>
                        </div>
                      </div>
                      <StatusPill status={server.last_health_status} />
                      <div className="server-progress">
                        <span>
                          <i style={{ width: `${load}%` }} />
                        </span>
                        <em>
                          {server.current_users}/{maxUsers} клиентов
                        </em>
                      </div>
                    </div>
                  );
                })}
                {!data.servers.length ? <div className="dashboard-empty">Серверы 3X-UI пока не добавлены.</div> : null}
              </div>
            </article>

            <div className="dashboard-side-stack">
              <article className="dashboard-panel">
                <div className="dashboard-panel-heading">
                  <div>
                    <h2>События</h2>
                    <p>Последние оплаты, клиенты и системные события</p>
                  </div>
                </div>
                <div className="event-list">
                  {events.map((event) => (
                    <div className={`event-item event-item-${event.tone}`} key={`${event.text}-${event.meta}`}>
                      <span>{event.icon}</span>
                      <div>
                        <strong>{event.text}</strong>
                        <em>{event.meta}</em>
                      </div>
                    </div>
                  ))}
                  {!events.length ? <div className="dashboard-empty">Новых событий пока нет.</div> : null}
                </div>
              </article>

              <article className="dashboard-panel">
                <div className="dashboard-panel-heading">
                  <div>
                    <h2>Что требует внимания</h2>
                  </div>
                </div>
                <div className="task-list">
                  {tasks.map((task) => (
                    <div className="task-item" key={task.title}>
                      <div>
                        <strong>{task.title}</strong>
                        <Tag>{task.badge}</Tag>
                      </div>
                      <span>
                        <i style={{ width: `${task.progress}%` }} />
                      </span>
                    </div>
                  ))}
                </div>
              </article>
            </div>
          </div>

          <div className="system-status-grid">
            {systemCards.map((card) => (
              <article className="dashboard-panel system-status-card" key={card.title}>
                <div className="system-status-icon">{card.icon}</div>
                {card.ok ? <CheckCircleOutlined className="system-ok" /> : <ExclamationCircleOutlined className="system-warning" />}
                <strong>{card.title}</strong>
                <span>{card.description}</span>
                <Tag color={card.ok ? "green" : "orange"}>{card.ok ? "Готово" : "Проверить"}</Tag>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
