import {
    loadVacanciesIfNeeded,
    getVacanciesData
} from "./api.js";

document.addEventListener("DOMContentLoaded", async () => {

    await loadVacanciesIfNeeded();

    renderTable();
});

function renderTable() {

    const tbody = document.querySelector(".salary-table tbody");

    tbody.innerHTML = "";

    const data = getVacanciesData();

    data.vacancies.forEach(vacancy => {

        const tr = document.createElement("tr");

        // Переход на страницу вакансии HH.ru в новой вкладке
        tr.style.cursor = "pointer";
        tr.addEventListener("click", () => {
            window.open(`https://hh.ru/vacancy/${vacancy.id}`, "_blank");
        });

        tr.innerHTML = `
            <td>${vacancy.name}</td>
            <td></td>
            <td>${vacancy.responses}</td>
            <td></td>
            <td></td>
        `;

        tbody.appendChild(tr);
    });

}