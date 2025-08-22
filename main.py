"""
FastAPI-приложение для отображения информации о динамике вакансий, зарплатах,
языках программирования и навыках.

Модуль включает:

- Инициализацию и настройку FastAPI с асинхронным жизненным циклом.
- Подключение к PostgreSQL через asyncpg и к Redis для кэширования.
- Подключение статических файлов и шаблонов Jinja2 для фронтенда.
- REST API эндпоинты:
    - "/" — главная страница (index.html)
    - "/{lang}" — страница конкретного языка программирования (lang.html)
    - "/api/salaries" — данные по зарплатам (JSON)
    - "/api/languages" — список языков программирования (JSON)
    - "/api/vacancy-statistics" — статистика вакансий по языкам и профессиям (JSON)

Используемые технологии и библиотеки:
- FastAPI
- Jinja2
- asyncpg (PostgreSQL)
- redis.asyncio
- uvicorn

Примечания:
- Все эндпоинты асинхронные.
- Данные кэшируются в Redis для ускорения повторных запросов.
- Статические файлы и шаблоны подгружаются из директорий, указанных в переменных окружения.
"""

# --- Стандартные библиотеки ---
import json                                      # Сериализация
import logging                                   # Отслеживание работы/диагностика проблем
from contextlib import asynccontextmanager       # для запуска/завершения FastAPI

# --- Сторонние библиотеки ---
import asyncpg                                   # Работа с PostgreSQL (async)
import uvicorn                                   # Сервер ASGI(Asynhronus Server Gateway Interface)
from fastapi import FastAPI, Request             # FastAPI и Request для Jinja
from fastapi.responses import HTMLResponse       # Ответы в формате HTML-страниц
from fastapi.responses import JSONResponse       # Ответы в формате JSON (для API)
from fastapi.staticfiles import StaticFiles      # Подключение /static папки
from fastapi.templating import Jinja2Templates   # Генератор HTML-страниц с динамическими данными
from jinja2 import Environment, FileSystemLoader # Настройка Jinja2 для рендера HTML-шаблонов

# --- Модули проекта ---
from config import STATIC_DIR, TEMPLATES_DIR, CACHE_TTL_HOUR, CACHE_TTL_DAY, CACHE_TTL_NO_EXPIRY
from db import init_db_pool, close_db_pool, init_redis_pool, close_redis_pool


