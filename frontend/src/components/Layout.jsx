import { NavLink, Outlet } from "react-router-dom";
import { ROLE_NAME, useAuth } from "../auth";

const MENU = [
  { to: "/jobs", label: "ใบงาน" },
  { to: "/settings", label: "ตั้งค่า", roles: ["admin"] },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const menu = MENU.filter((m) => !m.roles || m.roles.includes(user.role));
  const link = ({ isActive }) =>
    `btn ${isActive ? "bg-accent-soft text-accent-ink" : "text-muted hover:bg-surface"}`;

  return (
    <div className="lg:flex">
      <aside className="hidden lg:flex lg:h-dvh lg:w-56 lg:shrink-0 lg:flex-col lg:gap-1 lg:border-r lg:border-line lg:p-3">
        <p className="px-4 py-3 font-semibold">อู่ซ่อมรถ</p>
        {menu.map((m) => (
          <NavLink key={m.to} to={m.to} className={link}>{m.label}</NavLink>
        ))}
        <div className="mt-auto border-t border-line px-4 pt-3 text-sm text-muted">
          <p>{user.full_name}</p>
          <p>{ROLE_NAME[user.role]}</p>
          <button className="mt-2 text-danger" onClick={logout}>ออกจากระบบ</button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 pb-20 lg:h-dvh lg:overflow-y-auto lg:pb-0">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 flex border-t border-line bg-white lg:hidden">
        {menu.map((m) => (
          <NavLink key={m.to} to={m.to} className={`${link} flex-1 flex-col text-xs`}>{m.label}</NavLink>
        ))}
      </nav>
    </div>
  );
}