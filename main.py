from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="活動報名平台 - 完整版")

# 資料庫連線配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "010030"  # 👈 請填入本機 PostgreSQL 密碼
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

# 1. 新增新的活動
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
            return {"message": "活動新增成功！", "id": act_id}
    finally:
        conn.close()

# 2. 列出活動清單 + 顯示目前報名人數 (Pro 版: COUNT 統計)
@app.get("/api/activities")
def list_activities():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    a.id, a.title, a.description, a.event_date, a.is_closed,
                    COUNT(r.id) AS registered_count
                FROM activities a
                LEFT JOIN registrations r ON a.id = r.activity_id
                GROUP BY a.id
                ORDER BY a.id DESC;
            """
            cur.execute(query)
            return cur.fetchall()
    finally:
        conn.close()

# 3. 報名活動 (Pro 版: 檢查同名且同電話重複報名、檢查是否已截止)
@app.post("/api/activities/{act_id}/register")
def register_activity(act_id: int, req: RegisterRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 檢查活動存在與是否已截止
            cur.execute("SELECT is_closed FROM activities WHERE id = %s;", (act_id,))
            activity = cur.fetchone()
            if not activity:
                raise HTTPException(status_code=404, detail="找不到該活動！")
            if activity["is_closed"]:
                raise HTTPException(status_code=400, detail="此活動已截止報名，無法填寫！")

            # 檢查同名且同電話重複報名
            cur.execute(
                "SELECT id FROM registrations WHERE activity_id = %s AND name = %s AND phone = %s;",
                (act_id, req.name, req.phone)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="您已報名過此活動（同姓名與電話）！請勿重複報名。")

            # 寫入報名資料
            cur.execute(
                "INSERT INTO registrations (activity_id, name, phone) VALUES (%s, %s, %s);",
                (act_id, req.name, req.phone)
            )
            conn.commit()
            return {"message": "報名成功！"}
    finally:
        conn.close()

# 4. 截止報名功能 (Pro 版)
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

# 5. 查看特定活動的報名清單 (基本款)
@app.get("/api/activities/{act_id}/registrations")
def get_activity_registrations(act_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, phone, created_at 
                FROM registrations 
                WHERE activity_id = %s 
                ORDER BY created_at ASC;
                """,
                (act_id,)
            )
            return cur.fetchall()
    finally:
        conn.close()