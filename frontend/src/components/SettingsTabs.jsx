import { NavLink } from "react-router-dom";

// แท็บสลับ ตั้งค่าอู่ / ผู้ใช้
export default function SettingsTabs() {
  return (
    <nav aria-label="หมวดตั้งค่า" className="tabs">
      <NavLink to="/settings" end className="tab">
        ตั้งค่าอู่
      </NavLink>
      <NavLink to="/settings/users" className="tab">
        ผู้ใช้
      </NavLink>
    </nav>
  );
}
