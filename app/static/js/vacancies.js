import {
    loadVacanciesIfNeeded,
    getVacanciesData
} from "./api.js";

let tableData = [];
let sortState = {
    column: null,
    ascending: false
};

const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const vacancyCountSpan = document.getElementById('vacancy-count');

function sortData() {
    if (sortState.column === null) return;
    const col = sortState.column;
    const asc = sortState.ascending;
    tableData.sort((a, b) => {
        switch (col) {
            case 0: {
                const nameA = a.name?.toLowerCase() ?? '';
                const nameB = b.name?.toLowerCase() ?? '';
                return asc ? nameA.localeCompare(nameB, 'ru') : nameB.localeCompare(nameA, 'ru');
            }
            case 1: {
                const compA = a.Работодатель?.toLowerCase() ?? '';
                const compB = b.Работодатель?.toLowerCase() ?? '';
                return asc ? compA.localeCompare(compB, 'ru') : compB.localeCompare(compA, 'ru');
            }
            case 2: {
                const dateA = Date.parse(a.Создана);
                const dateB = Date.parse(b.Создана);

                if (dateA !== dateB) {
                    return asc ? dateA - dateB : dateB - dateA;
                }

                return asc
                    ? a.responses - b.responses
                    : a.responses - b.responses;
            }
            case 3: {
                return asc ? a.responses - b.responses : b.responses - a.responses;
            }
            case 4: {
                const contractA = a.labor_contract ? 1 : 0;
                const contractB = b.labor_contract ? 1 : 0;
                return asc ? contractA - contractB : contractB - contractA;
            }
            case 5: {
                const salaryAFrom = a.salary?.[0] ?? 0;
                const salaryATo   = a.salary?.[1] ?? salaryAFrom;
                const salaryBFrom = b.salary?.[0] ?? 0;
                const salaryBTo   = b.salary?.[1] ?? salaryBFrom;
                if (salaryATo !== salaryBTo) {
                    return asc ? salaryATo - salaryBTo : salaryBTo - salaryATo;
                }
                return asc ? salaryAFrom - salaryBFrom : salaryBFrom - salaryAFrom;
            }
            default: return 0;
        }
    });
}

function formatLaborContract(value) {
    return value === true ? 'Трудовой договор' : '—';
}

function formatSalary(salary) {
    if (!salary) return '—';
    const [from, to] = salary;
    if (from && to && from === to) return `${from.toLocaleString('ru-RU')} ₽`;
    if (from && to) return `${from.toLocaleString('ru-RU')} - ${to.toLocaleString('ru-RU')} ₽`;
    if (from) return `от ${from.toLocaleString('ru-RU')} ₽`;
    if (to) return `до ${to.toLocaleString('ru-RU')} ₽`;
    return '—';
}

function renderTable() {
    const tbody = document.querySelector('.salary-table tbody');
    tbody.innerHTML = '';
    tableData.forEach(vacancy => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => {
            window.open(`https://hh.ru/vacancy/${vacancy.id}`, '_blank');
        });
        tr.innerHTML = `
            <td>${vacancy.name}</td>
            <td>${vacancy.Работодатель}</td>
            <td>${vacancy.Создана}</td>
            <td>${vacancy.responses}</td>
            <td>${formatLaborContract(vacancy.labor_contract)}</td>
            <td>${formatSalary(vacancy.salary)}</td>
        `;
        tbody.appendChild(tr);
    });
    if (vacancyCountSpan) {
        vacancyCountSpan.textContent = tableData.length;
}}

function updateSortIcons(activeColumn) {
    const headers = document.querySelectorAll('.salary-table th');
    headers.forEach((th, index) => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (index === activeColumn) {
            th.classList.add(sortState.ascending ? 'sort-asc' : 'sort-desc');
        }
    });
}

function addSorting() {
    const headers = document.querySelectorAll('.salary-table th');
    const columnHandlers = [
        () => { sortState.ascending = sortState.column === 0 ? !sortState.ascending : true; sortState.column = 0; sortData(); updateSortIcons(0); renderTable(); },
        () => { sortState.ascending = sortState.column === 1 ? !sortState.ascending : true; sortState.column = 1; sortData(); updateSortIcons(1); renderTable(); },
        () => { sortState.ascending = sortState.column === 2 ? !sortState.ascending : false; sortState.column = 2; sortData(); updateSortIcons(2); renderTable(); },
        () => { sortState.ascending = sortState.column === 3 ? !sortState.ascending : false; sortState.column = 3; sortData(); updateSortIcons(3); renderTable(); },
        () => { sortState.ascending = sortState.column === 4 ? !sortState.ascending : false; sortState.column = 4; sortData(); updateSortIcons(4); renderTable(); },
        () => { sortState.ascending = sortState.column === 5 ? !sortState.ascending : false; sortState.column = 5; sortData(); updateSortIcons(5); renderTable(); }
    ];
    headers.forEach((th, index) => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', columnHandlers[index] || (() => {}));
    });
}

