import { Navigate, Outlet, createBrowserRouter } from "react-router-dom";

import { AdminLayout } from "../components/AdminLayout";
import { authStore } from "../store/auth";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ClientsPage } from "../pages/clients/ClientsPage";
import { LoginPage } from "../pages/login/LoginPage";
import { TelegramSettingsPage } from "../pages/settings/TelegramSettingsPage";
import { XuiSettingsPage } from "../pages/settings/XuiSettingsPage";
import { UpdatesPage } from "../pages/system/UpdatesPage";
import { TariffsPage } from "../pages/tariffs/TariffsPage";
import { XuiClientsPage } from "../pages/xui-clients/XuiClientsPage";

function ProtectedRoute() {
  return authStore.getAccessToken() ? <Outlet /> : <Navigate replace to="/login" />;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          {
            path: "/",
            element: <DashboardPage />,
          },
          {
            path: "/clients",
            element: <ClientsPage />,
          },
          {
            path: "/system/updates",
            element: <UpdatesPage />,
          },
          {
            path: "/tariffs",
            element: <TariffsPage />,
          },
          {
            path: "/settings/xui",
            element: <XuiSettingsPage />,
          },
          {
            path: "/settings/telegram",
            element: <TelegramSettingsPage />,
          },
          {
            path: "/xui-clients",
            element: <XuiClientsPage />,
          },
        ],
      },
    ],
  },
]);
