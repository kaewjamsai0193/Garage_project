import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { api, formatMoney, formatQty, formatDate, formatUnitPrice } from "../api";
import { useAuth } from "../auth";
import Field from "../components/Field";
import Icon from "../components/Icon";
import DetailLayout from "../components/DetailLayout";
import ReasonDialog from "../components/ReasonDialog";
import ProductModal from "../components/ProductModal";
import StatusBadge, { productStatus } from "../components/StatusBadge";

const SOURCE_LABEL = { adjustment: "ปรับเพิ่ม", opening: "สต็อกตั้งต้น" };
const MOVE_LABEL = { adjust: "ปรับสต็อก", opening: "ตั้งต้น" };
const TABS = [
  ["lots", "Lot"],
  ["moves", "สมุดสต็อก"],
];

// หน้าสินค้า /stock/:id: ดึงสินค้า + Lot + สมุดสต็อก, เปิด popup แก้สินค้า / ปรับลด / ปรับเพิ่ม
export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const isStaff = user.role !== "mechanic";
  const product = useQuery({ queryKey: ["products", id] });
  const lots = useQuery({ queryKey: ["products", id, "lots"] });
  const moves = useQuery({ queryKey: ["products", id, "movements"] });
  const [tab, setTab] = useState("lots");
  const [dialog, setDialog] = useState(null); // ป๊อปอัพที่เปิดอยู่: null หรือ { type: "edit" | "up" | "down", lot? }
  const closeDialog = () => setDialog(null);

  const p = product.data;
  if (!p) return <DetailLayout back="/stock" backLabel="สต็อก" title={product.error?.message || "กำลังโหลด…"} />;

  return (
    <DetailLayout
      back="/stock"
      backLabel="สต็อก"
      title={p.name}
      subtitle={p.code}
      badge={<StatusBadge status={productStatus(p)} />}
      menu={isAdmin ? [{ label: "ปรับเพิ่ม / สต็อกตั้งต้น", onClick: () => setDialog({ type: "up" }) }] : []}
      footer={
        isStaff && (
          <button type="button" className="btn btn-primary w-full" onClick={() => setDialog({ type: "edit" })}>
            <Icon name="edit" size={20} />
            แก้สินค้า
          </button>
        )
      }
    >
      <div>
        <div className="text-sm text-muted">คงเหลือ</div>
        <div className="num text-4xl font-bold">
          {formatQty(p.qty_on_hand)} <span className="text-lg font-medium text-muted">{p.unit}</span>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <Fact label="ราคาขาย" value={formatMoney(p.sale_price)} />
        <Fact label="ขั้นต่ำ" value={Number(p.min_stock) > 0 ? formatQty(p.min_stock) : "-"} />
      </dl>

      <div role="tablist" aria-label="มุมมอง" className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className="tab"
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "lots" ? (
        <LotList
          lots={lots}
          showCost={isAdmin}
          canAdjust={isStaff}
          onAdjustDown={(lot) => setDialog({ type: "down", lot })}
        />
      ) : (
        <MovementList moves={moves} />
      )}

      {dialog?.type === "edit" && <ProductModal initial={p} onClose={closeDialog} onSaved={closeDialog} />}
      {dialog?.type === "up" && <AdjustUpDialog productId={p.id} onClose={closeDialog} />}
      {dialog?.type === "down" && <AdjustDownDialog lot={dialog.lot} onClose={closeDialog} />}
    </DetailLayout>
  );
}

// กล่องข้อมูลสั้น หัวข้อ + ค่า
function Fact({ label, value }) {
  return (
    <div className="rounded-lg bg-surface p-2">
      <dt className="text-muted">{label}</dt>
      <dd className="num font-semibold">{value}</dd>
    </div>
  );
}

