from fastapi import FastAPI

app = FastAPI(title="ระบบจัดการอู่ซ่อมรถ")


@app.get("/api/health")
def health():
    return {"ok": True}
