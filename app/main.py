"""
main.py — точка входа FastAPI-приложения.
"""

# Сторонние библиотеки
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # Подключение /static папки
import uvicorn  # Запуск сервера ASGI (Asynchronous Server Gateway Interface)

# Модули проекта
from app.api import router as api_router
from app.core.config import STATIC_DIR
from app.core.lifespan import lifespan
from app.web.pages import router as web_router


# Инициализация приложения
app = FastAPI(lifespan=lifespan)

# Подключаем маршруты
app.include_router(api_router)  # API (/salaries, /languages, /vacancy-statistics ...)
app.include_router(web_router)  # HTML-страницы (index.html, lang.html и др.)

# Подключаем статические файлы (/static: CSS, JS, изображения)
app.mount("/app/static", StaticFiles(directory=STATIC_DIR), name="static")


# Запуск приложения напрямую (только при запуске python main.py)
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        # workers=2, # на текущем железе при 2 воркерах происходит нехватка RAM — приложение падает
    )
