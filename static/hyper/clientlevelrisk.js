function initClientlevelrisk() {

    // Selectors
    const atRiskBody = document.querySelector("#atRiskTable tbody");
    const selectBranch = document.querySelector("#selectBranchLevel");
    const userSearch = document.querySelector("#user-search");
    const rowsSelect = document.querySelector("#rowsPerPage");
    const tableInfo = document.querySelector("#tableInfo");
    const paginationContainer = document.querySelector("#paginationControls");

    // State
    let allClients = []; 
    let filteredClients = []; 
    let currentPage = 1;
    let rowsPerPage = 10;

    async function loadAtRiskData() {
        atRiskBody.innerHTML = `<tr><td colspan="13" class="text-center p-5"><div class="spinner"></div><p>Loading...</p></td></tr>`;
        try {
            const response = await fetch("/api/risk/client-at-risk"); 
            const result = await response.json();
            
            if (result.success) {
                allClients = result.data.clients || [];
                updateSummaryCards(result.data.summary);
                filteredClients = [...allClients];
                renderTable(); 
            }
        } catch (error) {
            console.error("API Error:", error);
            atRiskBody.innerHTML = `<tr><td colspan="13" class="text-center text-danger p-4">Error loading data. Check console for details.</td></tr>`;
        }
    }

    function renderTable() {
        atRiskBody.innerHTML = "";
        
        // Calculate bounds
        const totalRows = filteredClients.length;
        const totalPages = Math.ceil(totalRows / rowsPerPage) || 1;

        // Validation: Ensure currentPage doesn't exceed totalPages after filtering
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;
        const paginatedData = filteredClients.slice(startIndex, endIndex);

        if (paginatedData.length === 0) {
            atRiskBody.innerHTML = `<tr><td colspan="13" class="text-center p-5 text-muted">No records found matching your filters.</td></tr>`;
            updatePaginationUI(0, 1);
            return;
        }

        const curr = (val) => new Intl.NumberFormat('en-PH', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        }).format(val || 0);

        paginatedData.forEach(client => {
            let severityColor = '#333';
            const sev = (client.riskSeverity || "").toLowerCase();
            if (sev.includes('high')) severityColor = '#e87a6d';
            else if (sev.includes('mod')) severityColor = '#5bc0de';
            else if (sev.includes('low')) severityColor = '#5cb85c';

            atRiskBody.insertAdjacentHTML("beforeend", `
                <tr>
                    <td><strong>${client.cid}</strong></td>
                    <td style="text-transform: uppercase; font-weight: 600;">${client.name}</td>
                    <td>${client.area}</td>
                    <td>${client.unit}</td>
                    <td>${client.center}</td>
                    <td>${client.loanType}</td>
                    <td class="text-center">${curr(client.loanPrincipal)}</td>
                    <td class="text-center">${curr(client.loanBalance)}</td>
                    <td class="text-center">${client.loanTerm}</td>
                    <td class="text-center">${client.daysArrear}</td>
                    <td class="text-center">${client.riskScore}</td>
                    <td class="text-center"><span style="color: ${severityColor}; font-weight: 800;">${client.riskSeverity}</span></td>
                    <td style="font-size: 0.75rem; color: #666;">${client.recommendedAction}</td>
                </tr>
            `);
        });

        updatePaginationUI(totalRows, totalPages);
    }

    function updatePaginationUI(totalRows, totalPages) {
        const startEntry = totalRows === 0 ? 0 : (currentPage - 1) * rowsPerPage + 1;
        const endEntry = Math.min(currentPage * rowsPerPage, totalRows);
        
        // Update Info Text
        if (tableInfo) {
            tableInfo.innerText = `Showing ${startEntry} to ${endEntry} of ${totalRows} entries`;
        }

        // Generate Buttons
        if (paginationContainer) {
            paginationContainer.innerHTML = `
                <div class="btn-group shadow-sm">
                    <button class="btn btn-sm btn-outline-secondary" ${currentPage === 1 ? 'disabled' : ''} id="prevPage">
                        &laquo; Prev
                    </button>
                    <button class="btn btn-sm btn-light border" disabled style="min-width: 100px;">
                        Page ${currentPage} of ${totalPages}
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" ${currentPage >= totalPages ? 'disabled' : ''} id="nextPage">
                        Next &raquo;
                    </button>
                </div>
            `;

            // Attach Listeners immediately after injecting HTML
            document.getElementById("prevPage")?.addEventListener("click", () => {
                currentPage--;
                renderTable();
            });
            document.getElementById("nextPage")?.addEventListener("click", () => {
                currentPage++;
                renderTable();
            });
        }
    }

    function handleFilters() {
        const searchTerm = userSearch.value.toLowerCase().trim();
        const branchLevel = selectBranch.value;

        filteredClients = allClients.filter(item => {
            const matchesSearch = item.cid.toString().toLowerCase().includes(searchTerm) || 
                                  item.name.toLowerCase().includes(searchTerm);
            
            // Fixed Branch Filter logic
            let matchesBranch = true;
            if (branchLevel !== "area") {
                // This checks if the data has a 'level' property matching the dropdown
                matchesBranch = item.level === branchLevel || 
                                item.branch_level === branchLevel;
            }

            return matchesSearch && matchesBranch;
        });

        currentPage = 1; // Reset to page 1 on every filter change!
        renderTable();
    }

    function updateSummaryCards(summary) {
        if (!summary) return;
        const fmt = (num) => new Intl.NumberFormat().format(num || 0);
        // Using IDs to ensure accuracy
        const lowBox = document.querySelector(".bg-low");
        const modBox = document.querySelector(".bg-moderate");
        const highBox = document.querySelector(".bg-high");
        
        if (lowBox) lowBox.innerText = fmt(summary.lowRisk);
        if (modBox) modBox.innerText = fmt(summary.moderateRisk);
        if (highBox) highBox.innerText = fmt(summary.highRisk);
    }

    // Listeners
    rowsSelect.addEventListener("change", (e) => { 
        rowsPerPage = parseInt(e.target.value); 
        currentPage = 1; 
        renderTable(); 
    });

    userSearch.addEventListener("input", handleFilters);
    selectBranch.addEventListener("change", handleFilters);

    // Run
    loadAtRiskData();

}