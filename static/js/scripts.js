// Импортируем функции из table.js и charts.js в самом начале файла (импорты только в верхнем уровне модуля)
import {initCharts}      from './charts.js';
import {initSalaryTable} from './table.js';

// Как только брауер прочёл HTML (инструкцию) и построил DOM (каркас) - можно слушать элменты DOM (Document Object Model) //
document.addEventListener('DOMContentLoaded', function () {
    /* Этот код выполнится, когда HTML будет загружен и готов к работе
       Если удалить - весь скрипт может выполниться до загрузки DOM-элементов и сломаться. */

    // Получаем текущие дату и время
    const now = new Date();
    // Форматируем дату в YYYY.MM.DD
    const date = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`;
    // Получаем локализованное время
    const time = now.toLocaleTimeString();
    // Получаем таймзону
    const tz = now.toLocaleTimeString(undefined, {timeZoneName: 'short'}).split(' ').pop();


    // --- Локализованная текущая дата --- //
    // Получаем ссылку на HTML-элемент с id "current-date" и отображаем текущую дату в локализованном формате
    document.getElementById('current-date').textContent = date;


    // --- Локализованные текущие дата и время --- //
    // Получаем ссылку на HTML-элемент с id "current-datetime" и отображаем текущие дату и время в этом HTML-элементе в локализованном формате
    document.getElementById('current-datetime').textContent = `${date}, ${time} ${tz}`;


    // Запуск графиков
    initCharts();

    // Запуск таблицы с зарплатами и переключателями вкладок
    initSalaryTable();
});