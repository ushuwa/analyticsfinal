function initPovertyInsights() {

    const select = document.getElementById("selectBranchLevel");
    const ppiBody = document.querySelector("#povertyIndexTables tbody");
    const paginationControls = document.getElementById("paginationControls");
    const rowsPerPageSelect = document.getElementById("rowsPerPage");
    const tableInfo = document.getElementById("tableInfo");

    let currentPage = 1;
    let rowsPerPage = parseInt(rowsPerPageSelect.value);
    let fullData = [];

    async function loadTables(branchLevel = "area_office") {

        ppiBody.innerHTML = `
            <tr>
                <td colspan="6" class="table-loading">
                    <div class="spinner"></div>
                </td>
            </tr>
        `;

        try {

            const response = await fetch(`/api/ppi/branch-analysis?branchLevel=${branchLevel}`);
            const result = await response.json();

            fullData = result.data || [];
            currentPage = 1;

            renderTable();

        } catch (error) {

            ppiBody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-loading">
                        Failed to load data
                    </td>
                </tr>
            `;

            console.error(error);
        }
    }

    function renderTable() {

        ppiBody.innerHTML = "";

        if (!fullData.length) {
            ppiBody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-loading">
                        No data available
                    </td>
                </tr>
            `;
            paginationControls.innerHTML = "";
            tableInfo.innerHTML = "";
            return;
        }

        const start = (currentPage - 1) * rowsPerPage;
        const end = Math.min(start + rowsPerPage, fullData.length);
        const pageData = fullData.slice(start, end);

        pageData.forEach(row => {
            ppiBody.insertAdjacentHTML("beforeend", `
                <tr>
                    <td>${row.branch}</td>
                    <td class="text-center">${row.totalClients}</td>
                    <td class="text-center">${row.totalPagtalubo}</td>
                    <td class="text-center">${row.totalRegular}</td>
                    <td class="text-center">${row.pagtaluboPercentage}%</td>
                    <td class="text-center">${row.regularPercentage}%</td>
                </tr>
            `);
        });

        tableInfo.innerHTML = `Showing ${start + 1} to ${end} of ${fullData.length} entries`;

        renderPagination();
    }

    function renderPagination() {

        const totalPages = Math.ceil(fullData.length / rowsPerPage);
        let buttons = "";

        // Prev button
        buttons += `
            <button class="btn btn-sm btn-light" ${currentPage === 1 ? "disabled" : ""}
                onclick="changePage(${currentPage - 1})">
                «
            </button>
        `;

        // Smart page numbers (max 5 visible)
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            buttons += `
                <button class="btn btn-sm ${i === currentPage ? 'btn-primary' : 'btn-light'}"
                    onclick="changePage(${i})">
                    ${i}
                </button>
            `;
        }

        // Next button
        buttons += `
            <button class="btn btn-sm btn-light" ${currentPage === totalPages ? "disabled" : ""}
                onclick="changePage(${currentPage + 1})">
                »
            </button>
        `;

        paginationControls.innerHTML = buttons;
    }

    // global
    window.changePage = function(page) {
        currentPage = page;
        renderTable();
    }

    /* Events */
    select.addEventListener("change", function () {
        loadTables(this.value || "area_office");
    });

    rowsPerPageSelect.addEventListener("change", function () {
        rowsPerPage = parseInt(this.value);
        currentPage = 1;
        renderTable();
    });

    /* Initial load */
    loadTables();
}