import {
    loadVacanciesIfNeeded,
    getVacanciesData
} from "./api.js";

let tableData = [];
let sortState = {
    column: null,
    ascending: false
};

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

    const headers = document.querySelectorAll(".salary-table th");

    // 2-я колонка ("Опубликована")
    headers[1].style.cursor = "pointer";
    headers[1].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 1 ? !sortState.ascending : false;
        sortState.column = 1;

        tableData.sort((a, b) =>
            sortState.ascending
                ? Date.parse(a.date) - Date.parse(b.date)
                : Date.parse(b.date) - Date.parse(a.date)
        );

        renderTable();
    });

    // 3-я колонка ("Откликов")
    headers[2].style.cursor = "pointer";
    headers[2].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 2 ? !sortState.ascending : false;
        sortState.column = 2;

        tableData.sort((a, b) =>
            sortState.ascending
                ? a.responses - b.responses
                : b.responses - a.responses
        );

        renderTable();
    });

}