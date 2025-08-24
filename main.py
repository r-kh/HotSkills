"""
main.py — точка входа FastAPI-приложения.

Назначение:
- Инициализация и настройка FastAPI с асинхронным жизненным циклом.
- Подключение к PostgreSQL через asyncpg и к Redis для кэширования.
- Загрузка списка языков программирования при старте.
- Подключение маршрутов:
    - API эндпоинты из пакета api (JSON-ответы).
    - HTML-страницы из views (рендер Jinja2-шаблонов).
- Подключение статических файлов (/static).
"""

# --- Стандартные библиотеки ---
from contextlib import asynccontextmanager       # для запуска/завершения FastAPI

# --- Сторонние библиотеки ---
import uvicorn                                   # Сервер ASGI(Asynhronus Server Gateway Interface)
from fastapi import FastAPI                      # FastAPI
from fastapi.staticfiles import StaticFiles      # Подключение /static папки

# --- Модули проекта ---
from api import router as api_router
from config import STATIC_DIR
from db import init_db_pool, close_db_pool, init_redis_pool, close_redis_pool
from views import router as views_router


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

# Подключаем HTML-страницы (index.html, lang.html и др.) из views.py
app.include_router(views_router)

# --- Подключаем статические файлы (/static) и шаблоны (HTML) в FastAPI-приложение ---

# подключение CSS, JS, изображений
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Запуск при старте ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info",
        # workers=2, # При 2 воркерах на текущем железе происходит нехватка RAM — приложение падает
    )
