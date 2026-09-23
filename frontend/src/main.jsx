import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { queryClient } from "./api";
import { AuthProvider, useAuth } from "./auth";
import AppLayout from "./components/AppLayout";
import LoginPage from "./pages/LoginPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ProductFormPage from "./pages/ProductFormPage";
import ProductListPage from "./pages/ProductListPage";
import SettingsPage from "./pages/SettingsPage";
import UserFormPage from "./pages/UserFormPage";
import UserListPage from "./pages/UserListPage";

const STAFF = ["admin", "employee"];
const ADMIN = ["admin"];

// กันหน้า: ยังโหลด user ไม่โชว์อะไร, ไม่ล็อกอินไป /login, role ไม่ตรงไป /
function Guard({ roles, children }) {
  const { user } = useAuth();
  if (user === undefined) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <Guard>
                <AppLayout />
              </Guard>
            }
          >
            <Route index element={<Navigate to="/stock" replace />} />
            <Route path="stock" element={<ProductListPage />}>
              <Route
                path="new"
                element={
                  <Guard roles={STAFF}>
                    <ProductFormPage />
                  </Guard>
                }
              />
            </Route>
            <Route path="stock/:id" element={<ProductDetailPage />} />
            <Route
              path="settings"
              element={
                <Guard roles={ADMIN}>
                  <SettingsPage />
                </Guard>
              }
            />
            <Route
              path="settings/users"
              element={
                <Guard roles={ADMIN}>
                  <UserListPage />
                </Guard>
              }
            >
              <Route path="new" element={<UserFormPage />} />
              <Route path=":id" element={<UserFormPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </QueryClientProvider>,
);
