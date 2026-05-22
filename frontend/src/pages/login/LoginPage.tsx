import { LockOutlined, MailOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../../api/auth";
import { authStore } from "../../store/auth";

type LoginForm = {
  email: string;
  password: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(values: LoginForm) {
    setLoading(true);
    setError(null);
    try {
      authStore.setTokens(await login(values.email, values.password));
      navigate("/");
    } catch {
      setError("Access denied. Check the admin credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <Typography.Title>VPNBotX Admin</Typography.Title>
        <Typography.Paragraph>
          Sign in with the owner or staff account created by the deployment CLI.
        </Typography.Paragraph>
        {error ? <Alert message={error} showIcon type="error" /> : null}
        <Form<LoginForm> layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item label="Email" name="email" rules={[{ required: true }, { type: "email" }]}>
            <Input prefix={<MailOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button block htmlType="submit" loading={loading} size="large" type="primary">
            Sign in
          </Button>
        </Form>
      </section>
    </main>
  );
}

