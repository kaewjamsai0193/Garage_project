import { QueryClient } from "@tanstack/react-query";
import axios from "axios";

// token ใน localStorage: อ่าน / เก็บ / ลบ
export const getToken = () => localStorage.getItem("token");
export const setToken = (token) => localStorage.setItem("token", token);
export const removeToken = () => localStorage.removeItem("token");

// แปลง error validation 1 รายการจาก FastAPI (422) → ข้อความไทย
const validationMessage = ({ type, ctx = {} }) =>
  ({
    missing: "กรอกข้อมูลไม่ครบ",
    greater_than: `ต้องมากกว่า ${ctx.gt}`,
    greater_than_equal: `ต้องไม่น้อยกว่า ${ctx.ge}`,
    less_than: `ต้องน้อยกว่า ${ctx.lt}`,
    less_than_equal: `ต้องไม่เกิน ${ctx.le}`,
    string_too_short: "ข้อความสั้นเกินไป",
    string_too_long: "ข้อความยาวเกินไป",
  })[type] ?? "รูปแบบข้อมูลไม่ถูกต้อง";

// แปลง body error จาก backend → ข้อความเดียวไว้โชว์ผู้ใช้
function toErrorMessage(data) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return "ข้อมูลไม่ถูกต้อง: " + [...new Set(d.map(validationMessage))].join(", ");
  return "เกิดข้อผิดพลาด กรุณาลองใหม่";
}

// เรียก backend /api{path} แนบ token → คืน data (204 = null), 401 ลบ token แล้วไปหน้า login
export async function api(path, { method = "GET", body } = {}) {
  const token = getToken();

  try {
    const response = await axios.request({
      url: `/api${path}`,
      method,
      data: body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return response.status === 204 ? null : response.data;
  } catch (error) {
    if (error.response?.status === 401 && path !== "/auth/login") {
      removeToken();
      location.assign("/login");
    }
    throw new Error(toErrorMessage(error.response?.data));
  }
}

// cache ข้อมูลจาก backend ของทั้งแอป
// queryKey คือ path ของ API แยกเป็นท่อน: ["products", id, "lots"] → GET /products/{id}/lots
// ท่อนแรกเป็นกลุ่มข้อมูล สั่ง invalidateQueries({ queryKey: ["products"] }) ทีเดียว โหลดใหม่ทุกอย่างของสินค้า
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: ({ queryKey }) => api("/" + queryKey.join("/")),
      retry: false, // error จาก backend (404, 403) ลองซ้ำก็ได้ผลเดิม
    },
  },
});

// จัดรูปตัวเลขไว้โชว์: เงิน (2 ตำแหน่งเสมอ), ต้นทุน/ราคาต่อหน่วย (ทศนิยมเท่าที่มีจริง ≤4), จำนวน (≤3), วันที่ไทยเวลากรุงเทพ
export const formatMoney = (v) =>
  Number(v).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const formatUnitPrice = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 4 });

export const formatQty = (v) => Number(v).toLocaleString("th-TH", { maximumFractionDigits: 3 });

// ตัดศูนย์ท้ายทิ้งไว้ใส่ช่องกรอก: "150.0000" → "150" (ต่างจาก formatMoney ที่ใส่ , และทศนิยมให้ ซึ่งพิมพ์ต่อไม่ได้)
export const plainNumber = (v) => (v === null || v === undefined || v === "" ? "" : String(Number(v)));

export const formatDate = (v) =>
  v ? new Date(v).toLocaleDateString("th-TH-u-ca-gregory", { timeZone: "Asia/Bangkok", dateStyle: "medium" }) : "-";
