"""
pages.py — маршруты для HTML-страниц (frontend-часть).

Содержит обработчики GET-запросов, которые возвращают сгенерированные Jinja2-шаблоны:
- "/"       — главная страница (index.html)
- "/{lang}" — страница конкретного языка программирования (lang.html)
"""

import json                                      # Сериализация
from fastapi import APIRouter, Request           # Маршрутизатор и объект запроса FastAPI
from fastapi.responses import HTMLResponse       # Ответы в формате HTML-страниц
from fastapi.templating import Jinja2Templates   # Генератор HTML-страниц с динамическими данными
from jinja2 import Environment, FileSystemLoader # Настройка Jinja2 для рендера HTML-шаблонов

from app.core.config import TEMPLATES_DIR, CACHE_TTL_DAY
from app.core.helpers import get_cache, set_cache

router = APIRouter()

# шаблоны HTML (через Jinja2) (надо попробовать переехать на React/Vue)
templates = Jinja2Templates(env=Environment(loader=FileSystemLoader(TEMPLATES_DIR)))


# --- Главная страница сайта (index.html) ---
@router.get("/", response_class=HTMLResponse)
# Ловим GET запрос по адресу "/" и отвечаем HTML'ом
async def index(request: Request):
    """Главная страница сайта."""

    return templates.TemplateResponse("index.html", {"request": request})


# --- Обработчик GET-запроса для страницы языка по коду (lang.html) ---
@router.get("/{lang}", response_class=HTMLResponse)
async def show_lang_page(request: Request, lang: str):
    """
    Возвращает страницу языка с актуальными навыками и статистикой.

    Ловим URL с переменной lang (код языка),
    передаём её в асинхронную функцию-обработчик и возвращаем HTML
    """

    # Получаем доступ к пулам соединений с БД и Redis
    db_pool    = request.app.state.db_pool
    redis_pool = request.app.state.redis_pool

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
