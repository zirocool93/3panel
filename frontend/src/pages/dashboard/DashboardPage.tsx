import { ApiOutlined, DatabaseOutlined, MessageOutlined } from "@ant-design/icons";
import { Col, Row, Statistic, Typography } from "antd";

import { ru } from "../../i18n/ru";

export function DashboardPage() {
  return (
    <section className="dashboard-page">
      <Typography.Title level={2}>{ru.dashboard.title}</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic prefix={<ApiOutlined />} title={ru.dashboard.api} value={ru.dashboard.apiValue} />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic
              prefix={<DatabaseOutlined />}
              title={ru.dashboard.database}
              value={ru.dashboard.databaseValue}
            />
          </div>
        </Col>
        <Col xs={24} md={8}>
          <div className="metric-tile">
            <Statistic prefix={<MessageOutlined />} title={ru.dashboard.bot} value={ru.dashboard.botValue} />
          </div>
        </Col>
      </Row>
    </section>
  );
}
