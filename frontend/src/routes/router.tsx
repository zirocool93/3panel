import { Navigate, Outlet, createBrowserRouter } from "react-router-dom";

import { AdminLayout } from "../components/AdminLayout";
import { authStore } from "../store/auth";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { LoginPage } from "../pages/login/LoginPage";

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
        ],
      },
    ],
  },
]);