// รายการ Lot เก่า→ใหม่: ต้นทุนโชว์เฉพาะ admin, Lot ที่ยังเหลือของมีปุ่มปรับลด
function LotList({ lots, showCost, canAdjust, onAdjustDown }) {
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {lots.error && (
        <li role="alert" className="field-error p-4">
          {lots.error.message}
        </li>
      )}
      {lots.data?.length === 0 && <li className="p-4 text-muted">ยังไม่มีของเข้าคลัง</li>}
      {lots.data?.map((lot) => {
        const hasStock = Number(lot.qty_remaining) > 0;
        return (
          <li key={lot.id} className={`space-y-1 px-4 py-3 ${hasStock ? "" : "text-muted"}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">
                Lot #{lot.id} · {SOURCE_LABEL[lot.source_type]}
              </span>
              <span className="text-sm">{formatDate(lot.created_at)}</span>
            </div>
            <div className="num text-sm">
              รับเข้า {formatQty(lot.qty_received)} · <b>เหลือ {formatQty(lot.qty_remaining)}</b>
            </div>
            {showCost && <div className="num text-sm">ต้นทุน/หน่วย {formatUnitPrice(lot.unit_cost)}</div>}
            {canAdjust && hasStock && (
              <button type="button" className="btn btn-secondary" onClick={() => onAdjustDown(lot)}>
                <Icon name="minus" size={20} />
                ปรับลด
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// สมุดสต็อก: รายการเข้า/ออกล่าสุดก่อน ตัวเลขติดลบเป็นสีแดง
function MovementList({ moves }) {
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {moves.error && (
        <li role="alert" className="field-error p-4">
          {moves.error.message}
        </li>
      )}
      {moves.data?.length === 0 && <li className="p-4 text-muted">ยังไม่มีรายการ</li>}
      {moves.data?.map((m) => {
        const qty = Number(m.qty);
        return (
          <li key={m.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
            <div className="min-w-0 text-sm">
              <div className="font-semibold">
                {MOVE_LABEL[m.movement_type]} · Lot #{m.lot_id}
              </div>
              <div className="text-muted">
                {formatDate(m.created_at)} · {m.created_by_name}
              </div>
              {m.reason && <div className="text-muted">{m.reason}</div>}
            </div>
            <span className={`num font-bold ${qty < 0 ? "text-danger" : ""}`}>
              {qty > 0 ? "+" : ""}
              {formatQty(m.qty)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// POST คำสั่งปรับสต็อก สำเร็จแล้วให้ข้อมูลสินค้าทุกหน้าโหลดใหม่ (คงเหลือ, Lot, สมุดสต็อก, รายการสินค้า) แล้วปิด popup
function useAdjustStock(path, onDone) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => api(path, { method: "POST", body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onDone();
    },
  });
}

// popup ปรับลด Lot: POST /stock/adjust-down { lot_id, qty, reason }
function AdjustDownDialog({ lot, onClose }) {
  const { register, handleSubmit } = useForm({ defaultValues: { qty: "", reason: "" } });
  const adjustDown = useAdjustStock("/stock/adjust-down", onClose);
  return (
    <ReasonDialog
      title={`ปรับลด Lot #${lot.id}`}
      onClose={onClose}
      register={register}
      mutation={adjustDown}
      onSubmit={handleSubmit((form) => adjustDown.mutate({ ...form, lot_id: lot.id }))}
    >
      <Field
        label={`จำนวนที่ลด (เหลือ ${formatQty(lot.qty_remaining)})`}
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0.001"
        required
        {...register("qty")}
      />
    </ReasonDialog>
  );
}

// popup ปรับเพิ่ม/สต็อกตั้งต้น (admin): POST /stock/adjust-up สร้าง Lot ใหม่
function AdjustUpDialog({ productId, onClose }) {
  const { register, handleSubmit } = useForm({
    defaultValues: { source_type: "adjustment", qty: "", unit_cost: "", reason: "" },
  });
  const adjustUp = useAdjustStock("/stock/adjust-up", onClose);
  return (
    <ReasonDialog
      title="ปรับเพิ่ม / สต็อกตั้งต้น"
      onClose={onClose}
      register={register}
      mutation={adjustUp}
      onSubmit={handleSubmit((form) => adjustUp.mutate({ ...form, product_id: productId }))}
    >
      <label className="block">
        <span className="label">ประเภท</span>
        <select className="input" {...register("source_type")}>
          <option value="adjustment">ปรับเพิ่ม</option>
          <option value="opening">สต็อกตั้งต้น</option>
        </select>
      </label>
      <Field label="จำนวน" type="number" inputMode="decimal" step="0.001" min="0.001" required {...register("qty")} />
      <Field
        label="ต้นทุนต่อหน่วย (ก่อน VAT)"
        type="number"
        inputMode="decimal"
        step="0.0001"
        min="0"
        required
        {...register("unit_cost")}
      />
    </ReasonDialog>
  );
}
