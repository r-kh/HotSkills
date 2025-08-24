// === Кэш для данных по зарплатам и вакансиям (чтобы не создавать избыточных запросов (fetch), например при переключении регионов или дневных/почасовых показателей) === //
let cachedSalariesData            = null;
let cachedVacanciesStatisticsData = null;
let cachedLanguagesData           = null;
let cachedLanguageCodes           = null;
let cachedLanguageNames           = null;

// === Промисы загрузки (чтобы избежать одних и тех же дублирующих одинаковых параллельных запросов к api) === //
let salariesLoadingPromise  = null;
let vacanciesLoadingPromise = null;
let languagesLoadingPromise = null;


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
export async function loadVacanciesIfNeeded() {
    if (cachedVacanciesStatisticsData) return;
    if (vacanciesLoadingPromise) return vacanciesLoadingPromise;

    vacanciesLoadingPromise = fetch("/api/vacancy-statistics")
        .then(res => res.json())
        .then(json => {
            cachedVacanciesStatisticsData = json;
            vacanciesLoadingPromise = null; // сброс
        });

    return vacanciesLoadingPromise;
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
export function getVacanciesData() {
    return cachedVacanciesStatisticsData;
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