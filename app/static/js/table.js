import { loadVacanciesIfNeeded, loadSalariesIfNeeded, getLanguagesData, getVacanciesData, getSalariesData } from './api.js';


let currentRegion = 'moscow';  // Текущий выбранный регион (по умолчанию Москва)
let tabs;                            // Элементы в HTML с классом .tab (вкладки) (*вынесена в переменную чтобы не дублировать поиск по HTML в разных функциях)
let tableData = [];           // Хранит строки таблицы как данные, не как DOM (для сортировки)
let currentSort = {
    columnIndex: null,              // Индекс текущего столбца сортировки
    ascending: true                 // Направление сортировки: по возрастанию
}; // Состояние сортировки таблицы (нужно для запоминания последней сортировки при переключении вкладок)



// === Инициализация таблицы с зарплатами === //
export function initSalaryTable() {
    initRegionTabs(); // Запускаем инициализацию вкладок (иначе переключение вкладок Москва/Россия не будет работать)
}



// === Переключатель вкладок Москва/Россия === //

// Инициализация вкладок (табы), чтобы пользователь мог переключаться между регионами.
function initRegionTabs() {

    // Получаем все элементы в HTML с классом .tab (вкладки), по которым можно кликнуть.
    tabs = document.querySelectorAll('.tab');

    // Вешаем обработчики(слушатели) кликов ("click") на каждую вкладку (при клике будет вызываться activateTab(tab), которая переключает регион)
    tabs.forEach(tab => { tab.addEventListener('click', () => activateTab(tab)); });

    // Активируем первую вкладку по умолчанию
    if (tabs.length > 0) activateTab(tabs[0]);
}

// Активация-Деактивация вкладки (и обновление таблицы зарплат при переключении)
async function activateTab(tab) {
    tabs.forEach(t => t.classList.remove('active')); // Убираем класс 'active' со всех вкладок (иначе все будут активны)
    tab.classList.add('active');                            // Добавляем 'active' на выбранную вкладку (иначе не будет видно, что выбрано)
    currentRegion = tab.dataset.value;                      // Обновляем регион на основе data-value (иначе не поймём, какой регион выбран)
    await updateSalaryTable(currentRegion);                 // Обновляем таблицу в соответствии с выбранным регионом
}



// === Таблица с данными === //

// Заполнение/Очистка/Сортировка и отображение данных
async function updateSalaryTable(region) {
    try {
        // загружаем данные при необходимости
        await Promise.all([loadVacanciesIfNeeded(), loadSalariesIfNeeded()]);
        clearTableBody();       // Очищаем таблицу
        addRowsToTable(region); // Заполняем таблицу строками по региону
        addTableSorting();      // Подключаем сортировку
    } catch (error) {
        console.error("Ошибка при загрузке таблицы:", error);
    }
    // Если после сортировки колонки переключаемся на другую вкладку, повторно сортируем эту же колонку (это удобно для сравнения)
    if (currentSort.columnIndex !== null) {
        sortTableDataAndRender(currentSort.columnIndex, currentSort.ascending);
    }
}

// Очистка таблицы
function clearTableBody() {
    const tbody = document.querySelector(".salary-table tbody");
    tbody.innerHTML = "";
}

// Добавление строк в таблицу (с зарплатами для указанного региона)
function addRowsToTable(region) {

    const languages = getLanguagesData(); // список языков программирования -> массив объектов: { code, name }
    const vacancies = getVacanciesData(); // кэшированные данные по вакансиям -> объекты: code -> { daily, hourly }
    const salaries  = getSalariesData();  // кэшированные данные по зарплатам -> объекты: code -> { без опыта, 1-3года, 3-6лет, 6+ }

    // Собираем данные в строки по каждому языку в единый массив tableData для дальнейшей отрисовки
    tableData = languages.map(lang => {

        // Получаем последнюю запись по вакансиям и извлекаем соответствующее значение для региона
        const vacancyData = vacancies[lang.code].daily.slice(-1)[0][1]; // daily берёт первый, а daily.slice(-1)[0][1] - берёт последний(-1) элемент массива, вытаскивает его[0], и достаёт из него второй элемент [москва, россия]

        // Берём значение по региону: [0] для Москвы, для России [1]
        const vacancyCount = vacancyData ? (region === 'moscow' ? vacancyData[0] : vacancyData[1]) : 0;

        // Форматируем зарплаты для отображения в таблице (иначе будут "сырые" цифры или ошибки)
        const salaryRanges = formatSalaryRanges(salaries[lang.code], region);

        // Возвращаем объект с данными по языку: понадобится для отрисовки строки таблицы
        return {
            code: lang.code,              // код языка — нужен для формирования ссылок и логотипов
            name: lang.name,              // имя языка — отображается пользователю
            vacancyCount,                 // количество вакансий — числовое значение в таблице
            salaryRanges,                 // массив диапазонов зарплат
        };
    });

    // Отрисовываем собранные данные в DOM таблицы (иначе пользователь не увидит результата)
    renderTableData();
}

