import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { formatMoney, formatQty } from "../api";
import { useAuth } from "../auth";
import ListLayout from "../components/ListLayout";
import DataTable from "../components/DataTable";
import StatusBadge, { productStatus } from "../components/StatusBadge";
import SearchBar from "../components/SearchBar";

const FILTERS = [
  ["active", "ใช้งานอยู่"],
  ["low", "ต่ำกว่าขั้นต่ำ"],
  ["inactive", "เลิกใช้"],
];

// หน้า /stock: GET /products แล้วค้น/กรองฝั่ง client, route ลูก new เปิด popup เพิ่มสินค้า
export default function ProductListPage() {
  const { user } = useAuth();
  const { data, error } = useQuery({ queryKey: ["products"] });
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("active");
  const text = q.trim().toLowerCase();
  const items = data?.filter(
    (p) =>
      (filter === "active" ? p.is_active : productStatus(p) === filter) &&
      (!text || p.code.toLowerCase().includes(text) || p.name.toLowerCase().includes(text)),
  );

  return (
    <ListLayout
      title="สต็อก"
      basePath="/stock"
      action={user.role !== "mechanic" && { label: "เพิ่มสินค้า", to: "/stock/new" }}
      toolbar={
        <SearchBar
          q={q}
          setQ={setQ}
          placeholder="ค้นรหัสหรือชื่อสินค้า"
          filters={FILTERS}
          filter={filter}
          setFilter={setFilter}
        />
      }
    >
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      <DataTable
        items={items}
        to={(p) => `/stock/${p.id}`}
        empty="ไม่พบสินค้า"
        card={(p) => (
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-semibold">{p.name}</div>
              <div className="text-sm text-muted">
                {p.code} · ขาย {formatMoney(p.sale_price)}
              </div>
              <div className="mt-2">
                <StatusBadge status={productStatus(p)} />
              </div>
            </div>
            <div className="text-right">
              <div className="num text-2xl font-bold">{formatQty(p.qty_on_hand)}</div>
              <div className="text-sm text-muted">{p.unit}</div>
            </div>
          </div>
        )}
        columns={[
          { label: "รหัส", render: (p) => p.code },
          { label: "ชื่อ", render: (p) => p.name },
          { label: "ราคาขาย", align: "right", render: (p) => formatMoney(p.sale_price) },
          { label: "คงเหลือ", align: "right", render: (p) => `${formatQty(p.qty_on_hand)} ${p.unit}` },
          { label: "สถานะ", render: (p) => <StatusBadge status={productStatus(p)} /> },
        ]}
      />
    </ListLayout>
  );
}
