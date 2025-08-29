# Базовый образ с Python
FROM python:3.11.4

# Метаданные образа
LABEL description="Образ с Python 3.11.4 для HotSkills.info"
LABEL version="1.0"
LABEL maintainer="raphael@mail.ru"

# Рабочая директория внутри контейнера
WORKDIR /HotSkills.info

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# переменные окружения
ENV STATIC_DIR=/HotSkills.info/app/static
ENV TEMPLATES_DIR=/HotSkills.info/app/templates

# Копируем проект внутрь контейнера
COPY app/ ./app

# Команда по умолчанию для запуска FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]