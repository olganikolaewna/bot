from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
import asyncpg
import asyncio
import os

app = FastAPI()

DATABASE_CONFIG = {
    "user":"postgres",
    "password":"postgres",
    "database":"shortl-db",
    "host":"db",
    "port": 5432
}



@app.on_event("startup")
async def startup():
    for attempt in range(5):
        try:
            app.state.conn = await asyncpg.connect(**DATABASE_CONFIG)
            print("✅ Connected to DB")
            return
        except Exception as e:
            print(f"⏳ DB not ready (attempt {attempt + 1}), retrying...")
            await asyncio.sleep(2)
    raise RuntimeError("❌ Failed to connect to DB after retries.")

@app.on_event("shutdown")
async def shutdown():
    await app.state.conn.close()

@app.get("/{short_code}")
async def redirect(short_code: str, request: Request):
    conn = app.state.conn

    row = await conn.fetchrow('''
        SELECT original_url FROM links WHERE short_code = $1
    ''', short_code)
    if row:
        user_ip = request.client.host
        await conn.execute('''
            INSERT INTO clicks (short_code, user_ip)
            VALUES ($1, $2)
        ''', short_code, user_ip)
        
        return RedirectResponse(url=row["original_url"])
    raise HTTPException(status_code=404, detail = "Ссылка не найдена")