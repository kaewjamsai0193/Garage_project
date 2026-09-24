import { useEffect, useRef } from "react";
import Icon from "./Icon";

// popup จาก <dialog> เปิดทันทีที่ render (อยากปิดก็เลิก render): Esc/คลิกพื้นหลังเรียก onClose, มี onSubmit จะห่อเนื้อหาด้วย <form>
export default function Modal({ title, onClose, onSubmit, footer, children }) {
  const ref = useRef(null);

  useEffect(() => ref.current.showModal(), []);

  const Body = onSubmit ? "form" : "div";
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        // โดนตัว <dialog> เอง = คลิกฉากหลังนอกกล่อง (คลิกเนื้อหาข้างใน target จะเป็นลูกของมัน)
        if (e.target === ref.current) onClose();
      }}
    >
      <Body onSubmit={onSubmit} className="flex min-h-0 flex-auto flex-col">
        <header className="flex items-center gap-2 border-b border-line py-2 pr-2 pl-4">
          <h2 className="min-w-0 flex-1 truncate text-lg font-semibold">{title}</h2>
          <button type="button" aria-label="ปิด" className="btn btn-ghost btn-icon" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        <div className="min-h-0 flex-auto space-y-4 overflow-y-auto p-4">{children}</div>
        {footer && (
          <footer className="border-t border-line px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {footer}
          </footer>
        )}
      </Body>
    </dialog>
  );
}