// Отрисовка данных таблицы в DOM на основе содержимого массива tableData
function renderTableData() {

    const tbody = document.querySelector(".salary-table tbody"); // Находим <tbody> таблицы по классу .salary-table (иначе некуда будет вставлять строки)
    tbody.innerHTML = "";                                                        // Очищаем старое содержимое таблицы (иначе данные будут дублироваться при перерисовке)

    // Проходим по каждому элементу данных и создаём для него строку таблицы
    tableData.forEach(item => {

        // --- Строка в таблице
        const tr = document.createElement("tr");    // Создаём <tr> — строку как элемент таблицы
        tr.dataset.langName = item.name;                                        // Добавляем название языка как data-атрибут (может использоваться для поиска/фильтрации)
        tr.onclick = () => location.href = `/${item.code}`;            // Устанавливаем обработчик клика по строке: переход по ссылке на страницу языка

        // --- Блок с логотипом и названием языка ---
        const tdLogo = document.createElement("td");// Создаём <td> — 1-ю ячейку таблицы
        const img = document.createElement("img");     // Создаём <img> — логотип языка
        img.src = `/static/logos/${item.code}.webp`;                            // Указываем путь к логотипу по коду языка (иначе не будет изображения)
        img.alt = item.name;                                                    // Добавляем alt-текст для картинки (важно для доступности и SEO)
        tdLogo.appendChild(img);                                                // Вставляем логотип в ячейку
        tdLogo.appendChild(document.createTextNode(item.name));                 // Добавляем текст (название языка) рядом с логотипом
        tr.appendChild(tdLogo);                                                 // Добавляем ячейку логотипа и названия в строку

        // --- Блок с количеством вакансий ---
        const tdVac = document.createElement("td"); // Создаём 2-ю ячейку для количества вакансий
        tdVac.textContent = item.vacancyCount;                                  // Отображаем количество вакансий текстом
        tr.appendChild(tdVac);                                                  // Добавляем ячейку в строку

        // --- Блок с зарплатными диапазонами ---
        item.salaryRanges.forEach(({ text, sortValue }) => {              // Проходим по каждому элементу в массиве salaryRanges (без опыта, 1–3 года, 3-6лет, 6+)
            const td = document.createElement("td");// Создаём 3-4-5-6ю ячейку для одного диапазона зарплат
            td.textContent = text;                                              // Вставляем отформатированный текст зарплаты (например, "80 000 - 100 000")
            tr.appendChild(td);                                                 // Добавляем ячейку в строку
        });

        // Вставляем полностью собранную строку в <tbody>
        tbody.appendChild(tr);
    });
}

// Форматирует "сырые" данные по зарплатам в удобочитаемые диапазоны для таблицы
function formatSalaryRanges(rawArray, region) {

    const ranges = [];                                             // Массив, в который будут собираться отформатированные диапазоны зарплат
    const offset = region === 'moscow' ? 0 : 8;                  // Определяем смещение (offset): Москва идёт с 0-го элемента, Россия — с 8-го
    const roundToHundreds = (value) => Math.round(value / 100) * 100; // Функция округления числа вверх до сотен (Иначе зарплаты будут отображаться с "грязными" числами вроде 83 241)

    // Проходим по 4 диапазонам (8 значений по 2: min и max)
    for (let i = 0; i < 8; i += 2) {

        // Получаем минимальное и максимальное значение диапазона с учётом смещения по региону
        let min = rawArray[offset + i];
        let max = rawArray[offset + i + 1];

        // Если данных нет (оба значения = 0), добавляем "нет данных" (иначе отобразится пустая или некорректная строка)
        if (min === 0 && max === 0) {
            ranges.push({ min, max, text: "нет данных" });
        } else {
            // Округляем min и max до сотен для аккуратного вида
            min = roundToHundreds(min);
            max = roundToHundreds(max);

            // Формируем текстовую строку диапазона (например, "80 000 ₽ – 120 000 ₽")
            const text = `${min.toLocaleString('ru-RU')} ₽ – ${max.toLocaleString('ru-RU')} ₽`;

            // Добавляем объект с данными в массив (text будет показан в таблице)
            ranges.push({ min, max, text });
        }
    }

    return ranges; // возвращаем отформатированные данные (иначе таблица не сможет отобразить зарплаты)
}



