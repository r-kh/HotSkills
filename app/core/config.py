"""
Конфигурация FastAPI-приложения.
Содержит настройки подключения к базам данных, Redis, пути к статике и шаблонам.
"""

import os   # Для работы с переменными окружения

# --- Конфигурация базы данных (берётся из переменных окружения) ---
DB_CONFIG = {
    "host"     : os.getenv("DB_HOST"),
    "database" : os.getenv("DB_NAME"),
    "user"     : os.getenv("DB_USER"),
    "password" : os.getenv("DB_PASSWORD"),
    "ssl"      : os.getenv("DB_SSL") == "True"
}

# --- Конфигурация Redis (берётся из переменной окружения) ---
REDIS_URL = os.getenv("REDIS_URL")

# --- Пути к статическим файлам и шаблонам ---
STATIC_DIR    = os.getenv("STATIC_DIR")
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR")

# --- Настройки кэширования (по умолчанию) ---
CACHE_TTL_HOUR      = 3600  # 1 час
CACHE_TTL_DAY       = 86400 # 24 часа
CACHE_TTL_NO_EXPIRY = None  # бессрочно
