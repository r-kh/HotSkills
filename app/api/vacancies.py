"""
Модуль API для получения вакансий.
"""

# --- Стандартные библиотеки ---
import logging

# --- Сторонние библиотеки ---
import re
from fastapi import APIRouter, Request       # Маршрутизатор и запросы к FastAPI
from fastapi.responses import JSONResponse   # Ответы в формате JSON (для API)
from asyncpg.exceptions import PostgresError

# --- Модули проекта ---
from app.core.config import CACHE_TTL_30_MIN
from app.core.helpers import get_cache, set_cache



router = APIRouter()

# --- API: вакансии ---
@router.get("/vacancies", response_class=JSONResponse)
async def get_vacancies(request: Request, search: str | None = None):
    """
    Возвращает JSON с вакансиями

    Пример ответа на фронт:
    {
        "vacancies": [
            {"id": 135021315, "name": "Python",    "Создана": "2026-07-08", "responses": 351, "salary": [1000, null] },
            {"id": 135021315, "name": "FastAPI",   "Создана": "2026-07-08", "responses": 351, "salary": [1000, 2000] },
            {"id": 135021316, "name": "Backend",   "Создана": "2026-07-07", "responses": 120, "salary": [null, 3000] },
            {"id": 135021317, "name": "Developer", "Создана": "2026-07-06", "responses": 500, "salary":         null },
            ...]
    }
    """

    # Получаем доступ к пулам соединений с БД и Redis
    postgresql = request.app.state.db_pool
    redis      = request.app.state.redis_pool


    # --- Формируем имя ключа по которому будем искать данные в Redis ---
    if search:
        имя_ключа_кэш_данных = f"vacancies:{search.strip().lower()}"
    else:
        имя_ключа_кэш_данных = "vacancies:no_description"



    # --- Пробуем достать кэш по этому ключу ---
    данные_с_кэша = await get_cache(redis, имя_ключа_кэш_данных)

    if данные_с_кэша is not None:
        logging.info("Берём вакансии из кэша")
        return JSONResponse(content=данные_с_кэша)



    # --- Если кэша нет - то нужно взять все вакансии с параметрами из Redis если есть, или из БД (и заодно закешировать их в Redis), выполнить фильтрацию, закешировать и вернуть пользователю
    # проверяем закэшированы ли вакансии с description

    закэшированые_вакансии_с_description = await get_cache(redis,"vacancies")

    # если не кэшированы идем в PostgreSQL за ними
    if закэшированые_вакансии_с_description is None:
        try:
            async with postgresql.acquire() as conn:

                # получаем данные
                rows = await conn.fetch("""SELECT id, name, employer, Создана, responses, labor_contract, salary, description FROM vacancies;""")

                # нам понадобится делать 2 кэша, 1 со всеми параметрами для поиска, 2 без description для быстрой передачи пользователю
                вакансии_с_description = {"vacancies": []}
                вакансии_без_description = {"vacancies": []}
                # Проходимся по всем вакансиям
                for row in rows:

                    вакансия = {
                        "id"             : row["id"],
                        "name"           : row["name"],
                        "Работодатель"   : row["employer"],
                        "Создана"        : row["Создана"].isoformat(),
                        "responses"      : row["responses"],
                        "labor_contract" : row["labor_contract"],
                        "salary"         : row["salary"]}

                    вакансии_без_description["vacancies"].append(вакансия)
                    вакансии_с_description["vacancies"].append(вакансия | {"description": row["description"]})

            # кэшируем полученные вакансии в Redis на 30 минут с ключом "vacancies"
            await set_cache(redis, "vacancies", вакансии_с_description, expire=CACHE_TTL_30_MIN)
            await set_cache(redis, "vacancies:no_description", вакансии_без_description, expire=CACHE_TTL_30_MIN)
            # если нам изначально нужны были все вакансии без description, то можно их уже возвращать
            if имя_ключа_кэш_данных == "vacancies:no_description":
                return JSONResponse(content=вакансии_без_description)

        except PostgresError as e:
            logging.error("Ошибка при запросе к базе данных (vacancies): %s", e)
            return JSONResponse(status_code=500, content={"error": str(e)})


    # Поддержка запросов вида "Go OR Golang"
    ключевые_слова_для_поиска = [q.strip().lower() for q in search.split("OR")]

    вакансии = закэшированые_вакансии_с_description or вакансии_с_description

    def match_text(text: str, query: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(query)}(?!\w)", text.lower()) is not None

    вакансии_по_поиску_без_description = {
        "vacancies": [
            {key: value for key, value in vacancy.items() if key != "description"}
            for vacancy in вакансии["vacancies"]
            if any(match_text(vacancy["name"], ключевое_слово) or match_text(vacancy["description"], ключевое_слово)
                   for ключевое_слово in ключевые_слова_для_поиска)]}


    await set_cache(redis, имя_ключа_кэш_данных, вакансии_по_поиску_без_description, expire=CACHE_TTL_30_MIN)

    return JSONResponse(content=вакансии_по_поиску_без_description)
