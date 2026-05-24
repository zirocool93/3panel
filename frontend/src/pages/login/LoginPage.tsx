import { LockOutlined, MailOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography } from "antd";
import axios from "axios";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../../api/auth";
import { ru } from "../../i18n/ru";
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
    } catch (caughtError) {
      if (axios.isAxiosError(caughtError)) {
        const status = caughtError.response?.status;
        const detail = caughtError.response?.data?.detail;
        if (status === 401) {
          setError(ru.auth.invalidCredentials);
        } else if (status) {
          setError(`${ru.auth.apiError} ${status}: ${detail ?? ru.auth.apiFallback}`);
        } else {
          setError(ru.auth.apiUnavailable);
        }
      } else {
        setError(ru.auth.unknownError);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <Typography.Title>{ru.auth.title}</Typography.Title>
        <Typography.Paragraph>{ru.auth.subtitle}</Typography.Paragraph>
        {error ? <Alert message={error} showIcon type="error" /> : null}
        <Form<LoginForm> layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item label={ru.auth.email} name="email" rules={[{ required: true }, { type: "email" }]}>
            <Input prefix={<MailOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item label={ru.auth.password} name="password" rules={[{ required: true }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button block htmlType="submit" loading={loading} size="large" type="primary">
            {ru.auth.signIn}
          </Button>
        </Form>
      </section>
    </main>
  );
}
