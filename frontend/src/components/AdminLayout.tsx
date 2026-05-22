import { DashboardOutlined, LogoutOutlined } from "@ant-design/icons";
import { Button, Layout, Menu, Tag, Typography } from "antd";
import { Outlet, useNavigate } from "react-router-dom";

import { authStore } from "../store/auth";

const { Header, Sider, Content } = Layout;

export function AdminLayout() {
  const navigate = useNavigate();

  return (
    <Layout className="admin-shell">
      <Sider breakpoint="lg" collapsedWidth="0" className="side-panel" width={224}>
        <div className="brand-block">
          <Typography.Title level={4}>VPNBotX</Typography.Title>
          <Tag color="green">Stage 1</Tag>
        </div>
        <Menu
          className="nav-menu"
          defaultSelectedKeys={["dashboard"]}
          items={[{ key: "dashboard", icon: <DashboardOutlined />, label: "Dashboard" }]}
        />
      </Sider>
      <Layout>
        <Header className="top-bar">
          <Typography.Text strong>Administration</Typography.Text>
          <Button
            icon={<LogoutOutlined />}
            onClick={() => {
              authStore.clear();
              navigate("/login");
            }}
          >
            Sign out
          </Button>
        </Header>
        <Content className="workspace">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

