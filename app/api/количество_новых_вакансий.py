import logging
from asyncpg.exceptions import PostgresError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.config import CACHE_TTL_DAY
from app.core.helpers import get_cache, set_cache

router = APIRouter()

@router.get("/new-vacancies-statistics", response_class=JSONResponse)
async def get_new_vacancies_statistics(request: Request):
    """
    Возвращает JSON с ежедневным количеством новых вакансий (Россия и Москва).
    """
    db_pool = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool

    cache_key = "new-vacancies-statistics"
    cached = await get_cache(redis_pool, cache_key)
    if cached:
        logging.info("Возвращаем данные по новым вакансиям из кеша")
        return JSONResponse(content=cached)

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT "Дата", "Россия", "Москва"
                FROM "количество_новых_вакансий"
                WHERE "Дата" >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY "Дата" ASC;
            """)

        moscow_daily = [[str(r["Дата"]), r["Москва"]] for r in rows]
        russia_daily = [[str(r["Дата"]), r["Россия"]] for r in rows]

        result = {
            "moscow": {"daily": moscow_daily},
            "russia": {"daily": russia_daily}
        }

        await set_cache(redis_pool, cache_key, result, expire=CACHE_TTL_DAY)
        return JSONResponse(content=result)

    except PostgresError as e:
        logging.error("Ошибка при запросе новых вакансий: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})