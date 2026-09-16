import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const AuthContext = createContext(null);

export const ROLE_NAME = { admin: "เจ้าของอู่", employee: "พนักงาน", mechanic: "ช่าง" };

// React hook สำหรับเก็บ state ของ user และฟังก์ชัน login/logout
export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);
  useEffect(() => {
    if (getToken()) api("/auth/me").then(setUser, () => setUser(null));
    else setUser(null);
  }, []);
  const login = async (username, password) => {
    const r = await api("/auth/login", { method: "POST", body: { username, password } });
    setToken(r.access_token);
    setUser(r.user);
  };
  const logout = () => {
    setToken(null);
    setUser(null);
  };
  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);