import asyncpg                                              # Работа с PostgreSQL (асинхронно)
import json                                                 # Сериализация
import logging                                              # Отслеживание работы + диагностика проблем
import os                                                   # Работа с переменными окружения
import redis.asyncio as redis                               # Кэширование часто запрашиваемых данных (асинхронно)
import uvicorn                                              # ASGI сервер (Asynchronous Server Gateway Interface)

from contextlib import asynccontextmanager                  # для запуска/завершения FastAPI
from fastapi import FastAPI, Request                        # FastAPI и Request для Jinja
from fastapi.responses import HTMLResponse, JSONResponse    # Ответы сервера
from fastapi.staticfiles import StaticFiles                 # Подключение /static папки
from fastapi.templating import Jinja2Templates              # Рендер HTML-шаблонов с динамическими данными (для lang.html)
from jinja2 import Environment, FileSystemLoader            # Шаблонизатор Jinja2 (HTML)


# --- Конфигурация базы данных (берётся из переменных окружения) ---
DB_CONFIG = {
    "host"      : os.getenv("DB_HOST"),
    "database"  : os.getenv("DB_NAME"),
    "user"      : os.getenv("DB_USER"),
    "password"  : os.getenv("DB_PASSWORD"),
    "ssl"       : os.getenv("DB_SSL") == "True"
}


# --- Жизненный цикл приложения FastAPI
@asynccontextmanager
#   @asynccontextmanager превращает функцию lifespan в асинхронный контекстный менеджер,
#   это позволяет FastAPI управлять ресурсами на старте и завершении (иначе startup/shutdown не сработают)
async def lifespan(app: FastAPI):

    # --- Инициализация ресурсов (Startup) ---

    # Создание и настройка пула соединений с БД (я в RAM ограничен, поставил пока 4, но можно попробовать больше, 1 сессия БД = ~ work_mem + temp_buffers)
    app.state.db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=4)

    # Подключение к Redis (для кэширования и быстрого доступа к данным Redis)
    app.state.redis_pool = await redis.from_url(os.getenv("REDIS_HOST"))

    # Загружаем языки один раз при запуске и сохраняем в app.state
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT code, name, color FROM programming_languages ORDER BY id")
        # Сохраняем как список словарей
        app.state.languages = [{"code": row["code"], "name": row["name"], "color": row["color"]} for row in rows]


    # --- тут FastAPI начинает работать ---
    yield  # передача управления FastAPI и запуск сервера


    # --- Очистка ресурсов (Shutdown) ---

    # Закрытие пула соединений с БД при завершении приложения (иначе соединения с БД останутся открытыми -> утечка ресурсов)
    await app.state.db_pool.close()

    # Закрытие соединения с Redis при завершении приложения (иначе Redis-соединение останется активным -> утечка соединений и потенциальные ошибки)
    await app.state.redis_pool.close()


# --- Создаем экземпляр приложения (пока без доп.параметров title, description, version..., потом может добавлю)
app = FastAPI(lifespan=lifespan)


# --- Подключаем статические файлы (/static) и шаблоны (HTML) в FastAPI-приложение ---
app.mount("/static", StaticFiles(directory=os.getenv("STATIC_DIR")), name="static") # подключение CSS, JS, изображений
templates = Jinja2Templates(env=Environment(loader=FileSystemLoader(os.getenv("TEMPLATES_DIR")))) # шаблоны HTML (через Jinja2) (надо попробовать переехать на React/Vue)


# --- Главная страница сайта (index.html) ---
@app.get("/", response_class=HTMLResponse)
# Ловим GET запрос по адресу "/" и отвечаем HTML'ом
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Обработчик GET-запроса для страницы языка по коду (lang.html) ---
@app.get("/{lang}", response_class=HTMLResponse)
# ловим URL с переменной lang (код языка), передаём её в асинхронную функцию-обработчик и возвращаем HTML
async def show_lang_page(request: Request, lang: str):

    async with app.state.db_pool.acquire() as conn:    # Получаем соединение из пула БД (иначе запрос не отправить)
        # ищем язык (name, code) по коду (lang)
        row = await conn.fetchrow(
            "SELECT code, name FROM programming_languages WHERE code = $1",
            lang.lower()    # на случай, если пользователь пришлёт /Python или /JAVA
        )

    # Если язык не найден — 404
    if not row:
        return HTMLResponse(content="Страница не найдена", status_code=404)

    # Возвращаем отрендереный шаблон lang.html (с code и name)
    return templates.TemplateResponse("lang.html", {
        "request": request,
        "code"   : row["code"],  # для логотипов/таблиц/графиков
        "name"   : row["name"],  # для правильного отображения языка на страницах
    })


