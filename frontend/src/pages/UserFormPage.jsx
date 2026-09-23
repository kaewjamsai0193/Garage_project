import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useOutletContext, useParams } from "react-router-dom";
import { api } from "../api";
import { ROLE_NAME, useAuth } from "../auth";
import Field from "../components/Field";
import Modal from "../components/Modal";

const EMPTY = { username: "", full_name: "", role: "employee", password: "" };

// popup ผู้ใช้ /settings/users/new หรือ /:id: หา user จาก cache ["users"] ชุดเดียวกับ UserListPage
// (มีของแล้ววาดทันที แล้ว TanStack Query ดึงใหม่เบื้องหลังหนึ่งครั้ง) แล้วส่งให้ UserForm
export default function UserFormPage() {
  const { id } = useParams();
  const { close } = useOutletContext();
  const { data: users } = useQuery({ queryKey: ["users"] });
  const current = id && users?.find((u) => String(u.id) === id);
  if (id && !current) return <Modal title={users ? "ไม่พบผู้ใช้" : "กำลังโหลด…"} onClose={close} />;
  return <UserForm key={id ?? "new"} initial={current ? { ...current, password: "" } : EMPTY} close={close} />;
}

// ฟอร์มผู้ใช้: สร้าง POST /users, แก้ PATCH /users/{id}, ปุ่มเปิด/ปิดใช้งาน
function UserForm({ initial, close }) {
  const isEdit = !!initial.id;
  const { user: me, setUser } = useAuth();
  const queryClient = useQueryClient();
  const refreshUsers = () => queryClient.invalidateQueries({ queryKey: ["users"] });
  const { register, handleSubmit } = useForm({ defaultValues: initial });

  const save = useMutation({
    mutationFn: (form) =>
      isEdit
        ? api(`/users/${initial.id}`, {
            method: "PATCH",
            body: { full_name: form.full_name, role: form.role, password: form.password || null },
          })
        : api("/users", { method: "POST", body: form }),
    onSuccess: (saved) => {
      if (saved.id === me.id) setUser(saved); // แก้บัญชีตัวเอง → ชื่อในแถบข้างเปลี่ยนตาม
      refreshUsers();
      close();
    },
  });

  // สลับ is_active: สถานะที่โชว์มาจาก initial (ข้อมูลใน cache) พอ refresh แล้วจะอัปเดตเอง
  const toggleActive = useMutation({
    mutationFn: () => api(`/users/${initial.id}`, { method: "PATCH", body: { is_active: !initial.is_active } }),
    onSuccess: refreshUsers,
  });

  const busy = save.isPending || toggleActive.isPending;
  const error = save.error ?? toggleActive.error;

  return (
    <Modal
      title={isEdit ? `แก้ไข ${initial.username}` : "เพิ่มผู้ใช้"}
      onClose={close}
      onSubmit={handleSubmit((form) => save.mutate(form))}
      footer={
        <>
          {error && (
            <p role="alert" className="field-error mb-2">
              {error.message}
            </p>
          )}
          <div className="flex gap-2">
            <button className="btn btn-primary flex-1" disabled={busy}>
              บันทึก
            </button>
            {isEdit && (
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => toggleActive.mutate()}>
                {initial.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
              </button>
            )}
          </div>
        </>
      }
    >
      {isEdit && <p className="text-sm text-muted">{initial.is_active ? "ใช้งานอยู่" : "ปิดใช้งานแล้ว"}</p>}
      <Field
        label="ชื่อผู้ใช้ (อังกฤษ/ตัวเลข)"
        required
        disabled={isEdit}
        autoCapitalize="none"
        autoComplete="off"
        {...register("username")}
      />
      <Field label="ชื่อ-นามสกุล" required {...register("full_name")} />
      <label className="block">
        <span className="label">บทบาท</span>
        <select className="input" {...register("role")}>
          {Object.entries(ROLE_NAME).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <Field
        label={isEdit ? "รหัสผ่านใหม่" : "รหัสผ่าน"}
        hint={isEdit ? "เว้นว่างถ้าไม่เปลี่ยน · อย่างน้อย 6 ตัว" : "อย่างน้อย 6 ตัว"}
        type="password"
        minLength={6}
        required={!isEdit}
        autoComplete="new-password"
        {...register("password")}
      />
    </Modal>
  );
}
