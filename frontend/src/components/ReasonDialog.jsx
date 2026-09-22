import Modal from "./Modal";

// popup ที่มีช่อง "เหตุผล" ท้ายฟอร์ม: ฟอร์ม (register/onSubmit) และ mutation มาจากคนเรียก
// render เมื่อจะเปิด เลิก render = ปิด ค่าในฟอร์มล้างเอง
export default function ReasonDialog({ title, onClose, onSubmit, register, mutation, children }) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      onSubmit={onSubmit}
      footer={
        <>
          {mutation.error && (
            <p role="alert" className="field-error mb-2">
              {mutation.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              ยกเลิก
            </button>
            <button className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? "กำลังบันทึก…" : "ยืนยัน"}
            </button>
          </div>
        </>
      }
    >
      {children}
      <label className="block">
        <span className="label">เหตุผล</span>
        <textarea className="input" rows={3} required {...register("reason")} />
      </label>
    </Modal>
  );
}
