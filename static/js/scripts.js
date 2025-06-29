// Импортируем функции из table.js и charts.js в самом начале файла (импорты только в верхнем уровне модуля)
import {initCharts}      from './charts.js';
import {initSalaryTable} from './table.js';

// Как только брауер прочёл HTML (инструкцию) и построил DOM (каркас) - можно слушать элменты DOM (Document Object Model) //
document.addEventListener('DOMContentLoaded', function () {
    /* Этот код выполнится, когда HTML будет загружен и готов к работе
       Если удалить - весь скрипт может выполниться до загрузки DOM-элементов и сломаться. */


    // --- Локализованная текущая дата --- //
    // Получаем ссылку на HTML-элемент с id "current-date"
    document.getElementById('current-date').textContent =
        // Получаем текущую дату, и отображаем её в этом HTML-элементе в локализованном формате
        (d => `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`)(new Date());// (формат YYYY.MM.DD)


    // --- Локализованные текущие дата и время --- //
    // Получаем ссылку на HTML-элемент с id "current-datetime"
    document.getElementById('current-datetime').textContent =
        // Получаем текущие дату и время, и отображаем их в этом HTML-элементе в локализованном формате
        new Date().toLocaleString(undefined, {timeZoneName: 'short'}); // (включая короткое название часового пояса (например, GMT+3))


    // Запуск графиков
    initCharts();

    // Запуск таблицы с зарплатами и переключателями вкладок
    initSalaryTable();
});