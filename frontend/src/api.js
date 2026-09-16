//ที่เดียวที่คุยกับ backend
import axios from "axios";
import { useCallback, useEffect, useState } from "react";

export const getToken = () => localStorage.getItem("token");
export const setToken = (t) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token"));

// แปลง error type เป็นข้อความที่อ่านง่าย
const validationText = ({ type, ctx = {} }) =>
  ({
    missing: "กรอกข้อมูลไม่ครบ",
    greater_than: `ต้องมากกว่า ${ctx.gt}`,
    greater_than_equal: `ต้องไม่น้อยกว่า ${ctx.ge}`,
    less_than: `ต้องน้อยกว่า ${ctx.lt}`,
    less_than_equal: `ต้องไม่เกิน ${ctx.le}`,
    string_too_short: "ข้อความสั้นเกินไป",
    string_too_long: "ข้อความยาวเกินไป",
  })[type] ?? "รูปแบบข้อมูลไม่ถูกต้อง";


// แปลง error จาก backend เป็นข้อความที่อ่านง่าย
function errorText(data) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return "ข้อมูลไม่ถูกต้อง: " + [...new Set(d.map(validationText))].join(", ");
  return "เกิดข้อผิดพลาด กรุณาลองใหม่";
}


// เรียก backend ทุกครั้งผ่านฟังก์ชันนี้ แนบ token และแปลง error ให้
export async function api(path, { method = "GET", body } = {}) {
  const token = getToken();
  try {
    const res = await axios.request({
      url: `/api${path}`,
      method,
      data: body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.status === 204 ? null : res.data;
  } catch (e) {
    if (e.response?.status === 401 && path !== "/auth/login") {
      setToken(null);
      location.assign("/login");
    }
    throw new Error(errorText(e.response?.data));
  }
}

// React hook สำหรับเรียก backend และเก็บ state ของข้อมูลและ error
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: "" });
  const reload = useCallback(() => {
    if (!path) return setState({ data: null, error: "" });
    api(path).then((data) => setState({ data, error: "" }), (e) => setState({ data: null, error: e.message }));
  }, [path]);
  useEffect(reload, [reload]);
  return { ...state, reload };
}