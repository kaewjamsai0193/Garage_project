import { Link, useNavigate, useOutlet } from "react-router-dom";
import Icon from "./Icon";

// โครงหน้ารายการ: หัว + ปุ่มเพิ่ม + toolbar + เนื้อหา, ส่ง close() ให้ route ลูก (popup) ผ่าน outlet context
export default function ListLayout({ title, basePath, action, toolbar, children }) {
  const navigate = useNavigate();
  const outlet = useOutlet({ close: () => navigate(basePath) });

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="page-title mr-auto">{title}</h1>
        {action && (
          <Link to={action.to} className="btn btn-primary hidden md:inline-flex">
            <Icon name="plus" size={20} />
            {action.label}
          </Link>
        )}
      </div>
      {toolbar}
      {children}
      {action && (
        <Link
          to={action.to}
          aria-label={action.label}
          className="btn btn-primary btn-icon fixed right-4 bottom-6 z-20 size-14 rounded-2xl shadow-lg md:hidden"
        >
          <Icon name="plus" size={28} />
        </Link>
      )}
      {outlet}
    </section>
  );
}
