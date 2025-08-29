"""
lifespan.py — жизненный цикл FastAPI приложения.

Задачи:
- Инициализация и закрытие соединений с PostgreSQL и Redis
- Загрузка языков программирования в app.state
"""

# Стандартные библиотеки
from contextlib import asynccontextmanager  # для запуска/завершения FastAPI

# Сторонние библиотеки
from fastapi import FastAPI

# Модули проекта
from app.core.db import init_db_pool, close_db_pool, init_redis_pool, close_redis_pool


async def load_languages(db_pool):
    """
    Загружает языки программирования и их параметры из базы данных.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT code, name, color FROM programming_languages ORDER BY id"
        )
        return [dict(row) for row in rows]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Асинхронный контекстный менеджер для запуска и завершения (замена startup/shutdown).
    """

    # Startup
    # Инициализация БД и Redis и загрузка языков
    app.state.db_pool = await init_db_pool()
    app.state.redis_pool = await init_redis_pool()
    app.state.languages = await load_languages(app.state.db_pool)

    yield  # точка запуска приложения: FastAPI запускается здесь и работает до завершения(shutdown)

    # Shutdown
    # Очистка ресурсов, закрываем соединения (иначе будут утечки)
    await close_db_pool(app.state.db_pool)
    await close_redis_pool(app.state.redis_pool)
