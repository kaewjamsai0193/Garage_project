import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, queryClient, setToken, removeToken } from "./api";

const AuthContext = createContext(null);

export const ROLE_NAME = { admin: "เจ้าของอู่", employee: "พนักงาน", mechanic: "ช่าง" };

// Context ผู้ใช้: เปิดแอปถ้ามี token ดึง /auth/me, user = undefined(กำลังโหลด) | null | object
export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    api("/auth/me")
      .then((user) => setUser(user))
      .catch(() => setUser(null));
  }, []);

  // POST /auth/login → เก็บ token + ตั้ง user
  const login = async (username, password) => {
    const response = await api("/auth/login", { method: "POST", body: { username, password } });
    setToken(response.access_token);
    setUser(response.user);
  };

  // ลบ token + ล้าง cache (กันคนถัดไปเห็นข้อมูลค้าง เช่นต้นทุนที่เห็นได้เฉพาะ admin) + ล้าง user
  const logout = () => {
    removeToken();
    queryClient.clear();
    setUser(null);
  };
  return <AuthContext.Provider value={{ user, login, logout }}> {children} </AuthContext.Provider>;
}

// ดึง { user, login, logout } จาก AuthContext
export const useAuth = () => useContext(AuthContext);
