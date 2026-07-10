"""
Модуль API для получения вакансий.
"""

# --- Стандартные библиотеки ---
import logging

# --- Сторонние библиотеки ---
from fastapi import APIRouter, Request       # Маршрутизатор и запросы к FastAPI
from fastapi.responses import JSONResponse   # Ответы в формате JSON (для API)
from asyncpg.exceptions import PostgresError

# --- Модули проекта ---
from app.core.config import CACHE_TTL_30_MIN
from app.core.helpers import get_cache, set_cache



router = APIRouter()

# --- API: вакансии ---
@router.get("/vacancies", response_class=JSONResponse)
async def get_vacancies(request: Request):
    """
    Возвращает JSON с вакансиями

    Пример ответа на фронт:
    {
        "vacancies": {
            { "id" : "135021315", "name" : "Инженер-разработчик систем искусственного интеллекта" },
            { "id" : "135021316", "name" : "Python Backend Developer" },
            ...
        }
    }
    """

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool

    # --- Пробуем достать кэш ---
    cache_key = "vacancies"
    cached = await get_cache(redis_pool, cache_key)

    if cached:
        logging.info("Возвращаем вакансии из кеша")
        return JSONResponse(content=cached)

    # Если кеша нет, то достаём данные из базы
    try:
        async with db_pool.acquire() as conn:

            # получаем данные
            rows = await conn.fetch("""SELECT id, name, date, responses FROM vacancies;""")

            result = { "vacancies": [{"id": row["id"], "name": row["name"], "date": row["date"].isoformat(), "responses": row["responses"]} for row in rows] }

        # кэшируем на 1 час
        await set_cache(redis_pool, cache_key, result, expire=CACHE_TTL_30_MIN)

        return JSONResponse(content=result)

    except PostgresError as e:
        logging.error("Ошибка при запросе к базе данных (vacancies): %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
