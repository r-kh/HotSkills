"""
Модуль API для работы с данными о зарплатах.
"""

# --- Стандартные библиотеки ---
import logging                             # Отслеживание работы/диагностика проблем

# --- Сторонние библиотеки ---
import asyncpg                             # Работа с PostgreSQL (async)
from fastapi import APIRouter, Request     # Маршрутизатор и объект запроса FastAPI
from fastapi.responses import JSONResponse # Ответы в формате JSON (для API)

# --- Модули проекта ---
from app.core.config import CACHE_TTL_HOUR
from app.core.helpers import get_cache, set_cache

router = APIRouter()

# --- API: данные по зарплатам ---
@router.get("/salaries")
# Обработчик GET-запроса по маршруту /salaries
async def get_salaries(request: Request):
    """Возвращает JSON с последними данными по зарплатам."""

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "salaries"
    cached_salaries = await get_cache(redis_pool, "salaries")
    # Если кеш есть
    if cached_salaries:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=cached_salaries) # Отдаём кеш в виде JSON

    # Если кеша нет
    try:
        # Получаем соединение с базой данных
        async with db_pool.acquire() as conn:

            # Достаём одну (последнюю по дате) запись с зарплатами (DESC/DESCENDING - по убыванию)
            salaries_last_row = await conn.fetchrow(
                "SELECT * FROM salaries ORDER BY date DESC LIMIT 1"
            )

    except asyncpg.exceptions.PostgresError as e:

        # Логируем ошибку (иначе не узнаем о проблемах)
        logging.error("Ошибка при запросе к базе данных: %s", e)

        # Отправляем клиенту ошибку 500 (иначе клиент не узнает о проблеме)
        return JSONResponse(status_code=500, content={"error": str(e)})


    # salaries_last_row - это объект asyncpg.Record,
    # нужно конвертировать в словарь чтобы потом получилось сериализовать в JSON
    # (иначе упадёт с ошибкой)
    salaries_last_row_dict = dict(salaries_last_row) if salaries_last_row else {}

    # Удаляем поле date, (сейчас на фронте оно пока не нужно)
    salaries_last_row_dict.pop('date', None)

    # Сохраняем результат в Redis на 60 минут (ex=3600 секунд)
    await set_cache(redis_pool, "salaries", salaries_last_row_dict, expire=CACHE_TTL_HOUR)

    # Возвращаем результат в виде JSON
    return JSONResponse(content=salaries_last_row_dict)
