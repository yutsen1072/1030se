from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="活動管理模組 - guan")

# 資料庫連線設定
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "anita0306"  # 👈 請填寫本地 PostgreSQL 密碼
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# Request 格式定義
class ActivityCreate(BaseModel):
    title: str
    description: str
    event_date: str

class RegisterRequest(BaseModel):
    name: str
    phone: str

@app.get("/")
def read_root():
    return FileResponse("index.html")

# ----------------- cai 原有的報名功能保留 -----------------
@app.post("/api/activities/{act_id}/register")
def register_activity(act_id: int, req: RegisterRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_closed FROM activities WHERE id = %s;", (act_id,))
            activity = cur.fetchone()
            if not activity:
                raise HTTPException(status_code=404, detail="找不到該活動編號！")
            if activity["is_closed"]:
                raise HTTPException(status_code=400, detail="此活動已截止報名，無法填寫！")

            try:
                cur.execute(
                    "INSERT INTO registrations (activity_id, name, phone) VALUES (%s, %s, %s);",
                    (act_id, req.name, req.phone)
                )
                conn.commit()
                return {"message": "報名成功！"}
            except psycopg2.IntegrityError:
                conn.rollback()
                raise HTTPException(status_code=400, detail="您已報名過此活動！")
    finally:
        conn.close()

# ----------------- guan 負責新增的模組：活動管理 -----------------
# 1. 發布新活動
@app.post("/api/activities")
def create_activity(data: ActivityCreate):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO activities (title, description, event_date)
                VALUES (%s, %s, %s) RETURNING id;
                """,
                (data.title, data.description, data.event_date)
            )
            act_id = cur.fetchone()["id"]
            conn.commit()
            return {"message": "活動發布成功！", "id": act_id}
    finally:
        conn.close()

# 2. 截止活動報名
@app.post("/api/activities/{act_id}/close")
def close_activity(act_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE activities SET is_closed = TRUE WHERE id = %s;", (act_id,))
            conn.commit()
            return {"message": "活動已成功截止報名！"}
    finally:
        conn.close()