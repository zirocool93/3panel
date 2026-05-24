import { DashboardOutlined, LogoutOutlined, SyncOutlined } from "@ant-design/icons";
import { Button, Layout, Menu, Tag, Typography } from "antd";
import { Outlet, useNavigate } from "react-router-dom";

import { ru } from "../i18n/ru";
import { authStore } from "../store/auth";

const { Header, Sider, Content } = Layout;

export function AdminLayout() {
  const navigate = useNavigate();

  return (
    <Layout className="admin-shell">
      <Sider breakpoint="lg" collapsedWidth="0" className="side-panel" width={224}>
        <div className="brand-block">
          <Typography.Title level={4}>{ru.common.appName}</Typography.Title>
          <Tag color="green">{ru.common.stage}</Tag>
        </div>
        <Menu
          className="nav-menu"
          defaultSelectedKeys={["dashboard"]}
          items={[
            {
              key: "dashboard",
              icon: <DashboardOutlined />,
              label: ru.navigation.dashboard,
              onClick: () => navigate("/"),
            },
            {
              key: "updates",
              icon: <SyncOutlined />,
              label: ru.navigation.updates,
              onClick: () => navigate("/system/updates"),
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="top-bar">
          <Typography.Text strong>{ru.navigation.administration}</Typography.Text>
          <Button
            icon={<LogoutOutlined />}
            onClick={() => {
              authStore.clear();
              navigate("/login");
            }}
          >
            {ru.common.signOut}
          </Button>
        </Header>
        <Content className="workspace">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
