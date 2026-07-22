// === Кэш для данных по зарплатам и вакансиям (чтобы не создавать избыточных запросов (fetch), например при переключении регионов или дневных/почасовых показателей) === //
let cachedSalariesData          = null;
let cachedVacanciesData           = {};
let cachedVacancyStatisticsData = null;
let cachedResumeStatisticsData  = null;
let cachedLanguagesData         = null;
let cachedLanguageCodes         = null;
let cachedLanguageNames         = null;
let cachedNewVacanciesStatisticsData = null;

// === Промисы загрузки (чтобы избежать одних и тех же дублирующих одинаковых параллельных запросов к api) === //
let salariesLoadingPromise          = null;
let vacanciesLoadingPromise         = null;
let vacancyStatisticsLoadingPromise = null;
let resumeStatisticsLoadingPromise  = null;
let languagesLoadingPromise         = null;
let newVacanciesStatisticsLoadingPromise = null;


/**
 * Загрузка и кэширование данных о зарплатах и вакансиях,
 * если они ещё не загружены.
 * @returns {Promise<void>}
 */

// === Загрузка зарплат ===
export async function loadSalariesIfNeeded() {
    if (cachedSalariesData) return;
    if (salariesLoadingPromise) return salariesLoadingPromise;

    salariesLoadingPromise = fetch("/api/salaries")
        .then(res => res.json())
        .then(json => {
            cachedSalariesData = json;
            salariesLoadingPromise = null; // сброс
        });

    return salariesLoadingPromise;
}


// === Загрузка вакансий ===
// === Загрузка вакансий ===
export async function loadVacanciesIfNeeded(search = null) {

    const cacheKey = search || "all";

    if (cachedVacanciesData[cacheKey]) return;

    if (vacanciesLoadingPromise) return vacanciesLoadingPromise;

    let url = "/api/vacancies";
    if (search) {
        url += `?search=${encodeURIComponent(search)}`;
    }

    vacanciesLoadingPromise = fetch(url)
        .then(res => res.json())
        .then(json => {
            cachedVacanciesData[cacheKey] = json;
            vacanciesLoadingPromise = null;
        })
        .catch(err => {
            vacanciesLoadingPromise = null;
            throw err;
        });
    return vacanciesLoadingPromise;
}


// === Загрузка статистики вакансий ===
export async function loadVacancyStatisticsIfNeeded() {
    if (cachedVacancyStatisticsData) return;
    if (vacancyStatisticsLoadingPromise) return vacancyStatisticsLoadingPromise;

    vacancyStatisticsLoadingPromise = fetch("/api/vacancy-statistics")
        .then(res => res.json())
        .then(json => {
            cachedVacancyStatisticsData = json;
            vacancyStatisticsLoadingPromise = null; // сброс
        });

    return vacancyStatisticsLoadingPromise;
}


// Функция загрузки
export async function loadNewVacanciesStatisticsIfNeeded() {
    if (cachedNewVacanciesStatisticsData) return;
    if (newVacanciesStatisticsLoadingPromise) return newVacanciesStatisticsLoadingPromise;

    newVacanciesStatisticsLoadingPromise = fetch("/api/new-vacancies-statistics")
        .then(res => res.json())
        .then(json => {
            cachedNewVacanciesStatisticsData = json;
            newVacanciesStatisticsLoadingPromise = null;
        })
        .catch(err => {
            newVacanciesStatisticsLoadingPromise = null;
            throw err;
        });

    return newVacanciesStatisticsLoadingPromise;
}


// === Загрузка статистики резюме ===
export async function loadResumeStatisticsIfNeeded() {
    if (cachedResumeStatisticsData) return;
    if (resumeStatisticsLoadingPromise) return resumeStatisticsLoadingPromise;

    resumeStatisticsLoadingPromise = fetch("/api/resume-statistics")
        .then(res => res.json())
        .then(json => {
            cachedResumeStatisticsData = json;
            resumeStatisticsLoadingPromise = null; // сброс
        });

    return resumeStatisticsLoadingPromise;
}

// === Загрузка языков ===
export async function loadLanguagesIfNeeded() {
    if (cachedLanguagesData) return;
    if (languagesLoadingPromise) return languagesLoadingPromise;

    languagesLoadingPromise = fetch("/api/languages")
        .then(res => res.json())
        .then(json => {
            cachedLanguagesData = json;
            cachedLanguageCodes = json.map(lang => lang.code);
            cachedLanguageNames = json.map(lang => lang.name);
            languagesLoadingPromise = null;
        })
        .catch(err => {
            languagesLoadingPromise = null;
            throw err;
        });

    return languagesLoadingPromise;
}



// === Геттеры == //

// Возвращает кэшированные данные по зарплатам
export function getSalariesData() {
    return cachedSalariesData;
}

// Возвращает кэшированные данные по вакансиям
export function getVacanciesData(search = null) {
    return cachedVacanciesData[search || "all"];
}

// Возвращает кэшированные данные по статистике вакансий
export function getVacancyStatisticsData() {
    return cachedVacancyStatisticsData;
}

// Возвращает кэшированные данные по статистике новых вакансий
export function getNewVacanciesStatisticsData() {
    return cachedNewVacanciesStatisticsData;
}

// Возвращает кэшированные данные по статистике резюме
export function getResumesStatisticsData() {
    return cachedResumeStatisticsData;
}

export function getLanguagesData() {
    return cachedLanguagesData;
}

export function getLanguageCodes() {
    return cachedLanguageCodes;
}

export function getLanguageNames() {
    return cachedLanguageNames;
}