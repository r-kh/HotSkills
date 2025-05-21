import asyncpg
import logging
import os
import sys
from datetime import timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import redis.asyncio as redis
import json

enable_logging = "--log" in sys.argv

# Логирование
logging.basicConfig(level=logging.INFO if enable_logging else logging.CRITICAL)

app = FastAPI()

app.mount("/static", StaticFiles(directory="/mnt/sda1/WWW/HotSkills.info/static"), name="static")
templates = Jinja2Templates(directory="/mnt/sda1/WWW/HotSkills.info/templates")

DB_CONFIG = {
    "host"      : os.getenv("DB_HOST"),
    "database"  : os.getenv("DB_NAME"),
    "user"      : os.getenv("DB_USER"),
    "password"  : os.getenv("DB_PASSWORD"),
    "ssl"       : os.getenv("DB_SSL") == "True"
}

redis_pool = None


@app.on_event("startup")
async def startup():
    app.state.db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=4)
    global redis_pool
    redis_pool = await redis.from_url("redis://localhost")


@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()
    await redis_pool.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/salaries")
async def get_salaries_data():
    pool = app.state.db_pool

    cached = await redis_pool.get("salary_table")
    if cached:
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=json.loads(cached))

    try:
        async with pool.acquire() as conn:
            languages = await conn.fetch("SELECT name, code FROM programming_languages ORDER BY id")
            salary_row = await conn.fetchrow("SELECT * FROM salaries ORDER BY date DESC LIMIT 1")
    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка при запросе к базе данных: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    def format_range(start, end):
        if start == 0 and end == 0:
            return "нет данных"

        # округляем до 100
        start = round(start, -2)
        end = round(end, -2)

        return f"{start:,} ₽&nbsp;&nbsp;–&nbsp;&nbsp;{end:,} ₽".replace(",", " ")

    result = []

    for lang in languages:
        code = lang["code"]
        name = lang["name"]
        salary_data = salary_row.get(code)
        if not salary_data or len(salary_data) != 16:
            moscow = ["нет данных"] * 4
            russia = ["нет данных"] * 4
        else:
            moscow = [format_range(salary_data[i], salary_data[i + 1]) for i in range(0, 8, 2)]
            russia = [format_range(salary_data[i], salary_data[i + 1]) for i in range(8, 16, 2)]

        result.append({
            "name": name,
            "code": code,
            "moscow": moscow,
            "russia": russia
        })

    await redis_pool.set("salary_table", json.dumps(result), ex=1800)  # 30 минут
    return JSONResponse(content=result)


@app.get("/{language}", response_class=HTMLResponse)
async def show_language(request: Request, language: str):
    supported_languages = [
        "python", "go", "java", "cpp", "php", "ruby", "swift", "dart",
        "kotlin", "scala", "csharp", "typescript", "javascript", "one_c"
    ]
    if language.lower() not in supported_languages:
        return HTMLResponse(content="Страница не найдена", status_code=404)

    # Получаем имя языка из базы по коду
    async with app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT name FROM programming_languages WHERE code = $1", language.lower())

    if not row:
        return HTMLResponse(content="Страница не найдена", status_code=404)

    language_name = row["name"]

    return templates.TemplateResponse("lang.html", {
        "request": request,
        "language": language,  # код
        "language_name": language_name  # красивое имя
    })


@app.get("/api/languages")
async def get_languages():
    pool = app.state.db_pool

    cached = await redis_pool.get("languages_list")
    if cached:
        logging.info("Возвращаем список языков из кеша")
        return JSONResponse(content=json.loads(cached))

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT code, name FROM programming_languages ORDER BY id")
    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка при получении языков: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    result = [{"code": row["code"], "name": row["name"]} for row in rows]

    await redis_pool.set("languages_list", json.dumps(result), ex=86400)  # 24ч кеш
    return JSONResponse(content=result)


