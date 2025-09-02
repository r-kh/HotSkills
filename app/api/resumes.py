# --- Стандартные библиотеки ---
import logging

# --- Сторонние библиотеки ---
from asyncpg.exceptions import PostgresError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

# --- Модули проекта ---
from app.core.config import CACHE_TTL_HOUR
from app.core.helpers import get_cache, set_cache

router = APIRouter()


# --- API: данные по резюме ---
@router.get("/resume-statistics", response_class=JSONResponse)
async def get_resume_statistics(request: Request):
    """
    Возвращает JSON со статистикой резюме (daily + hourly).

    Пример ответа на фронт:
    {
        "resumes": {
            "daily":  [["2025-05-22",          5400], ...],
            "hourly": [["2025-05-23 20:00:00", 5600], ...]
        }
    }
    """

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool

    # сбор данных по часам
    async def fetch_hourly(conn):
        sql_query = """
            SELECT date, "software_developer"
            FROM resumes
            WHERE date >= NOW() - INTERVAL '24 hours'
            ORDER BY date ASC;
        """
        return await conn.fetch(sql_query)

    # сбор данных по дням (берём самую позднюю запись на каждый день)
    async def fetch_daily(conn):
        sql_query = """
            SELECT date::date AS date, "software_developer"
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY date::date ORDER BY date DESC) AS rn
                FROM resumes
                WHERE date >= NOW() - INTERVAL '30 days'
            ) sub
            WHERE rn = 1
            ORDER BY date;
        """
        return await conn.fetch(sql_query)

    # --- Пробуем достать кэш ---
    cache_key = "resume-statistics"
    cached_statistics = await get_cache(redis_pool, cache_key)

    if cached_statistics:
        logging.info("Возвращаем данные по резюме из кеша")
        return JSONResponse(content=cached_statistics)

    try:
        async with db_pool.acquire() as conn:
            # получаем данные
            daily  = await fetch_daily(conn)
            hourly = await fetch_hourly(conn)

            # приводим к нужному формату
            result = {
                "resumes": {
                    "daily":  [[str(row["date"]), row["software_developer"]] for row in daily],
                    "hourly": [[str(row["date"]), row["software_developer"]] for row in hourly],
                }
            }

        # кэшируем на 1 час
        await set_cache(redis_pool, cache_key, result, expire=CACHE_TTL_HOUR)

        return JSONResponse(content=result)

    except PostgresError as e:
        logging.error("Ошибка при запросе к базе данных (resumes): %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