# --- API: данные по зарплатам ---
@app.get("/api/salaries")
# Обработчик GET-запроса по маршруту /api/salaries
async def get_salaries():

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = app.state.db_pool
    redis_pool = app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "salaries"
    cached = await redis_pool.get("salaries")
    # Если кеш есть
    if cached:
        logging.info("Возвращаем данные из кеша")       # Логируем, что используются кэшированные данные из Redis
        return JSONResponse(content=json.loads(cached)) # Отдаём кеш в виде JSON

    # Если кеша нет
    try:
        # Получаем соединение с базой данных
        async with db_pool.acquire() as conn:

            # Достаём одну (последнюю по дате) запись с зарплатами (DESC/DESCENDING значит «по убыванию»)
            salaries_last_row = await conn.fetchrow("SELECT * FROM salaries ORDER BY date DESC LIMIT 1")

    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка при запросе к базе данных: {e}")         # Логируем ошибку (иначе не узнаем о проблемах)
        return JSONResponse(status_code=500, content={"error": str(e)}) # Отправляем клиенту ошибку 500 (иначе клиент не узнает о проблеме)

    # salaries_last_row - это объект asyncpg.Record, нужно конвертировать в словарь чтобы потом получилось сериализовать в JSON (иначе упадёт с ошибкой)
    salaries_last_row_dict = dict(salaries_last_row) if salaries_last_row else {}

    # Удаляем поле date, (сейчас на фронте оно пока не нужно)
    salaries_last_row_dict.pop('date', None)

    # Сохраняем результат в Redis на 60 минут (ex=3600 секунд)
    await redis_pool.set("salaries", json.dumps(salaries_last_row_dict), ex=3600)

    # Возвращаем результат в виде JSON
    return JSONResponse(content=salaries_last_row_dict)


# --- API: получение списка языков программирования ---
@app.get("/api/languages")
# Пример ответа на фронт:
# [{"code":"one_c","name":"1C","color":"#E31E24"},...]
# Обработчик GET-запроса по маршруту /api/languages
async def get_languages():

    # Получаем доступ к пулам соединений с Redis
    redis_pool = app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "languages" (иначе всегда будем дергать БД)
    cached = await redis_pool.get("languages")
    # Если кеш есть
    if cached:
        logging.info("Возвращаем список языков из кеша") # Логируем, что используются кэшированные данные из Redis
        return JSONResponse(content=json.loads(cached))  # Отдаём кеш в виде JSON

    # Если нет — берём из загруженного списка
    languages = app.state.languages

    # Сохраняем результат в кеш Redis бессрочно, языки не часто обновляются (иначе каждый запрос будет идти в БД)
    # (если я добавлю новые языки, я перезапущу руками)
    await redis_pool.set("languages", json.dumps(languages))

    # Возвращаем данные в виде JSON
    return JSONResponse(content=languages)


# --- API: данные по вакансиям ---
@app.get("/api/vacancy-statistics", response_class=JSONResponse)
@app.get("/api/vacancy-statistics/{query}", response_class=JSONResponse)
# Пример ответа на фронт:
# {            "python": {"daily": [["2025-05-22", [1200, 1600]], ..], "hourly": [["2025-05-23 20:00:00", [1100, 1500]], ..]},
#  "software_developer": {"daily": [["2025-05-22",       14500 ], ..], "hourly": [["2025-05-23 20:00:00",       14700 ], ..}}
# Обработчик GET-запроса по маршруту /api/vacancy-statistics
async def get_vacancy_statistics(query: str = None):

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

    # сбор данных по дням
    async def fetch_daily(conn, table, columns):
        sql_query = f"""
            SELECT DISTINCT ON (DATE(date)) DATE(date) AS date, {columns}
            FROM {table}
            WHERE date >= NOW() - INTERVAL '31 days'
            ORDER BY DATE(date), date DESC;
        """
        return await conn.fetch(sql_query)

    # Пробуем сначала получить кешированные данные из Redis по ключу "vacancy-statistics"
    cache_key = f"vacancy-statistics:{query or 'all'}"
    cached_data = await redis_pool.get(cache_key)

    # Если кеш есть
    if cached_data:
        logging.info("Возвращаем данные из кеша")             # Логируем, что используются кэшированные данные из Redis
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

            # Если query — software_developer или не задан, собираем статистику по software_developer
            if query in ["software_developer", None]:
                # Добавляем статистику по профессии в общий результат
                result.update(await get_stat("vacancies_statistics.professions", ["software_developer"]))

        # --- Кешируем сформированный результат в Redis на 1 час (3600 сек) ---
        await redis_pool.set(cache_key, json.dumps(result), ex=3600) # Сохраняем результат для быстрого доступа, иначе каждый запрос будет грузить БД
        # --- Возвращаем ответ клиенту ---
        return JSONResponse(content=result)  # Отдаем собранные данные в JSON формате, иначе клиент не получит ответ

    except Exception as e:
        logging.error(f"Ошибка при получении статистики: {e}")          # Логируем ошибку (иначе не узнаем о проблемах)
        return JSONResponse(status_code=500, content={"error": str(e)}) # Отправляем клиенту ошибку 500 (иначе клиент не узнает о проблеме)


# --- Запуск при старте ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
