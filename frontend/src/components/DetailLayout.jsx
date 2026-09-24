import { Link } from "react-router-dom";
import Icon from "./Icon";

// ปุ่ม ⋯ เปิดเมนูคำสั่งเพิ่มเติม คลิกแล้วปิดเมนูและเรียก onClick
function MoreMenu({ items }) {
  return (
    <details className="relative">
      <summary
        aria-label="คำสั่งเพิ่มเติม"
        className="btn btn-ghost btn-icon list-none [&::-webkit-details-marker]:hidden"
      >
        <Icon name="more" />
      </summary>
      <ul className="absolute right-0 z-20 mt-1 w-60 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lg">
        {items.map((m) => (
          <li key={m.label}>
            <button
              type="button"
              onClick={(e) => {
                e.currentTarget.closest("details").open = false;
                m.onClick();
              }}
              className="flex min-h-11 w-full items-center px-4 text-left hover:bg-surface"
            >
              {m.label}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}

// โครงหน้ารายละเอียด: ลิงก์กลับ + หัวเรื่อง (+ ปุ่ม action / เมนู ⋯) + เนื้อหา + แถบปุ่มหลัก (มือถือติดขอบล่าง จอใหญ่อยู่ท้ายเนื้อหา)
export default function DetailLayout({ back, backLabel, title, subtitle, badge, action, menu = [], footer, children }) {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <header>
        <Link
          to={back}
          className="-ml-2 inline-flex min-h-11 items-center gap-1 px-2 text-sm text-muted hover:text-ink"
        >
          <Icon name="back" size={18} />
          {backLabel}
        </Link>
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <h1 className="page-title break-words">{title}</h1>
            {subtitle && <div className="text-sm text-muted">{subtitle}</div>}
          </div>
          {badge && <div className="pt-1">{badge}</div>}
          {action}
          {menu.length > 0 && <MoreMenu items={menu} />}
        </div>
      </header>
      {children}
      {footer && (
        <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-white px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:static md:mx-0 md:border-0 md:px-0">
          {footer}
        </div>
      )}
    </div>
  );
}
