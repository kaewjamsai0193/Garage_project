import { Link, useNavigate } from "react-router-dom";

// แสดง items เป็นการ์ด (แคบ) หรือตาราง (กว้าง), คลิกแถวไปหน้า to(item)
export default function DataTable({ items, columns, card, to, empty = "ไม่มีข้อมูล" }) {
  const navigate = useNavigate();
  if (!items) return <p className="text-muted">กำลังโหลด…</p>;
  if (items.length === 0)
    return <p className="rounded-xl border border-dashed border-line py-10 text-center text-muted">{empty}</p>;

  // Container query: plain rows until the list is 48rem wide, then a table.
  return (
    <div className="@container">
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-white @3xl:hidden">
        {items.map((item) => (
          <li key={item.id}>
            <Link to={to(item)} className="block px-4 py-3 transition-colors duration-150 hover:bg-surface">
              {card(item)}
            </Link>
          </li>
        ))}
      </ul>
      <div className="hidden overflow-x-auto rounded-xl border border-line bg-white @3xl:block">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.label} className={c.align === "right" ? "text-right" : ""}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} onClick={() => navigate(to(item))}>
                {columns.map((c, i) => (
                  <td key={c.label} className={c.align === "right" ? "num text-right" : ""}>
                    {i === 0 ? (
                      <Link to={to(item)} className="font-semibold hover:underline">
                        {c.render(item)}
                      </Link>
                    ) : (
                      c.render(item)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
