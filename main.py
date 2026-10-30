from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="活動報名模組 - cai")

# PostgreSQL 資料庫連線設定
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "010030"  # 👈 請填入你的 PostgreSQL 密碼
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# 報名資料結構定義
class RegisterRequest(BaseModel):
    name: str
    phone: str

# 首頁路由：提供報名頁面
@app.get("/")
def read_root():
    return FileResponse("index.html")

# ----------------- cai 核心模組：使用者報名 -----------------
@app.post("/api/activities/{act_id}/register")
def register_activity(act_id: int, req: RegisterRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. 檢查活動是否存在以及是否截止 (Pro版需求)
            cur.execute("SELECT is_closed FROM activities WHERE id = %s;", (act_id,))
            activity = cur.fetchone()
            
            if not activity:
                raise HTTPException(status_code=404, detail="找不到該活動編號！")
            
            if activity["is_closed"]:
                raise HTTPException(status_code=400, detail="此活動已截止報名，無法填寫！")

            # 2. 寫入報名資料，重複時捕捉 UNIQUE 錯誤 (Pro版需求)
            try:
                cur.execute(
                    """
                    INSERT INTO registrations (activity_id, name, phone)
                    VALUES (%s, %s, %s);
                    """,
                    (act_id, req.name, req.phone)
                )
                conn.commit()
                return {"message": "報名成功！"}
            except psycopg2.IntegrityError:
                conn.rollback()
                raise HTTPException(status_code=400, detail="您已使用相同的姓名與電話報名過此活動！")
    finally:
        conn.close()