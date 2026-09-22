import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import Icon from "../components/Icon";

// หน้าเข้าสู่ระบบ ล็อกอินอยู่แล้วเด้งไป /
export default function LoginPage() {
  const { user, login } = useAuth();
  const { register, handleSubmit } = useForm({ defaultValues: { username: "", password: "" } });
  // ส่ง username/password ไป auth.login, ผิดโชว์ error
  const signIn = useMutation({ mutationFn: ({ username, password }) => login(username, password) });
  if (user) return <Navigate to="/" replace />;

  return (
    <main className="grid min-h-dvh place-items-center bg-surface px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-3 grid size-14 place-items-center rounded-2xl bg-accent text-white">
            <Icon name="wrench" size={30} />
          </div>
          <h1 className="text-2xl font-semibold">อู่ซ่อมรถ</h1>
          <p className="text-muted">เข้าสู่ระบบเพื่อเริ่มงาน</p>
        </div>
        <form onSubmit={handleSubmit((form) => signIn.mutate(form))} className="card space-y-4 p-6">
          <label className="block">
            <span className="label">ชื่อผู้ใช้</span>
            <input className="input" autoComplete="username" autoCapitalize="none" required {...register("username")} />
          </label>
          <label className="block">
            <span className="label">รหัสผ่าน</span>
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              required
              {...register("password")}
            />
          </label>
          {signIn.error && (
            <p role="alert" className="field-error">
              {signIn.error.message}
            </p>
          )}
          <button className="btn btn-primary w-full" disabled={signIn.isPending}>
            {signIn.isPending ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}
          </button>
        </form>
      </div>
    </main>
  );
}
