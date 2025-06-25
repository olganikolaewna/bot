import asyncpg 
from aiogram import types
import random
import string
from datetime import datetime, timedelta

async def create_db_connection():
    return await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="shortl-db",
        host="db"
    )

async def create_table():
    try:
        conn = await create_db_connection()
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                username TEXT
            );
            
            CREATE TABLE IF NOT EXISTS links (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                original_url TEXT,
                short_code TEXT UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS clicks (
                id SERIAL PRIMARY KEY,
                short_code TEXT NOT NULL,
                user_ip TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
    ''')
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
        raise  
    finally:
        if conn:
            await conn.close()



async def reg_user(user_id: int, username: str):
    conn = None
    try:
        conn = await create_db_connection()
        try:
            await conn.execute('''
                INSERT INTO users (user_id, username)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username)
        except:
            await create_table()
            await conn.execute('''
                INSERT INTO users (user_id, username)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username)
    finally:
        if conn:
            await conn.close()


def gen_short_code(url: str) -> str:
    characters = string.ascii_letters + string.digits
    short_url = "".join(random.choice(characters) for _ in range(6))
    return short_url


async def save_link(user_id: int, original_url: str) -> str:
    conn = await create_db_connection()
    try:
        for _ in range(5):
            short_code = gen_short_code(original_url)
            try:
                result = await conn.execute('''
                    INSERT INTO links (user_id, original_url, short_code)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (short_code) DO NOTHING
                ''', user_id, original_url, short_code)

                if result and "INSERT" in result:
                    return short_code 
            except Exception as e:
                print(f"Ошибка при сохранении ссылки: {e}")
                await create_table()

        
        raise Exception("Не удалось сгенерировать уникальный short_code")
    finally:
        await conn.close()



async def get_links(user_id: int):
    conn = await create_db_connection()
    try:
        rows = await conn.fetch('''
            SELECT original_url, short_code FROM links
            WHERE user_id = $1
        ''', user_id)
        return rows
    finally:
        await conn.close()

#Временная статистика
async def get_stat(short_code: str):
    conn = await create_db_connection()
    try:
        all_clicks = await conn.fetchval(
            "SELECT COUNT(*) FROM clicks WHERE short_code = $1", short_code
        )
        uni_users = await conn.fetchval(
             "SELECT COUNT(DISTINCT user_ip) FROM clicks WHERE short_code = $1", short_code
         )
        return all_clicks, uni_users
    finally:
        await conn.close()




#Новая статистика
async def get_statistics(stat_type: str, short_code: str) -> str:
    conn = await create_db_connection()
    try:
        now = datetime.utcnow()

        if stat_type == "day":
            since = now - timedelta(days=7)
            group_by = "DATE_TRUNC('day', timestamp)"
            label_format = 'YYYY-MM-DD'

        elif stat_type == "week":
            since = now - timedelta(weeks=4)
            group_by = "DATE_TRUNC('week', timestamp)"
            label_format = '"Week "IW, YYYY'

        elif stat_type == "month":
            since = now - timedelta(days=365)
            group_by = "DATE_TRUNC('month', timestamp)"
            label_format = 'Mon YYYY'
            
        else:
            return "❌ Неверный период."

        query = f"""
            SELECT
                TO_CHAR({group_by}, '{label_format}') AS stat_type,
                COUNT(*) AS total,
                COUNT(DISTINCT user_ip) AS unique
            FROM clicks
            WHERE short_code = $1 AND timestamp >= $2
            GROUP BY stat_type
            ORDER BY stat_type
        """
        rows = await conn.fetch(query, short_code, since)

        if not rows:
            return "Нет переходов за этот период."


        return [(row['stat_type'], row['total'], row['unique']) for row in rows]

    finally:
        await conn.close()


#Удаление ссылки
async def delete_link(short_code: str, user_id: int):
    conn = await create_db_connection()

    try:
        await conn.execute('''
            DELETE FROM links WHERE short_code = $1 AND user_id = $2
        ''', short_code, user_id)
        await conn.execute('''
            DELETE FROM clicks WHERE short_code = $1
        ''', short_code)
    finally:
        await conn.close()