import { useNavigate, useOutletContext } from "react-router-dom";
import ProductModal from "../components/ProductModal";

const EMPTY_PRODUCT = { code: "", name: "", unit: "", sale_price: "", min_stock: "0", is_active: true };

// /stock/new: popup เพิ่มสินค้าบนหน้ารายการ บันทึกแล้วไปหน้าสินค้าตัวใหม่
export default function ProductFormPage() {
  const { close } = useOutletContext();
  const navigate = useNavigate();
  return <ProductModal initial={EMPTY_PRODUCT} onClose={close} onSaved={(p) => navigate(`/stock/${p.id}`)} />;
}
