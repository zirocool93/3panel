import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Table, Typography, type TableColumnsType } from "antd";
import { useEffect, useState } from "react";

import { listTransactions, type ClientTransactionRead } from "../../api/clients";

export function TransactionsPage() {
  const [transactions, setTransactions] = useState<ClientTransactionRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshTransactions() {
    setLoading(true);
    try {
      setTransactions(await listTransactions());
      setError(null);
    } catch {
      setError("Не удалось загрузить транзакции.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshTransactions();
  }, []);

  const columns: TableColumnsType<ClientTransactionRead> = [
    {
      title: "Клиент",
      render: (_, transaction) => transaction.user_display_name || `#${transaction.user_id}`,
    },
    { title: "Тип", dataIndex: "type" },
    { title: "Способ оплаты", dataIndex: "payment_method" },
    {
      title: "Сумма",
      render: (_, transaction) => `${transaction.amount} ${transaction.currency}`,
    },
    { title: "Баланс до", dataIndex: "balance_before" },
    { title: "Баланс после", dataIndex: "balance_after" },
    { title: "Подписка", dataIndex: "subscription_id" },
    { title: "Комментарий", dataIndex: "description" },
    {
      title: "Дата",
      render: (_, transaction) => new Date(transaction.created_at).toLocaleString("ru-RU"),
    },
  ];

  return (
    <section className="settings-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>Транзакции</Typography.Title>
          <Typography.Paragraph>
            Общая история оплат, ручных начислений и списаний по всем клиентам.
          </Typography.Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refreshTransactions()}>
          Обновить
        </Button>
      </div>
      {error ? <Alert className="page-alert" message={error} showIcon type="error" /> : null}
      <section className="settings-section">
        <Table
          columns={columns}
          dataSource={transactions}
          loading={loading}
          locale={{ emptyText: "Транзакций пока нет." }}
          pagination={{ pageSize: 20 }}
          rowKey="id"
          scroll={{ x: 1300 }}
        />
      </section>
    </section>
  );
}
