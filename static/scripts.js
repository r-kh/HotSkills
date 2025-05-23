// Как только брауер прочёл HTML (инструкцию) и построил DOM (каркас) - можно слушать элменты DOM (Document Object Model) //
document.addEventListener('DOMContentLoaded', function () {
    /* Этот код выполнится, когда HTML будет загружен и готов к работе
       Если удалить - весь скрипт может выполниться до загрузки DOM-элементов и сломаться. */


    let cachedSalariesData = null;
    let cachedVacancyData = null;
    // глобальная переменная для региона
    let currentRegion = 'moscow';

    // Отображение текущей локализованной даты и времени в элементе с id "current-datetime"
    const now = new Date();
    const dateTimeElement = document.getElementById('current-datetime');
    if (dateTimeElement) {
        dateTimeElement.textContent = now.toLocaleString(undefined, {
            timeZoneName: 'short' // короткое название часового пояса
        });
    }


    // === Сбор данных для графиков через API запрос к Redis/PostgreSQL === //
    async function fetchChartStatistics() {
        const res = await fetch('/api/vacancy-statistics');
        if (!res.ok) throw new Error(`API: ${res.status} - ${await res.text()}`);
        return res.json();
    }


    // === Адаптивная верстка (для легенды) === //
    const isMobile = window.innerWidth <= 600;


    // === Базовый макет графиков (ось Y, отступы, шрифт и т.д.) === //
    const chartLayout = {
        height: 300, // 👈 устанавливает высоту графика в пикселях
        yaxis: {
            title: {
                text: 'Количество открытых вакансий',
                standoff: 20,
            },
            tickformat: ',.0f',
            automargin: true
        },
        margin: {
            t: 30, b: 80, l: 60, r: 30
        },
        hovermode: 'closest',
        showlegend: true,
        font: {
            family: 'Exo 2, sans-serif',
            size: isMobile ? 11 : 12,  // уменьшенный общий шрифт
            weight: 'bold'
        },
        legend: {
            orientation: 'h',
            x: 0.5,
            y: 1.2,      // увеличиваем отступ вниз, дефолтное -0.2 (вниз отрицательные значения, вверх положительные)
            xanchor: 'center',
            yanchor: 'top',
            font: {size: 12},
            bgcolor: 'rgba(255,255,255,0)',
            borderwidth: 0,
            itemclick: 'toggleothers',  // одиночный выбор
        }
    };


    // === Часовой график (отталкивается от базового (Y), имеет X по часам) === //
    const hourlyChartLayout = (() => {
        const end = new Date(now);
        end.setHours(now.getHours() + 1, 0, 0, 0);

        const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
        const startReserve = new Date(start.getTime() - 1 * 60 * 60 * 1000);

        const tickVals = [];
        const tickTexts = [];

        for (let t = new Date(start); t <= now; t.setHours(t.getHours() + 1)) {
            if (!isMobile || t.getHours() % 2 === 0) {  // Если не мобильный — все часы, если мобильный — только четные
                tickVals.push(new Date(t));
                tickTexts.push(t.getHours().toString().padStart(2, '0') + ':00');
            }
        }

        return {
            ...chartLayout,
            xaxis: {
                type: 'date',
                tickvals: tickVals,
                ticktext: tickTexts,
                tickangle: -90,
                range: [startReserve, end],
                automargin: true
            }
        };
    })();


    // === Дневной график (отталкивается от базового (Y), имеет X по дням) === //
    const dailyChartLayout = (() => {
        const daysToShow = 15;
        const end = new Date(now);
        const extendedEnd = new Date(end.getTime() + 24 * 60 * 60 * 1000);
        end.setHours(23, 59, 59, 999);

        const start = new Date(end.getTime() - (daysToShow - 1) * 24 * 60 * 60 * 1000);
        const startReserve = new Date(start.getTime() - 12 * 60 * 60 * 1000); // запас слева

        const tickVals = [];
        const tickTexts = [];

        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            tickVals.push(new Date(d));
            tickTexts.push(`${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`);
        }

        return {
            ...chartLayout,
            xaxis: {
                type: 'date',
                tickvals: tickVals,
                ticktext: tickTexts,
                tickangle: -90,
                automargin: true,
                range: [startReserve, extendedEnd],
                tickmode: 'array',
                dtick: 24 * 60 * 60 * 1000
            }
        };
    })();


    // === Языки программирования (Названия на графике, цвета и ключи) === //
    const languagesDesign = [
        {name: '1С', color: '#e31e24', key: 'one_c'},
        {name: 'C#', color: 'purple', key: 'csharp'},
        {name: 'Go', color: '#00ADD8', key: 'go'},
        {name: 'C++', color: 'green', key: 'cpp'},
        {name: 'PHP', color: '#68217A', key: 'php'},
        {name: 'Dart', color: '#00B4AB', key: 'dart'},
        {name: 'Java', color: '#f89820', key: 'java'},
        {name: 'Ruby', color: '#D10000', key: 'ruby'},
        {name: 'Scala', color: '#DC322F', key: 'scala'},
        {name: 'Swift', color: '#FF6F00', key: 'swift'},
        {name: 'Kotlin', color: '#7F52FF', key: 'kotlin'},
        {name: 'Python', color: 'blue', key: 'python'},
        {name: 'JavaScript', color: 'gold', key: 'javascript'},
        {name: 'TypeScript', color: '#3178C6', key: 'typescript'}
    ];


    // === Разработчик ПО (Название на графике, цвет) === //
    const developerDesign = {
        color: 'crimson',
        name: 'Разработчик ПО',
    };


    function renderChart({
                             htmlContainerId,       // название элемента/таблицы в файле html
                             dataLines,             // массив с данными для отрисовки
                             designLines,           // массив дизайнов линий или одна линия
                             switchable = false,    // можно ли переключать daily/hourly
                             defaultView,           // 'daily' или 'hourly'
                             showLegend = true,     // показывать ли легенду справа
                             region = 'moscow'       // Новый параметр
                         }) {

        const buildTraces = (data, design) => {
            if (!design) return [];

            const traces = (Array.isArray(design) ? design : [design]).map(object => {
                const d = data[object.key] || data;

                const vals = d[defaultView];
                if (!vals) return null;

                // 🆕 Проверка: если vals — это массив объектов { date, count }
                if (Array.isArray(vals) && vals.length > 0 && 'date' in vals[0] && 'count' in vals[0]) {
                    return {
                        x: vals.map(v => new Date(v.date)),
                        y: vals.map(v => v.count),
                        mode: 'lines+markers',
                        name: object.name + '\u00A0\u00A0\u00A0\u00A0',
                        marker: {color: object.color},
                        line: {shape: 'linear', width: 2},
                        hovertemplate: '%{y}<extra></extra>'
                    };
                }

                // 🧠 Обычная логика (moscow/russia)
                const x = defaultView === 'daily'
                    ? vals.days.map(d => {
                        const date = new Date(d);
                        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
                    })
                    : vals.hours.map(h => {
                        const date = new Date(h);
                        return new Date(
                            date.getFullYear(),
                            date.getMonth(),
                            date.getDate(),
                            date.getHours(),
                            date.getMinutes(),
                            date.getSeconds(),
                            date.getMilliseconds()
                        );
                    });

                let y = [];
                if (region === 'moscow') {
                    y = vals.moscow_counts;
                } else if (region === 'russia') {
                    y = vals.russia_counts;
                } else {
                    y = vals.counts || [];
                }

                return {
                    x, y,
                    mode: 'lines+markers',
                    name: object.name + '\u00A0\u00A0\u00A0\u00A0',
                    marker: {color: object.color},
                    line: {shape: 'linear', width: 2},
                    hovertemplate: '%{y}<extra></extra>'
                };
            }).filter(Boolean);

            return traces.length > 1
                ? traces.sort((a, b) => b.y[b.y.length - 1] - a.y[a.y.length - 1])
                : traces;
        };

        const doRender = () => {
            const traces = buildTraces(dataLines, designLines);
            if (!traces.length) return;

            // Очищаем контейнер перед отрисовкой нового графика
            Plotly.purge(htmlContainerId);

            const layout = {
                ...(defaultView === 'daily' ? dailyChartLayout : hourlyChartLayout),
                showlegend: showLegend,
                dragmode: false // Отключаем zoom режим
            };

            Plotly.react(htmlContainerId, traces, layout, {displayModeBar: false, responsive: true});
        };

        doRender();

        if (switchable) {
            document.getElementById(htmlContainerId)?.addEventListener('click', () => {
                defaultView = defaultView === 'daily' ? 'hourly' : 'daily';
                doRender();
            });
        }
    }


    // === Основной запуск === //
    async function initCharts(region = 'moscow') {
        try {
            const data = await fetchChartStatistics();

            renderChart({
                htmlContainerId: 'chart_software_developer',
                dataLines: { software_developer: data.software_developer },
                designLines: developerDesign,
                switchable: true,
                defaultView: 'hourly',
                showLegend: false,
                region // передаем регион
            });

            renderChart({
                htmlContainerId: 'chart_all_languages',
                dataLines: data,
                designLines: languagesDesign,
                switchable: false,
                defaultView: 'daily',
                showLegend: true,
                region
            });

        } catch (e) {
            console.error('Ошибка загрузки данных или отрисовки графиков:', e);
        }
    }

    // Запуск
    initCharts('russia');


    // === Переключатель Москва/Россия === //
    function initRegionTabs() {

        // Получаем все элементы со страницы с классом .tab
        const tabs = document.querySelectorAll('.tab');

        // Назначаем обработчики кликов (чтобы вкладки реагировали на клики)
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {

                // Удаляем активный класс у всех вкладок (иначе все вкладки будут "активными")
                tabs.forEach(t => t.classList.remove('active'));

                // Добавляем класс active текущей вкладке (иначе визуально не будет понятно, какая вкладка выбрана)
                tab.classList.add('active');

                currentRegion = tab.dataset.value;
                updateSalaryTable(currentRegion);
            });
        });

        // Загрузка данных по умолчанию (Москва)
        updateSalaryTable(currentRegion);
    }

    initRegionTabs();


    async function updateSalaryTable(region) {
        try {
            if (!cachedSalariesData || !cachedVacancyData) {
                const [salariesRes, vacancyRes] = await Promise.all([
                    fetch("/api/salaries"),
                    fetch("/api/vacancy-statistics")
                ]);

                [cachedSalariesData, cachedVacancyData] = await Promise.all([
                    salariesRes.json(),
                    vacancyRes.json()
                ]);
            }

            const tbody = document.querySelector(".salary-table tbody");
            tbody.innerHTML = "";

            cachedSalariesData.forEach(lang => {
                const tr = document.createElement("tr");
                tr.onclick = () => location.href = `/${lang.code.toLowerCase()}`;

                const tdLogo = document.createElement("td");
                const img = document.createElement("img");
                img.src = `/static/logos/${lang.code}.webp`;
                img.alt = lang.name;
                tdLogo.appendChild(img);
                tdLogo.appendChild(document.createTextNode(lang.name));
                tr.appendChild(tdLogo);

                const langKey = lang.code.toLowerCase();
                const langVacData = cachedVacancyData[langKey];

                let vacancyCount = '';
                if (langVacData && langVacData.daily && langVacData.daily[region + '_counts'] && langVacData.daily[region + '_counts'].length > 0) {
                    const counts = langVacData.daily[region + '_counts'];
                    vacancyCount = counts[counts.length - 1] || '';
                }

                const tdVacancies = document.createElement("td");
                tdVacancies.textContent = vacancyCount;
                tr.appendChild(tdVacancies);

                const salaries = lang[region] || lang["russia"] || [];
                const normalized = [...salaries];
                while (normalized.length < 4) normalized.push('');

                normalized.forEach(value => {
                    const td = document.createElement("td");
                    td.innerHTML = value;
                    tr.appendChild(td);
                });

                tbody.appendChild(tr);
            });

            addTableSorting();

        } catch (error) {
            console.error("Ошибка при загрузке таблицы зарплат и вакансий:", error);
        }
    }


