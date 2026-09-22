import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate, useOutletContext } from "react-router-dom";
import { api, plainNumber } from "../api";
import Field from "../components/Field";
import Modal from "../components/Modal";

export const EMPTY_PRODUCT = { code: "", name: "", unit: "", sale_price: "", min_stock: "0", is_active: true };

// /stock/new: popup เพิ่มสินค้าบนหน้ารายการ บันทึกแล้วไปหน้าสินค้าตัวใหม่
export default function ProductFormPage() {
  const { close } = useOutletContext();
  const navigate = useNavigate();
  return <ProductModal initial={EMPTY_PRODUCT} onClose={close} onSaved={(p) => navigate(`/stock/${p.id}`)} />;
}

// ฟอร์มสินค้า: มี id → PUT /products/{id}, ไม่มี → POST /products, สำเร็จแล้วให้ข้อมูลสินค้าทุกหน้าโหลดใหม่
export function ProductModal({ initial, onClose, onSaved }) {
  const isEdit = !!initial.id;
  const queryClient = useQueryClient();
  const { register, handleSubmit } = useForm({
    defaultValues: {
      ...initial,
      sale_price: plainNumber(initial.sale_price),
      min_stock: plainNumber(initial.min_stock),
    },
  });
  const save = useMutation({
    mutationFn: (form) =>
      api(isEdit ? `/products/${initial.id}` : "/products", { method: isEdit ? "PUT" : "POST", body: form }),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      onSaved(saved);
    },
  });

  return (
    <Modal
      title={isEdit ? `แก้ไข ${initial.code}` : "เพิ่มสินค้า"}
      onClose={onClose}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {save.error && (
            <p role="alert" className="field-error mb-2">
              {save.error.message}
            </p>
          )}
          <button className="btn btn-primary w-full" disabled={save.isPending}>
            {save.isPending ? "กำลังบันทึก…" : "บันทึกสินค้า"}
          </button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="รหัสสินค้า" required autoCapitalize="characters" {...register("code")} />
        <Field label="หน่วย" required placeholder="ชิ้น, ขวด" {...register("unit")} />
      </div>
      <Field label="ชื่อสินค้า" required {...register("name")} />
      <Field
        label="ราคาขาย (รวม VAT)"
        type="number"
        inputMode="decimal"
        step="0.01"
        min="0"
        required
        {...register("sale_price")}
      />
      <Field
        label="จุดเตือนขั้นต่ำ"
        hint="0 = ไม่เตือน"
        type="number"
        inputMode="decimal"
        step="0.001"
        min="0"
        {...register("min_stock")}
      />
      <label className="flex min-h-11 cursor-pointer items-center gap-3">
        <input type="checkbox" role="switch" className="size-5 accent-accent" {...register("is_active")} />
        ใช้งานอยู่
      </label>
    </Modal>
  );
}