async function updateTable(search) {
    await loadVacanciesIfNeeded(search);
    const data = getVacanciesData(search);
    tableData = data.vacancies || [];
    if (sortState.column !== null) sortData();
    renderTable();
    if (sortState.column !== null) updateSortIcons(sortState.column);
}

function getSearchFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('search');
}

function updateURL(search) {
    const url = new URL(window.location);
    if (search) url.searchParams.set('search', search);
    else url.searchParams.delete('search');
    window.history.pushState({}, '', url);
}

// Флаг, чтобы предотвратить повторные запросы во время загрузки
let isSearching = false;

// Функция для установки состояния загрузки
function setLoadingState(isLoading) {
    if (!searchButton || !searchInput) return;

    const tableWrapper = document.querySelector('.salary-table-wrapper');

    if (isLoading) {
        // Блокируем кнопку и меняем текст
        searchButton.disabled = true;
        searchButton.textContent = 'Ищем…';
        // Добавляем спиннер
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        spinner.id = 'search-spinner';
        searchButton.appendChild(spinner);

        // Меняем счётчик
        if (vacancyCountSpan) {
            vacancyCountSpan.textContent = '…';
            vacancyCountSpan.classList.add('loading');
        }

        // Затемняем таблицу
        if (tableWrapper) {
            tableWrapper.classList.add('loading');
        }
    } else {
        // Восстанавливаем кнопку
        searchButton.disabled = false;
        searchButton.textContent = 'Найти';
        const existingSpinner = document.getElementById('search-spinner');
        if (existingSpinner) existingSpinner.remove();

        // Восстанавливаем счётчик (он обновится в renderTable, но на всякий случай)
        if (vacancyCountSpan) {
            vacancyCountSpan.classList.remove('loading');
            vacancyCountSpan.textContent = tableData.length; // актуальное значение
        }

        // Убираем затемнение
        if (tableWrapper) {
            tableWrapper.classList.remove('loading');
        }
    }
}


// Обновлённая функция handleSearch
async function handleSearch() {
    // Если уже идёт поиск – игнорируем
    if (isSearching) return;

    const query = searchInput.value.trim();
    const searchParam = query || null;

    // Обновляем URL
    updateURL(searchParam);

    // Включаем индикатор загрузки
    setLoadingState(true);
    isSearching = true;

    try {
        // Выполняем запрос и обновляем таблицу
        await updateTable(searchParam);
    } catch (error) {
        console.error('Ошибка при поиске:', error);
        // Можно показать сообщение об ошибке (опционально)
        if (vacancyCountSpan) {
            vacancyCountSpan.textContent = 'Ошибка';
            vacancyCountSpan.classList.remove('loading');
        }
    } finally {
        // В любом случае выключаем индикатор
        setLoadingState(false);
        isSearching = false;
        // Обновляем счётчик после загрузки (он уже обновлён в renderTable, но на всякий случай)
        if (vacancyCountSpan && !vacancyCountSpan.classList.contains('loading')) {
            vacancyCountSpan.textContent = tableData.length;
        }
    }
}

function getInitialSearch() {
    if (typeof hhKeyword !== "undefined" && hhKeyword) {
        return hhKeyword;
    }

    return getSearchFromURL();
}

document.addEventListener('DOMContentLoaded', async () => {
    const urlSearch = getInitialSearch();

    if (searchInput && urlSearch) {
        searchInput.value = urlSearch;
    }

    await updateTable(urlSearch);

    // ----- начальная сортировка по дате -----
    if (sortState.column === null) {      // если сортировка ещё не установлена
        sortState.column = 2;             // колонка "Дата"
        sortState.ascending = false;      // false = по убыванию (свежие сверху)
        sortData();                       // применяем сортировку к tableData
        renderTable();                    // перерисовываем таблицу
        // updateSortIcons(2);            // обновляем иконку сортировки на заголовке (если нужно будет)
    }

    // сортировка всегда нужна
    addSorting();

    // поиск только на странице /vacancies
    if (searchButton && searchInput) {

        searchButton.addEventListener('click', handleSearch);

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSearch();
            }
        });
    }
});