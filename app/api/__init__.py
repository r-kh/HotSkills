"""
Пакет API с маршрутизатором для FastAPI.
"""

# --- Сторонние библиотеки ---
from fastapi import APIRouter
# --- Модули проекта ---
from . import salaries, languages, vacancy_statistics, resumes

router = APIRouter()
router.include_router(salaries.router, prefix="/api")
router.include_router(languages.router, prefix="/api")
router.include_router(resumes.router, prefix="/api")
router.include_router(vacancy_statistics.router, prefix="/api")
