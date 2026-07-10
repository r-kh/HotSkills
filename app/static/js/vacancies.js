import {
    loadVacanciesIfNeeded,
    getVacanciesData
} from "./api.js";

let tableData = [];
let ascending = false;

document.addEventListener("DOMContentLoaded", async () => {

    await loadVacanciesIfNeeded();

    tableData = [...getVacanciesData().vacancies];

    renderTable();
    addSorting();
});

function renderTable() {

    const tbody = document.querySelector(".salary-table tbody");

    tbody.innerHTML = "";

    tableData.forEach(vacancy => {

        const tr = document.createElement("tr");

        // Переход на страницу вакансии HH.ru в новой вкладке
        tr.style.cursor = "pointer";
        tr.addEventListener("click", () => {
            window.open(`https://hh.ru/vacancy/${vacancy.id}`, "_blank");
        });

        tr.innerHTML = `
            <td>${vacancy.name}</td>
            <td>${vacancy.date}</td>
            <td>${vacancy.responses}</td>
            <td></td>
            <td></td>
        `;

        tbody.appendChild(tr);
    });

}

function addSorting() {

    // 3-я колонка ("Откликов")
    const th = document.querySelectorAll(".salary-table th")[2];

    th.style.cursor = "pointer";

    th.addEventListener("click", () => {

        ascending = !ascending;

        tableData.sort((a, b) =>
            ascending
                ? a.responses - b.responses
                : b.responses - a.responses
        );

        renderTable();
    });

}