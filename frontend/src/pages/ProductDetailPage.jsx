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
// adjust ค่าบวก = ปรับเพิ่มแบบเก่า (ก่อนเหลือแค่ปุ่มของเสีย) ยังมีในฐาน
const MOVE_LABEL = { adjust: "ของเสีย/สูญหาย", opening: "ตั้งต้น" };
const TABS = [
  ["lots", "Lot"],
  ["moves", "สมุดสต็อก"],
];

// หน้าสินค้า /stock/:id: ดึงสินค้า + Lot + สมุดสต็อก, เปิด popup แก้สินค้า / ของเสีย/สูญหาย (ปุ่มล่าง) / สต็อกตั้งต้น (ปุ่มบน)
export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const isStaff = user.role !== "mechanic";
  const product = useQuery({ queryKey: ["products", id] });
  const lots = useQuery({ queryKey: ["products", id, "lots"] });
  const moves = useQuery({ queryKey: ["products", id, "movements"] });
  const [tab, setTab] = useState("lots");
  const [dialog, setDialog] = useState(null); // ป๊อปอัพที่เปิดอยู่: null หรือ { type: "edit" | "opening" | "waste" }
  const closeDialog = () => setDialog(null);
  const stockedLots = lots.data?.filter((l) => Number(l.qty_remaining) > 0) ?? []; // Lot ที่ยังมีของให้แจ้งเสีย

  const p = product.data;
  if (!p) return <DetailLayout back="/stock" backLabel="สต็อก" title={product.error?.message || "กำลังโหลด…"} />;

  return (
    <DetailLayout
      back="/stock"
      backLabel="สต็อก"
      title={p.name}
      subtitle={p.code}
      badge={<StatusBadge status={productStatus(p)} />}
      action={
        isAdmin && (
          <button type="button" className="btn btn-secondary" onClick={() => setDialog({ type: "opening" })}>
            <Icon name="plus" size={20} />
            สต็อกตั้งต้น
          </button>
        )
      }
      footer={
        isStaff && (
          <div className="flex gap-2">
            <button
              type="button"
              className="btn btn-secondary flex-1"
              disabled={!stockedLots.length}
              onClick={() => setDialog({ type: "waste" })}
            >
              <Icon name="minus" size={20} />
              ของเสีย/สูญหาย
            </button>
            <button type="button" className="btn btn-primary flex-1" onClick={() => setDialog({ type: "edit" })}>
              <Icon name="edit" size={20} />
              แก้สินค้า
            </button>
          </div>
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
      {tab === "lots" ? <LotList lots={lots} showCost={isAdmin} /> : <MovementList moves={moves} />}

      {dialog?.type === "edit" && <ProductModal initial={p} onClose={closeDialog} onSaved={closeDialog} />}
      {dialog?.type === "opening" && <OpeningDialog productId={p.id} onClose={closeDialog} />}
      {dialog?.type === "waste" && <WasteDialog lots={stockedLots} onClose={closeDialog} />}
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

// รายการ Lot เก่า→ใหม่: ต้นทุนโชว์เฉพาะ admin, Lot ที่ของหมดเป็นสีจาง
function LotList({ lots, showCost }) {
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
                {m.movement_type === "adjust" && qty > 0 ? "ปรับเพิ่ม" : MOVE_LABEL[m.movement_type]} · Lot #{m.lot_id}
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

// popup ของเสีย/สูญหาย (เลือก Lot ค่าเริ่ม Lot เก่าสุด): POST /stock/adjust-down { lot_id, qty, reason }
function WasteDialog({ lots, onClose }) {
  const { register, handleSubmit, watch } = useForm({
    defaultValues: { lot_id: String(lots[0].id), qty: "", reason: "" },
  });
  const waste = useAdjustStock("/stock/adjust-down", onClose);
  const lot = lots.find((l) => String(l.id) === watch("lot_id"));
  return (
    <ReasonDialog
      title="ของเสีย/สูญหาย"
      onClose={onClose}
      register={register}
      mutation={waste}
      onSubmit={handleSubmit((form) => waste.mutate({ ...form, lot_id: Number(form.lot_id) }))}
    >
      <label className="block">
        <span className="label">Lot</span>
        <select className="input" {...register("lot_id")}>
          {lots.map((l) => (
            <option key={l.id} value={l.id}>
              Lot #{l.id} · {formatDate(l.created_at)} · เหลือ {formatQty(l.qty_remaining)}
            </option>
          ))}
        </select>
      </label>
      <Field
        label={`จำนวน (เหลือ ${formatQty(lot.qty_remaining)})`}
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0.001"
        max={lot.qty_remaining}
        required
        {...register("qty")}
      />
    </ReasonDialog>
  );
}

// popup สต็อกตั้งต้น (admin): POST /stock/opening สร้าง Lot ใหม่ (ของเข้าปกติมาจากใบรับของ)
function OpeningDialog({ productId, onClose }) {
  const { register, handleSubmit } = useForm({ defaultValues: { qty: "", unit_cost: "", reason: "" } });
  const opening = useAdjustStock("/stock/opening", onClose);
  return (
    <ReasonDialog
      title="สต็อกตั้งต้น"
      onClose={onClose}
      register={register}
      mutation={opening}
      onSubmit={handleSubmit((form) => opening.mutate({ ...form, product_id: productId }))}
    >
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
