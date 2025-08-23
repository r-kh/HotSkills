"""
Вспомогательные функции для работы с кэшированием данных в Redis.
"""

# --- Стандартные библиотеки ---
import json                             # Сериализация
import logging                          # Отслеживание работы/диагностика проблем

# --- Сторонние библиотеки ---
from redis.exceptions import RedisError # для ловли ошибок Redis

async def get_cache(redis_pool, key):
    """
    Получает данные из Redis по ключу.
    Возвращает Python-объект или None, если данных нет.
    """
    cached = await redis_pool.get(key)
    if cached:
        logging.info("Кэш найден по ключу: %s", key)
        return json.loads(cached)
    return None


async def set_cache(redis_pool, key, value, expire=None):
    """
    Сохраняет данные в Redis.
    redis_pool : соединение с Redis
    key        : ключ
    value      : данные (будут сериализованы в JSON)
    expire     : время жизни в секундах (None = без TTL)
    """
    try:
        await redis_pool.set(key, json.dumps(value), ex=expire)
        logging.info("Кэш установлен по ключу: %s, TTL=%s", key, expire)
    except RedisError as e:
        logging.error("Ошибка при установке кэша в Redis: %s", e)
