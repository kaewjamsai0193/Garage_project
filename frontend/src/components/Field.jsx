// input พร้อม label และ hint, props ที่เหลือส่งต่อให้ <input>
export default function Field({ label, hint, className = "", ...props }) {
  return (
    <label className={`block ${className}`}>
      <span className="label">{label}</span>
      <input className="input" {...props} />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}
