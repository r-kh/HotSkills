"""
FastAPI-приложение для отображения информации о динамике вакансий, зарплатах,
языках программирования и навыках.

Модуль включает:

- Инициализацию и настройку FastAPI с асинхронным жизненным циклом.
- Подключение к PostgreSQL через asyncpg и к Redis для кэширования.
- Подключение статических файлов и шаблонов Jinja2 для фронтенда.
- Основные HTML-страницы:
    - "/" — главная страница (index.html)
    - "/{lang}" — страница конкретного языка программирования (lang.html)
- REST API эндпоинты подключаются через `api_router` (все маршруты находятся в папке api) :
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
from contextlib import asynccontextmanager       # для запуска/завершения FastAPI

# --- Сторонние библиотеки ---
import uvicorn                                   # Сервер ASGI(Asynhronus Server Gateway Interface)
from fastapi import FastAPI, Request             # FastAPI и Request для Jinja
from fastapi.responses import HTMLResponse       # Ответы в формате HTML-страниц
from fastapi.staticfiles import StaticFiles      # Подключение /static папки
from fastapi.templating import Jinja2Templates   # Генератор HTML-страниц с динамическими данными
from jinja2 import Environment, FileSystemLoader # Настройка Jinja2 для рендера HTML-шаблонов

# --- Модули проекта ---
from api import router as api_router
from config import STATIC_DIR, TEMPLATES_DIR, CACHE_TTL_DAY
from db import init_db_pool, close_db_pool, init_redis_pool, close_redis_pool
from helpers import get_cache, set_cache


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

# Подключаем маршруты API из папки api (/api/salaries, /api/languages, /api/vacancy-statistics ...)
app.include_router(api_router)

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
        skills = await get_cache(redis_pool, cache_key)

        if not skills:
            # Если в кэше нет — читаем из базы последние свежие данные для языка
            skill_row = await conn.fetchrow(
                f"SELECT {row['code']} FROM hot_skills ORDER BY date DESC LIMIT 1"
            )

            if skill_row and skill_row[row["code"]]:

                # Если данные есть, десериализуем из JSON
                skills = json.loads(skill_row[row["code"]])

                # Кэшируем полученные данные в Redis на 24 часа (данные обновляются раз в день)
                await set_cache(redis_pool, cache_key, skills, expire=CACHE_TTL_DAY)
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


# --- Запуск при старте ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info",
        # workers=2, # При 2 воркерах на текущем железе происходит нехватка RAM — приложение падает
    )
