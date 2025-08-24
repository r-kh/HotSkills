"""
Модуль API для работы с языками программирования.
"""

# --- Стандартные библиотеки ---
import logging                             # Отслеживание работы/диагностика проблем

# --- Сторонние библиотеки ---
from fastapi import APIRouter, Request     # Маршрутизатор и объект запроса FastAPI
from fastapi.responses import JSONResponse # Ответы в формате JSON (для API)

# --- Модули проекта ---
from app.core.config import CACHE_TTL_NO_EXPIRY
from app.core.helpers import get_cache, set_cache

router = APIRouter()

# --- API: получение списка языков программирования ---
@router.get("/languages")
async def get_languages(request: Request):
    """
    Возвращает JSON со списком языков программирования.
    Пример ответа на фронт:
    [{"code":"one_c","name":"1C","color":"#E31E24"},...]
    """

    # Получаем доступ к пулам соединений с Redis
    redis_pool = request.app.state.redis_pool

    # Пробуем сначала получить кешированные данные из Redis по ключу "languages"
    # (иначе всегда будем дергать БД)
    cached_languages = await get_cache(redis_pool, "languages")
    # Если кеш есть
    if cached_languages:
        # Логируем, что используются кэшированные данные из Redis
        logging.info("Возвращаем список языков из кеша")
        return JSONResponse(content=cached_languages)  # Отдаём кеш в виде JSON

    # Если нет — берём из загруженного списка
    languages = request.app.state.languages

    # Сохраняем результат в кеш Redis бессрочно, языки не часто обновляются
    # (иначе каждый запрос будет идти в БД)
    # (если я добавлю новые языки, я перезапущу руками)
    await set_cache(redis_pool, "languages", languages, expire=CACHE_TTL_NO_EXPIRY)

    # Возвращаем данные в виде JSON
    return JSONResponse(content=languages)