# --- Жизненный цикл приложения FastAPI
@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Асинхронный контекстный менеджер для запуска и завершения FastAPI приложения.

    @asynccontextmanager превращает функцию lifespan в асинхронный контекстный менеджер,
    это позволяет FastAPI управлять ресурсами на старте и завершении (замена startup/shutdown)
    """

    # --- Инициализация ресурсов (Startup) ---

    # Инициализация пулов соединений с БД PostgreSQL + Redis(кэширование/быстрый доступ к данным)
    application.state.db_pool = await init_db_pool()
    application.state.redis_pool = await init_redis_pool()

    # Загружаем языки один раз при запуске и сохраняем в app.state
    async with application.state.db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT code, name, color FROM programming_languages ORDER BY id")
        # Сохраняем как список словарей
        application.state.languages = [
            {"code": row["code"], "name": row["name"], "color": row["color"]}
            for row in rows
        ]


    # --- тут FastAPI начинает работать ---
    yield  # передача управления FastAPI и запуск сервера


    # --- Очистка ресурсов (Shutdown) ---

    # Закрытие пула соединений с БД и Redis при завершении приложения
    # (иначе соединения с БД и Redis останутся открытыми -> утечка ресурсов)
    await close_db_pool(application.state.db_pool)
    await close_redis_pool(application.state.redis_pool)


# --- Создаем экземпляр приложения (пока без доп.параметров title, description, version...)
app = FastAPI(lifespan=lifespan)


# --- Подключаем статические файлы (/static) и шаблоны (HTML) в FastAPI-приложение ---

# подключение CSS, JS, изображений
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# шаблоны HTML (через Jinja2) (надо попробовать переехать на React/Vue)
templates = Jinja2Templates(env=Environment(loader=FileSystemLoader(TEMPLATES_DIR)))


# --- Главная страница сайта (index.html) ---
@app.get("/", response_class=HTMLResponse)
# Ловим GET запрос по адресу "/" и отвечаем HTML'ом
async def index(request: Request):
    """Главная страница сайта."""

    return templates.TemplateResponse("index.html", {"request": request})


# --- Обработчик GET-запроса для страницы языка по коду (lang.html) ---
@app.get("/{lang}", response_class=HTMLResponse)
async def show_lang_page(request: Request, lang: str):
    """
    Возвращает страницу языка с актуальными навыками и статистикой.

    Ловим URL с переменной lang (код языка),
    передаём её в асинхронную функцию-обработчик и возвращаем HTML
    """

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = app.state.db_pool
    redis_pool = app.state.redis_pool

    # Получаем соединение с базой данных
    async with db_pool.acquire() as conn:
        # ищем язык (name, code) по коду (lang)
        row = await conn.fetchrow(
            "SELECT code, name FROM programming_languages WHERE code = $1",
            lang.lower()    # на случай, если пользователь пришлёт /Python или /JAVA
        )

        # Если язык не найден — возвращаем ошибку 404 (страница не существует)
        if not row:
            return HTMLResponse(content="Страница не найдена", status_code=404)

        skills = []  # список навыков

        # Формируем ключ для Redis по коду языка, чтобы хранить/доставать кэшированные навыки
        # (Без ключа не сможем получить/записать данные в Redis)
        cache_key = f"skills:{row['code']}"

        # Пробуем сначала получить кешированные данные из Redis по ключу
        # (если убрать, будем постоянно читать из БД)
        cached_skills = await redis_pool.get(cache_key)
        # Если кеш есть
        if cached_skills:
            # Логируем, что используются кэшированные данные из Redis
            logging.info("Возвращаем данные из кеша")
            # Если кэш найден — десериализуем JSON в Python-объект (список или словарь)
            skills = json.loads(cached_skills)

        else:
            # Если в кэше нет — читаем из базы последние свежие данные для языка
            skill_row = await conn.fetchrow(
                f"SELECT {row['code']} FROM hot_skills ORDER BY date DESC LIMIT 1"
            )

            if skill_row and skill_row[row["code"]]:

                # Если данные есть, десериализуем из JSON
                skills = json.loads(skill_row[row["code"]])

                # Кэшируем полученные данные в Redis на 24 часа (данные обновляются раз в день)
                await redis_pool.set(cache_key, json.dumps(skills), ex=CACHE_TTL_DAY)
            else:
                # Если данных нет — оставляем пустым,
                # чтобы не сломать шаблон и корректно обработать отсутствие данных
                skills = []

    # Возвращаем отрендереный шаблон lang.html (с code и name)
    return templates.TemplateResponse("lang.html", {
        "request": request,
        # объект HTTP-запроса, который пришёл от клиента (браузера или другого клиента)
        # Он содержит всю информацию о текущем запросе: URL, заголовки, параметры, куки, тело и т.д
        "code"   : row["code"],  # для логотипов/таблиц/графиков
        "name"   : row["name"],  # для правильного отображения языка на страницах
        "skills" : skills        # навыки и их частота упоминаний (в пилюлях на странице языка)
    })


# --- API: данные по зарплатам ---
@app.get("/api/salaries")
# Обработчик GET-запроса по маршруту /api/salaries
async def get_salaries():
    """Возвращает JSON с последними данными по зарплатам."""

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = app.state.db_pool
    redis_pool = app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "salaries"
    cached = await redis_pool.get("salaries")
    # Если кеш есть
    if cached:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=json.loads(cached)) # Отдаём кеш в виде JSON

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
    await redis_pool.set("salaries", json.dumps(salaries_last_row_dict), ex=CACHE_TTL_HOUR)

    # Возвращаем результат в виде JSON
    return JSONResponse(content=salaries_last_row_dict)


# --- API: получение списка языков программирования ---
@app.get("/api/languages")
async def get_languages():
    """
    Возвращает JSON со списком языков программирования.
    Пример ответа на фронт:
    [{"code":"one_c","name":"1C","color":"#E31E24"},...]
    """

    # Получаем доступ к пулам соединений с Redis
    redis_pool = app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "languages"
    # (иначе всегда будем дергать БД)
    cached = await redis_pool.get("languages")
    # Если кеш есть
    if cached:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем список языков из кеша")
        return JSONResponse(content=json.loads(cached))  # Отдаём кеш в виде JSON

    # Если нет — берём из загруженного списка
    languages = app.state.languages

    # Сохраняем результат в кеш Redis бессрочно, языки не часто обновляются
    # (иначе каждый запрос будет идти в БД)
    # (если я добавлю новые языки, я перезапущу руками)
    await redis_pool.set("languages", json.dumps(languages), ex=CACHE_TTL_NO_EXPIRY)

    # Возвращаем данные в виде JSON
    return JSONResponse(content=languages)


# --- API: данные по вакансиям ---
@app.get("/api/vacancy-statistics", response_class=JSONResponse)
@app.get("/api/vacancy-statistics/{query}", response_class=JSONResponse)
async def get_vacancy_statistics(query: str = None):
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
    db_pool    = app.state.db_pool
    redis_pool = app.state.redis_pool
    langs      = [lang["code"] for lang in app.state.languages]

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
    cached_data = await redis_pool.get(cache_key)

    # Если кеш есть
    if cached_data:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=json.loads(cached_data))  # Отдаём кеш в виде JSON


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
        await redis_pool.set(cache_key, json.dumps(result), ex=CACHE_TTL_HOUR)

        # --- Возвращаем ответ клиенту ---
        # Отдаем собранные данные в JSON формате, иначе клиент не получит ответ
        return JSONResponse(content=result)

    except asyncpg.exceptions.PostgresError as e:

        # Логируем ошибку (иначе не узнаем о проблемах)
        logging.error("Ошибка при запросе к базе данных: %s", e)

        # Отправляем клиенту ошибку 500 (иначе клиент не узнает о проблеме)
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- Запуск при старте ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info",
        # workers=2, # При 2 воркерах на текущем железе происходит нехватка RAM — приложение падает
    )
