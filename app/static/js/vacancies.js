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


function formatLaborContract(value) {

    if (value === true) {
        return "Трудовой договор";
    }

    return "—";
}


function formatSalary(salary) {

    if (!salary) {
        return "—";
    }

    const from = salary[0];
    const to = salary[1];

    if (from && to && from === to) {return `${from.toLocaleString("ru-RU")} ₽`;}

    if (from && to) {return `${from.toLocaleString("ru-RU")} - ${to.toLocaleString("ru-RU")} ₽`;}

    if (from) {return `от ${from.toLocaleString("ru-RU")} ₽`;}

    if (to) {return `до ${to.toLocaleString("ru-RU")} ₽`;}

    return "—";
}


function updateSortIcons(activeColumn) {

    const headers = document.querySelectorAll(".salary-table th");

    headers.forEach((th, index) => {

        th.classList.remove("sort-asc", "sort-desc");

        if (index === activeColumn) {

            th.classList.add(
                sortState.ascending
                    ? "sort-asc"
                    : "sort-desc"
            );
        }
    });
}


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
            <td>${vacancy.Работодатель}</td>
            <td>${vacancy.date}</td>
            <td>${vacancy.responses}</td>
            <td>${formatLaborContract(vacancy.labor_contract)}</td>
            <td>${formatSalary(vacancy.salary)}</td>
        `;

        tbody.appendChild(tr);
    });

}

function addSorting() {

    const headers = document.querySelectorAll(".salary-table th");


    // 0-я колонка ("Вакансия")
    headers[0].style.cursor = "pointer";

    headers[0].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 0 ? !sortState.ascending : true;

        sortState.column = 0;

        tableData.sort((a, b) => {

            const nameA = a.name?.toLowerCase() ?? "";
            const nameB = b.name?.toLowerCase() ?? "";

            return sortState.ascending
                ? nameA.localeCompare(nameB, "ru")
                : nameB.localeCompare(nameA, "ru");
        });
        updateSortIcons(0);
        renderTable();
    });


    // 1-я колонка ("Работодатель")
    headers[1].style.cursor = "pointer";

    headers[1].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 1 ? !sortState.ascending : true;

        sortState.column = 1;

        tableData.sort((a, b) => {

            const companyA = a.Работодатель?.toLowerCase() ?? "";
            const companyB = b.Работодатель?.toLowerCase() ?? "";

            return sortState.ascending
                ? companyA.localeCompare(companyB, "ru")
                : companyB.localeCompare(companyA, "ru");
        });
        updateSortIcons(1);
        renderTable();
    });



    // 2-я колонка ("Опубликована")
    headers[2].style.cursor = "pointer";
    headers[2].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 2 ? !sortState.ascending : false;
        sortState.column = 2;

        tableData.sort((a, b) =>
            sortState.ascending
                ? Date.parse(a.date) - Date.parse(b.date)
                : Date.parse(b.date) - Date.parse(a.date)
        );
        updateSortIcons(2);
        renderTable();
    });

    // 3-я колонка ("Откликов")
    headers[3].style.cursor = "pointer";
    headers[3].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 3 ? !sortState.ascending : false;
        sortState.column = 3;

        tableData.sort((a, b) =>
            sortState.ascending
                ? a.responses - b.responses
                : b.responses - a.responses
        );
        updateSortIcons(3);
        renderTable();
    });


    // 4-я колонка ("Оформление")
    headers[4].style.cursor = "pointer";

    headers[4].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 4 ? !sortState.ascending : false;

        sortState.column = 4;

        tableData.sort((a, b) => {

            const contractA = a.labor_contract ? 1 : 0;
            const contractB = b.labor_contract ? 1 : 0;

            return sortState.ascending
                ? contractA - contractB
                : contractB - contractA;
        });

        updateSortIcons(4);
        renderTable();
    });

    // 5-я колонка ("Оклад")
    headers[5].style.cursor = "pointer";

    headers[5].addEventListener("click", () => {

        sortState.ascending =
            sortState.column === 5 ? !sortState.ascending : false;

        sortState.column = 5;

        tableData.sort((a, b) => {

            const salaryAFrom = a.salary?.[0] ?? 0;
            const salaryATo = a.salary?.[1] ?? salaryAFrom;

            const salaryBFrom = b.salary?.[0] ?? 0;
            const salaryBTo = b.salary?.[1] ?? salaryBFrom;


            if (salaryATo !== salaryBTo) {

                return sortState.ascending
                    ? salaryATo - salaryBTo
                    : salaryBTo - salaryATo;
            }


            return sortState.ascending
                ? salaryAFrom - salaryBFrom
                : salaryBFrom - salaryAFrom;
        });
        updateSortIcons(5);
        renderTable();
    });

}