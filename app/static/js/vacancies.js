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

        tr.innerHTML = `
            <td>${vacancy.name}</td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
        `;

        tbody.appendChild(tr);
    });

}