@app.get("/api/vacancy-data")
async def get_vacancy_data():
    pool = app.state.db_pool

    cached_data = await redis_pool.get("vacancy_stats")
    if cached_data:
        logging.info("Возвращаем данные из кеша")
        return JSONResponse(content=json.loads(cached_data))

    try:
        async with pool.acquire() as conn:
            # Данные по языкам (по часам) — оба значения (Москва и Россия)
            hourly_languages = await conn.fetch(
                """
                SELECT
                    date,
                    c[1] AS c_moscow, c[2] AS c_russia,
                    cpp[1] AS cpp_moscow, cpp[2] AS cpp_russia,
                    csharp[1] AS csharp_moscow, csharp[2] AS csharp_russia,
                    dart[1] AS dart_moscow, dart[2] AS dart_russia,
                    go[1] AS go_moscow, go[2] AS go_russia,
                    java[1] AS java_moscow, java[2] AS java_russia,
                    javascript[1] AS javascript_moscow, javascript[2] AS javascript_russia,
                    kotlin[1] AS kotlin_moscow, kotlin[2] AS kotlin_russia,
                    one_c[1] AS one_c_moscow, one_c[2] AS one_c_russia,
                    php[1] AS php_moscow, php[2] AS php_russia,
                    python[1] AS python_moscow, python[2] AS python_russia,
                    ruby[1] AS ruby_moscow, ruby[2] AS ruby_russia,
                    scala[1] AS scala_moscow, scala[2] AS scala_russia,
                    swift[1] AS swift_moscow, swift[2] AS swift_russia,
                    typescript[1] AS typescript_moscow, typescript[2] AS typescript_russia
                FROM hh_dev_vacancies_languages_popularity
                WHERE date >= NOW() - INTERVAL '24 hours'
                ORDER BY date ASC;
                """
            )

            # Данные по языкам (по дням) — оба значения
            daily_languages = await conn.fetch(
                """
                SELECT DISTINCT ON (DATE(date))
                    date,
                    c[1] AS c_moscow, c[2] AS c_russia,
                    cpp[1] AS cpp_moscow, cpp[2] AS cpp_russia,
                    csharp[1] AS csharp_moscow, csharp[2] AS csharp_russia,
                    dart[1] AS dart_moscow, dart[2] AS dart_russia,
                    go[1] AS go_moscow, go[2] AS go_russia,
                    java[1] AS java_moscow, java[2] AS java_russia,
                    javascript[1] AS javascript_moscow, javascript[2] AS javascript_russia,
                    kotlin[1] AS kotlin_moscow, kotlin[2] AS kotlin_russia,
                    one_c[1] AS one_c_moscow, one_c[2] AS one_c_russia,
                    php[1] AS php_moscow, php[2] AS php_russia,
                    python[1] AS python_moscow, python[2] AS python_russia,
                    ruby[1] AS ruby_moscow, ruby[2] AS ruby_russia,
                    scala[1] AS scala_moscow, scala[2] AS scala_russia,
                    swift[1] AS swift_moscow, swift[2] AS swift_russia,
                    typescript[1] AS typescript_moscow, typescript[2] AS typescript_russia
                FROM hh_dev_vacancies_languages_popularity
                WHERE date >= NOW() - INTERVAL '31 days'
                ORDER BY DATE(date), date DESC;
                """
            )

            # Разработчики ПО (по часам)
            hourly_profession = await conn.fetch(
                """
                SELECT date, software_developer
                FROM hh_profession_vacancies_statistics
                WHERE date >= NOW() - INTERVAL '24 hours'
                ORDER BY date ASC;
                """
            )

            # Разработчики ПО (по дням)
            daily_profession = await conn.fetch(
                """
                SELECT
                    DATE(date) AS day, software_developer
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY DATE(date) ORDER BY date DESC) AS rn
                    FROM hh_profession_vacancies_statistics
                    WHERE date >= NOW() - INTERVAL '31 days'
                ) AS ranked
                WHERE rn = 1
                ORDER BY day ASC;
                """
            )

    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка при запросе к базе данных: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    langs = ["c", "cpp", "csharp", "dart", "go", "java", "javascript", "kotlin",
             "one_c", "php", "python", "ruby", "scala", "swift", "typescript"]

    hourly = {lang: {"hours": [], "moscow_counts": [], "russia_counts": []} for lang in langs}
    for row in reversed(hourly_languages):
        for lang in langs:
            hourly[lang]["hours"].append(row["date"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
            hourly[lang]["moscow_counts"].append(row[f"{lang}_moscow"])
            hourly[lang]["russia_counts"].append(row[f"{lang}_russia"])

    daily_data = {lang: {"days": [], "moscow_counts": [], "russia_counts": []} for lang in langs}
    for row in daily_languages:
        for lang in langs:
            daily_data[lang]["days"].append(row["date"].isoformat())
            daily_data[lang]["moscow_counts"].append(row[f"{lang}_moscow"])
            daily_data[lang]["russia_counts"].append(row[f"{lang}_russia"])

    software_developer_hourly = {"hours": [], "counts": []}
    for row in reversed(hourly_profession):
        software_developer_hourly["hours"].append(row["date"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
        software_developer_hourly["counts"].append(row["software_developer"])

    software_developer_daily = {"days": [], "counts": []}
    for row in daily_profession:
        software_developer_daily["days"].append(row["day"].isoformat())
        software_developer_daily["counts"].append(row["software_developer"])

    result = {
        lang: {
            "hourly": hourly[lang],
            "daily": daily_data[lang]
        }
        for lang in langs
    }

    result["software_developer"] = {
        "hourly": software_developer_hourly,
        "daily": software_developer_daily
    }

    await redis_pool.set("vacancy_stats", json.dumps(result), ex=3600)  # кеш на час
    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info" if enable_logging else "warning")