// Состояние сортировки
    let currentSort = {
        columnIndex: null,
        ascending: true
    };

    function addTableSorting() {
        const headers = document.querySelectorAll(".salary-table th");

        headers.forEach((th, index) => {
            if (!th.hasAttribute("data-sortable")) return;

            th.style.cursor = "pointer";

            th.onclick = () => {
                const ascending = currentSort.columnIndex === index ? !currentSort.ascending : true;
                currentSort = {columnIndex: index, ascending};

                // Удаляем классы сортировки со всех заголовков
                headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));

                // Добавляем текущий класс
                th.classList.add(ascending ? 'sort-asc' : 'sort-desc');

                sortTableByColumn(index, ascending);
            };
        });
    }

    function sortTableByColumn(columnIndex, ascending = true) {
        const tbody = document.querySelector(".salary-table tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));

        rows.sort((a, b) => {
            let aValue, bValue;

            // Если сортируем по первому столбцу (название языка), достаём чистый текст из узла
            if (columnIndex === 0) {
                aValue = getLanguageNameFromCell(a.children[columnIndex]);
                bValue = getLanguageNameFromCell(b.children[columnIndex]);
            } else {
                aValue = a.children[columnIndex].textContent.trim();
                bValue = b.children[columnIndex].textContent.trim();
            }

            const aNum = parseFloat(aValue.replace(/\s/g, '').replace(',', '.'));
            const bNum = parseFloat(bValue.replace(/\s/g, '').replace(',', '.'));

            if (isNaN(aNum) || isNaN(bNum)) {
                return ascending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
            } else {
                return ascending ? aNum - bNum : bNum - aNum;
            }
        });

        rows.forEach(row => tbody.appendChild(row));
    }


// Вызов при старте
//     updateSalaryTable("russia");

    function getLanguageNameFromCell(cell) {
        // Предполагаем, что картинка — первый ребёнок, а текст — второй (узел с текстом)
        // Можно взять текст узла после img:
        for (const node of cell.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() !== '') {
                return node.textContent.trim();
            }
        }
        return cell.textContent.trim(); // fallback
    }

});