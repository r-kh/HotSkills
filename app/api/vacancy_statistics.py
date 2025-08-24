"""
Модуль API для получения статистики вакансий.
"""

# --- Стандартные библиотеки ---
import logging                               # Отслеживание работы/диагностика проблем

# --- Сторонние библиотеки ---
from asyncpg.exceptions import PostgresError # Работа с PostgreSQL (async)
from fastapi import APIRouter, Request       # Маршрутизатор и объект запроса FastAPI
from fastapi.responses import JSONResponse   # Ответы в формате JSON (для API)

# --- Модули проекта ---
from app.core.config import CACHE_TTL_HOUR
from app.core.helpers import get_cache, set_cache

router = APIRouter()


# --- API: данные по вакансиям ---
@router.get("/vacancy-statistics", response_class=JSONResponse)
@router.get("/vacancy-statistics/{query}", response_class=JSONResponse)
async def get_vacancy_statistics(request: Request, query: str = None):
    """
    Возвращает JSON со статистикой вакансий по языкам и профессиям.
    Аргументы: query (str, optional): Конкретный язык или профессия для фильтрации.

    Пример ответа на фронт:
    {            "python":  {"daily": [["2025-05-22",          [1200,  1600]], ..],
                            "hourly": [["2025-05-23 20:00:00", [1100,  1500]], ..]},
     "software_developer":  {"daily": [["2025-05-22",                 14500 ], ..],
                            "hourly": [["2025-05-23 20:00:00",        14700 ], ..}}
    """

    # Получаем доступ к пулам соединений с БД и Redis и список языков
    db_pool    = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool
    langs      = [lang["code"] for lang in request.app.state.languages]

    # сбор данных по часам
    async def fetch_hourly(conn, table, columns):
        sql_query = f"""
            SELECT date, {columns}
            FROM {table}
            WHERE date >= NOW() - INTERVAL '24 hours'
            ORDER BY date ASC;
        """
        return await conn.fetch(sql_query)

    # сбор данных по дням (берётся самая поздняя запись с каждого дня)
    async def fetch_daily(conn, table, columns):
        sql_query = f"""
            SELECT date::date AS date, {columns}
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY date::date ORDER BY date DESC) AS rn
                FROM {table}
                WHERE date >= NOW() - INTERVAL '30 days'
            ) sub
            WHERE rn = 1
            ORDER BY date;
        """
        return await conn.fetch(sql_query)

    # Пробуем сначала получить кешированные данные из Redis по ключу "vacancy-statistics"
    cache_key = f"vacancy-statistics:{query or 'all'}"
    cached_statistics = await get_cache(redis_pool, cache_key)

    # Если кеш есть
    if cached_statistics:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=cached_statistics)  # Отдаём кеш в виде JSON


    # Если кеша нет
    try:
        # Получаем соединение с базой данных
        async with db_pool.acquire() as conn:

            # Создаём пустой словарь для хранения итоговой статистики
            result = {}

            # Функция для получения статистики из таблицы по указанным колонкам
            async def get_stat(table, columns):

                # Запрашиваем ежедневные и почасовые данные из базы по указанным колонкам
                daily  = await fetch_daily (conn, table, ', '.join(columns))
                hourly = await fetch_hourly(conn, table, ', '.join(columns))

                # Создаём словарь для хранения статистики по каждой колонке
                statistics = {}

                # Проходим по каждой колонке (например, языку программирования или профессии)
                for column in columns:
                    # Если query задан и не совпадает с текущей колонкой, пропускаем её
                    if query and query != column:
                        continue

                    # Заполняем статистику для выбранной колонки по дням и часам
                    statistics[column] = {
                        # Формируем список пар [дата, значение] для ежедневных данных
                        "daily": [[str(row["date"]), row[column]] for row in daily],
                        # Формируем список пар [дата, значение] для почасовых данных
                        "hourly": [[str(row["date"]), row[column]] for row in hourly],
                    }

                # Возвращаем словарь со статистикой по всем нужным колонкам
                return statistics

            # Если query совпадает с одним из языков или не задан, собираем статистику по языкам
            if query in langs or query is None:
                # Добавляем статистику по языкам в общий результат
                result.update(await get_stat("vacancies_statistics.languages", langs))

            # Если query не задан или равен software_developer → статистика по software_developer
            if query in ["software_developer", None]:
                # Добавляем статистику по профессии в общий результат
                result.update(
                    await get_stat("vacancies_statistics.professions", ["software_developer"]))

        # --- Кешируем сформированный результат в Redis на 1 час (3600 сек) ---
        # Сохраняем результат для быстрого доступа, иначе каждый запрос будет грузить БД
        await set_cache(redis_pool, cache_key, result, expire=CACHE_TTL_HOUR)

        # --- Возвращаем ответ клиенту ---
        # Отдаем собранные данные в JSON формате, иначе клиент не получит ответ
        return JSONResponse(content=result)

    except PostgresError as e:

        # Логируем ошибку (иначе не узнаем о проблемах)
        logging.error("Ошибка при запросе к базе данных: %s", e)

        # Отправляем клиенту ошибку 500 (иначе клиент не узнает о проблеме)
        return JSONResponse(status_code=500, content={"error": str(e)})