// === Сортировка данных в таблице === //

// Добавление функции сортировки в заголовки (и сохранение предыдущей сортировки при переключении вкладок)
function addTableSorting() {

    const headers = document.querySelectorAll(".salary-table th"); // Находим все заголовки таблицы с классом .salary-table

    headers.forEach((th, index) => {    // Перебираем каждый заголовок и индекс

        // Пропускаем заголовки без атрибута data-sortable — только сортируемые колонки (иначе на не-сортируемых столбцах появится клик)
        if (!th.hasAttribute("data-sortable")) return;

        // меняем курсор мыши на "палец" при наведении, чтобы показать, что заголовок кликабелен (иначе пользователь не поймёт, что можно кликать)
        th.style.cursor = "pointer";

        th.onclick = () => {

            // Если кликнули на текущий отсортированный столбец, меняем направление сортировки (иначе устанавливаем сортировку по возрастанию)
            const ascending = currentSort.columnIndex === index ? !currentSort.ascending : false;

             // Сохраняем состояние сортировки (номер колонки и направление), иначе не запомнится выбранная сортировка
            currentSort = { columnIndex: index, ascending };

            // Удаляем классы сортировки со всех заголовков (чтобы убрать стрелки), иначе активные стрелки будут на нескольких колонках
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));

            // Добавляем класс сортировки на текущий заголовок в зависимости от направления (asc или desc) (для визуальной подсказки)
            th.classList.add(ascending ? 'sort-asc' : 'sort-desc');

            // Вызываем функцию сортировки таблицы по выбранному столбцу и направлению
            sortTableDataAndRender(index, ascending);
        };
    });

    // Если есть ранее запомненная сортировка, повторно применяем её к таблице после переключения вкладок (иначе после обновления таблицы сортировка сбросится)
    if (currentSort.columnIndex !== null) {
        sortTableDataAndRender(currentSort.columnIndex, currentSort.ascending);

        // Обновляем визуальные индикаторы (стрелки) сортировки в заголовках
        headers.forEach((th, index) => {

            // Удаляем классы сортировки с каждого заголовка (иначе активные стрелки будут на нескольких колонках)
            th.classList.remove('sort-asc', 'sort-desc');

            // Добавляем класс на текущий сортируемый заголовок в зависимости от направления сортировки (иначе стрелка не будет показана)
            if (index === currentSort.columnIndex) { th.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');}
        });
    }
}

// Сортирует данные таблицы по выбранному столбцу (имя, вакансии или зарплата) и перерисовывает таблицу
function sortTableDataAndRender(columnIndex, ascending = true) {

    // Сортируем массив tableData по заданному столбцу и направлению
    tableData.sort((a, b) => {

        // Сортировка первой колонки (название языка)
        if (columnIndex === 0) {
            return ascending
                ? a.name.localeCompare(b.name)   // Сортировка по имени A-Z
                : b.name.localeCompare(a.name);  // Сортировка по имени Z-A
        }

        // Сортировка второй колонки с количеством вакансий
        if (columnIndex === 1) {
            return ascending
                ? a.vacancyCount - b.vacancyCount  // Сортировка по возрастанию числа вакансий
                : b.vacancyCount - a.vacancyCount; // По убыванию
        }

        // Если клик по одной из четырёх колонок зарплат (индексы 2–5)
        const salaryIndex = columnIndex - 2;       // Приводим индекс колонки к индексу salaryRanges[0–3]
        const aRange = a.salaryRanges[salaryIndex]; // Берём соответствующий диапазон у первого элемента
        const bRange = b.salaryRanges[salaryIndex]; // У второго

        // Для сортировки: используем min для возрастания, max — для убывания
        const aVal = ascending ? aRange?.min ?? 0 : aRange?.max ?? 0; // Защита от отсутствия данных (undefined → 0)
        const bVal = ascending ? bRange?.min ?? 0 : bRange?.max ?? 0;

        // Специальная логика: элементы без данных (0) всегда идут в конец
        if (aVal === 0 && bVal !== 0) return 1;     // a → вниз
        if (bVal === 0 && aVal !== 0) return -1;    // b → вниз

        // Обычная числовая сортировка: min ↑ или max ↓
        return ascending ? aVal - bVal : bVal - aVal;
    });

    renderTableData(); // Перерисовываем таблицу с отсортированными данными (Иначе пользователь не увидит изменений после сортировки)
}