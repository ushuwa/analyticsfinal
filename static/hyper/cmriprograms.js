function initCMRIPrograms() {
    const ppiBody = document.querySelector("#ppiTables tbody");
    const riskBody = document.querySelector("#riskTables tbody");
    const citySelect = document.querySelector("#citySelect");
    const userSearch = document.querySelector("#user-search");
    const rowsSelect = document.querySelector("#rowsPerPageSelect");
    const ppiInfo = document.querySelector("#ppi-info");
    const ppiPagination = document.querySelector("#ppi-pagination");

    let allPPIData = []; 
    let filteredPPIData = []; 
    let currentPage = 1;
    let rowsPerPage = 10;

    /* =========================
       LOAD PPI TABLE
    ========================= */
    async function loadPPITable() {
        ppiBody.innerHTML = `<tr><td colspan="9" class="text-center p-4"><div class="spinner-border spinner-border-sm" style="color: #346739"></div></td></tr>`;
        try {
            const response = await fetch("/api/ppi/likelihood-table?limit=1000"); 
            const result = await response.json();
            allPPIData = result.data || [];
            filteredPPIData = [...allPPIData]; 

            populateAreaDropdown(allPPIData);
            renderPPITable(); 
        } catch (error) {
            ppiBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load data</td></tr>`;
        }
    }

    /* =========================
       RENDER LOGIC
    ========================= */
    function renderPPITable() {
        ppiBody.innerHTML = "";
        
        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;
        const paginatedData = filteredPPIData.slice(startIndex, endIndex);

        if (!paginatedData.length) {
            ppiBody.innerHTML = `<tr><td colspan="9" class="text-center p-4">No matching records found</td></tr>`;
            updatePaginationUI(0);
            return;
        }

        paginatedData.forEach(row => {
            ppiBody.insertAdjacentHTML("beforeend", `
                <tr>
                    <td><strong>${row.cid}</strong></td>
                    <td>${row.name}</td>
                    <td class="text-muted">${row.area}</td>
                    <td>${row.unit}</td>
                    <td>${row.center}</td>
                    <td class="text-center">${row.ppiScore}</td>
                    <td><span class="badge bg-success-subtle text-success">${row.classification}</span></td>
                    <td>${(row.povertyLikelihood * 100).toFixed(2)}%</td>
                    <td>${row.predictedPovertyLikelihood}</td>
                </tr>
            `);
        });

        updatePaginationUI(filteredPPIData.length);
    }

    function updatePaginationUI(totalRows) {
        const totalPages = Math.ceil(totalRows / rowsPerPage);
        const startEntry = totalRows === 0 ? 0 : (currentPage - 1) * rowsPerPage + 1;
        const endEntry = Math.min(currentPage * rowsPerPage, totalRows);
        
        ppiInfo.innerText = `Showing ${startEntry} to ${endEntry} of ${totalRows} entries`;
        ppiPagination.innerHTML = "";

        // Prev
        ppiPagination.insertAdjacentHTML("beforeend", `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" data-page="${currentPage - 1}">&laquo;</a>
            </li>
        `);

        // Pages
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                ppiPagination.insertAdjacentHTML("beforeend", `
                    <li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" data-page="${i}">${i}</a>
                    </li>
                `);
            } else if (i === currentPage - 2 || i === currentPage + 2) {
                ppiPagination.insertAdjacentHTML("beforeend", `<li class="page-item disabled"><span class="page-link">...</span></li>`);
            }
        }

        // Next
        ppiPagination.insertAdjacentHTML("beforeend", `
            <li class="page-item ${currentPage === totalPages || totalPages === 0 ? 'disabled' : ''}">
                <a class="page-link" data-page="${currentPage + 1}">&raquo;</a>
            </li>
        `);
    }

    /* =========================
       FILTERS & EVENTS
    ========================= */
    function handleFilters() {
        const areaFilter = citySelect.value.toLowerCase();
        const searchFilter = userSearch.value.toLowerCase();

        filteredPPIData = allPPIData.filter(item => {
            const matchesArea = areaFilter === "" || item.area.toLowerCase() === areaFilter;
            const matchesCID = item.cid.toString().toLowerCase().includes(searchFilter);
            return matchesArea && matchesCID;
        });

        currentPage = 1; 
        renderPPITable();
    }

    function populateAreaDropdown(data) {
        const areas = [...new Set(data.map(item => item.area))].sort();
        citySelect.innerHTML = `<option value="">All Areas</option>`;
        areas.forEach(area => {
            citySelect.insertAdjacentHTML("beforeend", `<option value="${area}">${area}</option>`);
        });
    }

    // Risk Table Sort
    async function loadRiskTable() {
        riskBody.innerHTML = "";
        try {
            const response = await fetch("/api/ppi/top-risk-factors");
            const result = await response.json();
            let riskData = result.data || [];
            riskData.sort((a, b) => b.percentage - a.percentage);

            riskData.forEach((row, index) => {
                const isTop = index === 0 ? 'style=" border-left: 4px solid #ffc107;"' : '';
                riskBody.insertAdjacentHTML("beforeend", `
                    <tr ${isTop}>
                        <td><strong>${row.questionNo}</strong></td>
                        <td style="width: 45%">
                            <div class="progress" style="height: 6px; margin-bottom: 2px;">
                                <div class="progress-bar ${index === 0 ? 'bg-danger' : 'bg-warning'}" style="width: ${row.percentage}%"></div>
                            </div>
                            <small class="text-muted">${row.percentage.toFixed(2)}%</small>
                        </td>
                        <td><strong>${row.averageScore.toFixed(2)}</strong></td>
                    </tr>
                `);
            });
        } catch (e) { console.error(e); }
    }

    /* =========================
       LISTENERS
    ========================= */
    rowsSelect.addEventListener("change", () => {
        rowsPerPage = parseInt(rowsSelect.value);
        currentPage = 1;
        renderPPITable();
    });

    citySelect.addEventListener("change", handleFilters);
    userSearch.addEventListener("input", handleFilters);

    ppiPagination.addEventListener("click", (e) => {
        const targetPage = parseInt(e.target.dataset.page);
        if (targetPage && targetPage !== currentPage) {
            currentPage = targetPage;
            renderPPITable();
            document.querySelector(".table-responsive-ppi").scrollTop = 0;
        }
    });

    /* =========================
       Poverty Movement
    ========================= */
    async function loadPovertyMovement() {
        const ppiMovementContainer = document.querySelector(".movement-stats");
        const improvedCount = document.querySelector("#improved-count");
        const declinedCount = document.querySelector("#declined-count");

        try {
            // Adjust IDs as needed for your specific batch selection logic
            const response = await fetch("/api/ppi/poverty-movement?currentBatchId=1&previousBatchId=2");
            const result = await response.json();

            if (result.success) {
                const summary = result.data.summary;
                const riskFactors = result.data.topRiskFactors;

                // 1. Update Summary Counters (Top Row)
                // Note: Ensure you add these IDs to your HTML spans for 'Improved' and 'Declined'
                if(improvedCount) improvedCount.innerText = summary.improved.toLocaleString();
                if(declinedCount) declinedCount.innerText = summary.declined.toLocaleString();

                // 2. Update Movement Stats List
                // We target the container we built in the previous step
                const statsContainer = document.querySelector(".movement-stats");
                if (statsContainer) {
                    statsContainer.innerHTML = `
                        <p class="row mb-2">
                            <span class="col-2 fw-bold text-success" style="font-size: 1.2rem;">${summary.graduatedFromPagtalubo.toLocaleString()}</span> 
                            <span class="col-8 fw-bold text-dark ms-2">Clients graduated from Pagtalubo</span>
                        </p>
                        <p class="row mb-2">
                            <span class="col-2 fw-bold text-primary" style="font-size: 1.2rem;">${summary.averagePpiImprovement >= 0 ? '+' : ''}${summary.averagePpiImprovement}</span> 
                            <span class="col-8 fw-bold text-dark ms-2">Average PPI improvement</span>
                        </p>
                        <p class="row mb-2">
                            <span class="col-2 fw-bold text-primary" style="font-size: 1.2rem;">${summary.povertyReductionRate}%</span> 
                            <span class="col-8 fw-bold text-dark ms-2">Poverty Reduction Rate</span>
                        </p>
                    `;
                }

                // 3. Render Risk Table from the same response
                renderRiskTable(riskFactors);
            }
        } catch (error) {
            console.error("Error loading movement data:", error);
        }
    }

    loadPPITable();
    loadRiskTable();
    loadPovertyMovement();
    
}