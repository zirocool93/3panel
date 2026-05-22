import { ApiOutlined, DatabaseOutlined, MessageOutlined } from "@ant-design/icons";
import { Col, Row, Statistic, Typography } from "antd";

export function DashboardPage() {
  return (
    <section className="dashboard-page">
      <Typography.Title level={2}>Dashboard</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic prefix={<ApiOutlined />} title="API" value="Ready" />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic prefix={<DatabaseOutlined />} title="Database" value="Migrated" />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic prefix={<MessageOutlined />} title="Bot" value="Bootstrapped" />
          </div>
        </Col>
      </Row>
    </section>
  );
}

