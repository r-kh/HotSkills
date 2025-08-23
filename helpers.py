import json
import logging


async def get_cache(redis_pool, key):
    """
    Получает данные из Redis по ключу.
    Возвращает Python-объект или None, если данных нет.
    """
    cached = await redis_pool.get(key)
    if cached:
        logging.info(f"Кэш найден по ключу: {key}")
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
        logging.info(f"Кэш установлен по ключу: {key}, TTL={expire}")
    except Exception as e:
        logging.error(f"Ошибка при установке кэша в Redis: {e}")
