"""
Модуль db.py для управления подключениями к PostgreSQL и Redis.

Включает:
- Создание и закрытие пулов соединений
- Функции получения пулов из состояния приложения (FastAPI)
"""

# --- Стандартные библиотеки ---
import logging                          # Отслеживание работы/диагностика проблем

# --- Сторонние библиотеки ---
import asyncpg                          # Работа с PostgreSQL (async)
import redis.asyncio as redis           # Кэширование часто запрашиваемых данных (async)

# --- Модули проекта ---
from config import DB_CONFIG, REDIS_URL


async def init_db_pool():
    """
    Создаёт пул соединений с PostgreSQL.
    Возвращает asyncpg.pool.Pool
    """
    try:
        # 1 сессия БД ~ work_mem + temp_buffers, установлено 4, можно больше (отталкиваться от RAM)
        pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=4)
        logging.info("Пул соединений к БД создан")
        return pool
    except Exception as e:
        logging.error("Ошибка при создании пула БД: %s", e)
        raise


async def close_db_pool(pool):
    """
    Закрывает пул соединений к PostgreSQL.
    """
    if pool:
        await pool.close()
        logging.info("Пул соединений к БД закрыт")


async def init_redis_pool():
    """
    Создаёт соединение с Redis.
    Возвращает redis.asyncio.Redis
    """
    try:
        r = await redis.from_url(REDIS_URL)
        logging.info("Соединение с Redis создано")
        return r
    except Exception as e:
        logging.error("Ошибка при подключении к Redis: %s", e)
        raise


async def close_redis_pool(pool):
    """
    Закрывает соединение с Redis.
    """
    if pool:
        await pool.close()
        logging.info("Соединение с Redis закрыто")
