import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, plainNumber } from "../api";
import Field from "../components/Field";
import Icon from "../components/Icon";
import SettingsTabs from "../components/SettingsTabs";

const GROUPS = [
  [
    "ข้อมูลบนหัวเอกสาร",
    [
      ["shop_name", "ชื่ออู่"],
      ["shop_tax_id", "เลขประจำตัวผู้เสียภาษี"],
      ["shop_address", "ที่อยู่"],
    ],
  ],
  ["ค่าระบบ", [["vat_rate", "อัตรา VAT (%)", "number"]]],
];

// หน้า /settings: GET /settings แล้วส่งค่าให้ SettingsForm
export default function SettingsPage() {
  const { data, error } = useQuery({ queryKey: ["settings"] });

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="page-title">ตั้งค่าและผู้ใช้</h1>
      <SettingsTabs />
      {error && (
        <p role="alert" className="field-error">
          {error.message}
        </p>
      )}
      {data ? <SettingsForm initial={data} /> : !error && <p className="text-muted">กำลังโหลด…</p>}
    </div>
  );
}

// ฟอร์มตั้งค่าอู่: PUT /settings แล้วเอาค่าที่ backend ตอบกลับใส่ cache ["settings"] เลย ไม่ต้องยิง GET ซ้ำ
function SettingsForm({ initial }) {
  const queryClient = useQueryClient();
  const { register, handleSubmit } = useForm({
    defaultValues: { ...initial, vat_rate: plainNumber(initial.vat_rate) },
  });
  const save = useMutation({
    mutationFn: (form) => api("/settings", { method: "PUT", body: form }),
    onSuccess: (saved) => queryClient.setQueryData(["settings"], saved),
  });

  return (
    <form onSubmit={handleSubmit((form) => save.mutate(form))} className="space-y-4">
      {GROUPS.map(([title, fields]) => (
        <section key={title} className="card space-y-4">
          <h2 className="font-semibold">{title}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {fields.map(([key, label, type]) => (
              <Field
                key={key}
                label={label}
                type={type || "text"}
                inputMode={type ? "decimal" : undefined}
                step="any"
                {...register(key)}
              />
            ))}
          </div>
        </section>
      ))}
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "กำลังบันทึก…" : "บันทึก"}
        </button>
        {save.error && (
          <span role="alert" className="field-error">
            {save.error.message}
          </span>
        )}
        {save.isSuccess && (
          <span role="status" className="inline-flex items-center gap-1 font-semibold">
            <Icon name="check" size={20} />
            บันทึกแล้ว
          </span>
        )}
      </div>
    </form>
  );
}
