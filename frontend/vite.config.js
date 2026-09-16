import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // proxy ชี้ที่ชื่อ service "api" ไม่ใช่ localhost เพราะอยู่คนละ container
  // usePolling จำเป็นบน Windows + Docker ไม่งั้น hot reload ไม่ทำงาน
  server: { proxy: { "/api": "http://api:8000" }, watch: { usePolling: true } },
});
