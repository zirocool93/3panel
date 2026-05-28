import {
  BugOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  IdcardOutlined,
  LogoutOutlined,
  MoonOutlined,
  RobotOutlined,
  SunOutlined,
  SyncOutlined,
  TagsOutlined,
  TeamOutlined,
  TransactionOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Switch, Tag, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { ru } from "../i18n/ru";
import { authStore } from "../store/auth";
import { useThemeMode } from "../store/theme";

const { Header, Sider, Content } = Layout;

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleMode } = useThemeMode();
  const selectedKey = location.pathname.startsWith("/settings/xui")
    ? "xui-settings"
    : location.pathname.startsWith("/payments")
      ? "payments"
      : location.pathname.startsWith("/transactions")
        ? "transactions"
        : location.pathname.startsWith("/settings/telegram")
          ? "telegram-settings"
          : location.pathname.startsWith("/clients")
            ? "clients"
            : location.pathname.startsWith("/tariffs")
              ? "tariffs"
              : location.pathname.startsWith("/xui-clients")
                ? "xui-clients"
                : location.pathname.startsWith("/system/updates")
                  ? "updates"
                  : location.pathname.startsWith("/system/diagnostics")
                    ? "diagnostics"
                    : "dashboard";

  return (
    <Layout className="admin-shell">
      <Sider breakpoint="lg" collapsedWidth="0" className="side-panel" width={224}>
        <div className="brand-block">
          <Typography.Title level={4}>{ru.common.appName}</Typography.Title>
          <Tag color="green">Этап 2</Tag>
        </div>
        <Menu
          className="nav-menu"
          selectedKeys={[selectedKey]}
          items={[
            {
              key: "dashboard",
              icon: <DashboardOutlined />,
              label: "Панель",
              onClick: () => navigate("/"),
            },
            {
              key: "clients",
              icon: <IdcardOutlined />,
              label: "Клиенты",
              onClick: () => navigate("/clients"),
            },
            {
              key: "tariffs",
              icon: <TagsOutlined />,
              label: "Тарифы",
              onClick: () => navigate("/tariffs"),
            },
            {
              key: "payments",
              icon: <WalletOutlined />,
              label: "Оплата",
              onClick: () => navigate("/payments"),
            },
            {
              key: "transactions",
              icon: <TransactionOutlined />,
              label: "Транзакции",
              onClick: () => navigate("/transactions"),
            },
            {
              key: "xui-settings",
              icon: <CloudServerOutlined />,
              label: "3X-UI серверы",
              onClick: () => navigate("/settings/xui"),
            },
            {
              key: "telegram-settings",
              icon: <RobotOutlined />,
              label: "Telegram бот",
              onClick: () => navigate("/settings/telegram"),
            },
            {
              key: "xui-clients",
              icon: <TeamOutlined />,
              label: "Клиенты 3X-UI",
              onClick: () => navigate("/xui-clients"),
            },
            {
              key: "updates",
              icon: <SyncOutlined />,
              label: "Обновление",
              onClick: () => navigate("/system/updates"),
            },
            {
              key: "diagnostics",
              icon: <BugOutlined />,
              label: "Диагностика",
              onClick: () => navigate("/system/diagnostics"),
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="top-bar">
          <Typography.Text strong>Администрирование</Typography.Text>
          <div className="top-bar-actions">
            <Switch
              checked={mode === "dark"}
              checkedChildren={<MoonOutlined />}
              onChange={toggleMode}
              title="Переключить тему"
              unCheckedChildren={<SunOutlined />}
            />
            <Button
              icon={<LogoutOutlined />}
              onClick={() => {
                authStore.clear();
                navigate("/login");
              }}
            >
              Выйти
            </Button>
          </div>
        </Header>
        <Content className="workspace">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
