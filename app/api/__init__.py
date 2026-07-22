"""
Пакет API с маршрутизатором для FastAPI.
"""

# --- Сторонние библиотеки ---
from fastapi import APIRouter
# --- Модули проекта ---
from . import salaries, languages, vacancies, vacancy_statistics, resumes, количество_новых_вакансий

router = APIRouter()
router.include_router(salaries.router, prefix="/api")
router.include_router(languages.router, prefix="/api")
router.include_router(resumes.router, prefix="/api")
router.include_router(vacancies.router, prefix="/api")
router.include_router(vacancy_statistics.router, prefix="/api")
router.include_router(количество_новых_вакансий.router, prefix="/api")