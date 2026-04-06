function initAtriskDashboard() {

    // // 1. Initialize Charts globally so we can update them later
    // let charts = {};

    // const donutOptions = (color, percent) => ({
    //     type: 'doughnut',
    //     data: {
    //         datasets: [{
    //             data: [percent, 100 - percent],
    //             backgroundColor: [color, '#333333'],
    //             borderWidth: 0
    //         }]
    //     },
    //     options: {
    //         cutout: '80%',
    //         responsive: true,
    //         maintainAspectRatio: false,
    //         plugins: { tooltip: { enabled: false }, legend: { display: false } }
    //     }
    // });

    // // Function to load the data
    // async function loadDashboardData() {
    //     try {
    //         // Replace with your actual endpoint if different
    //         const response = await fetch('/api/risk/dashboard');
    //         const result = await response.json();
            
    //         if (result.success) {
    //             renderDashboard(result.data);
    //         }
    //     } catch (error) {
    //         console.error("Error fetching dashboard data:", error);
    //     }
    // }

    // function renderDashboard(data) {
    //     const summary = data.summary;

    //     // 2. Update Circles (Summary)
    //     updateCircle('lowDonut', '#ff6b6b', summary.lowRiskPercentage);
    //     updateCircle('medDonut', '#ff6b6b', summary.mediumRiskPercentage);
    //     updateCircle('highDonut', '#ff6b6b', summary.highRiskPercentage);

    //     // Update the text percentage inside the circles
    //     document.querySelector('#lowDonut + .donut-text').innerText = summary.lowRiskPercentage.toFixed(1) + '%';
    //     document.querySelector('#medDonut + .donut-text').innerText = summary.mediumRiskPercentage.toFixed(1) + '%';
    //     document.querySelector('#highDonut + .donut-text').innerText = summary.highRiskPercentage.toFixed(1) + '%';

    //     // 3. Populate Top High Risk Branches
    //     const branchList = document.querySelector('.list-box:nth-of-type(1)'); // First list box
    //     branchList.innerHTML = `<ol style="font-weight: 700; font-size: 1rem; line-height: 1.8;">
    //         ${data.topHighRiskBranches.map(b => `<li>${b.branch} (${b.highRiskCount} High Risk)</li>`).join('')}
    //     </ol>`;

    //     // 4. Populate Top High Risk Clients
    //     const clientList = document.querySelector('#highRiskClientsList') || document.querySelector('.list-box:nth-of-type(2) ol');
    //     clientList.innerHTML = data.topHighRiskClients.map(c => 
    //         `<li>${c.name} <br><small class="text-muted">${c.name} | Score: ${c.riskScore}</small></li>`
    //     ).join('');

    //     // 5. Update Trend Chart (Using example logic as API is snapshot)
    //     renderTrendChart(summary);
    // }

    // function updateCircle(id, color, percent) {
    //     if (charts[id]) charts[id].destroy();
    //     charts[id] = new Chart(document.getElementById(id), donutOptions(color, percent));
    // }

    // function renderTrendChart(summary) {
    //     const ctx = document.getElementById('riskTrendChart');
    //     if (charts['trend']) charts['trend'].destroy();

    //     charts['trend'] = new Chart(ctx, {
    //         type: 'line',
    //         data: {
    //             labels: ['Current Assessment'],
    //             datasets: [
    //                 { label: 'Low', data: [summary.lowRiskCount], borderColor: '#238b45', backgroundColor: '#238b45', tension: 0.3 },
    //                 { label: 'Med', data: [summary.mediumRiskCount], borderColor: '#5d87ff', backgroundColor: '#5d87ff', tension: 0.3 },
    //                 { label: 'High', data: [summary.highRiskCount], borderColor: '#ff5b5b', backgroundColor: '#ff5b5b', tension: 0.3 }
    //             ]
    //         },
    //         options: {
    //             responsive: true,
    //             maintainAspectRatio: false,
    //             scales: { y: { beginAtZero: true } }
    //         }
    //     });
    // }

    // // Initial load
    // loadDashboardData();
    
    let charts = {};

    const donutOptions = (color, percent) => ({
        type: 'doughnut',
        data: {
            datasets: [{
                data: [percent, 100 - percent],
                backgroundColor: [color, '#333333'], // Light grey background for empty part
                borderWidth: 0
            }]
        },
        options: {
            cutout: '80%',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { tooltip: { enabled: false }, legend: { display: false } }
        }
    });

    async function loadDashboardData() {
        try {
            const response = await fetch('/api/risk/dashboard');
            const result = await response.json();
            if (result.success) renderDashboard(result.data);
        } catch (e) { console.error("Fetch error:", e); }
    }

    function renderDashboard(data) {
        const s = data.summary;

        // 1. Update Circles & Text - Using colors from your reference
        updateCircle('lowDonut', '#ff6b6b', s.lowRiskPercentage);
        updateCircle('medDonut', '#ff6b6b', s.mediumRiskPercentage);
        updateCircle('highDonut', '#ff6b6b', s.highRiskPercentage);

        document.getElementById('lowText').innerText = s.lowRiskPercentage.toFixed(1) + '%';
        document.getElementById('medText').innerText = s.mediumRiskPercentage.toFixed(1) + '%';
        document.getElementById('highText').innerText = s.highRiskPercentage.toFixed(1) + '%';

        // 2. Populate Branches
        // document.getElementById('branchListContainer').innerHTML = `<ol style="font-weight: 700; font-size: 0.8rem; line-height: 1.6;"">
        //     ${data.topHighRiskBranches.map(b => `<li>${b.branch} <small class="text-muted">(${b.highRiskCount})</small></li>`).join('')}
        // </ol>`;
        document.getElementById('branchListContainer').innerHTML = `<ol style="font-weight: 700; font-size: 0.8rem; line-height: 1.6;">
            ${data.topHighRiskBranches.slice(0, 5).map(b => `
                <li>${b.branch} <small class="text-muted">(${b.highRiskCount})</small></li>
            `).join('')}
        </ol>`;

        // 3. Populate Clients
        // document.getElementById('highRiskClientsList').innerHTML = data.topHighRiskClients.map(c => 
        //     `<li>${c.name} <br><small class="text-muted" style="font-size:0.7rem">${c.unit} | Score: ${c.riskScore}</small></li>`
        // ).join('');
        document.getElementById('highRiskClientsList').innerHTML = data.topHighRiskClients.slice(0, 5).map(c => `
            <li>${c.name} <br><small class="text-muted" style="font-size:0.7rem">${c.unit} | Score: ${c.riskScore}</small></li>
        `).join('');

        // 4. Trend Chart
        renderTrendChart(s);
    }

    function updateCircle(id, color, percent) {
        if (charts[id]) charts[id].destroy();
        charts[id] = new Chart(document.getElementById(id), donutOptions(color, percent));
    }

    function renderTrendChart(summary) {
        const ctx = document.getElementById('riskTrendChart');
        if (charts['trend']) charts['trend'].destroy();

        charts['trend'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Current'],
                datasets: [
                    { label: 'Low', data: [summary.lowRiskCount], borderColor: '#238b45', backgroundColor: '#238b45', tension: 0.3, pointRadius: 6 },
                    { label: 'Med', data: [summary.mediumRiskCount], borderColor: '#5d87ff', backgroundColor: '#5d87ff', tension: 0.3, pointRadius: 6 },
                    { label: 'High', data: [summary.highRiskCount], borderColor: '#ff5b5b', backgroundColor: '#ff5b5b', tension: 0.3, pointRadius: 6 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            // THIS FIXES THE RECTANGLE ISSUE:
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 20,
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#eee' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function renderMap(geographicData) {
        geographicData.forEach(item => {
            // Find the province element in the SVG by its ID (location name)
            const provinceElement = document.getElementById(item.location);
            
            if (provinceElement) {
                // Determine color based on averageRiskScore
                let color = '#d3d3d3'; // Default light gray
                const score = item.averageRiskScore;

                if (score > 40) color = '#800020';      // High Risk (Crimson)
                else if (score > 30) color = '#ffbc00'; // Medium Risk (Yellow)
                else if (score > 0) color = '#0acf97';  // Low Risk (Green)

                // Apply color and add a tooltip data attribute
                provinceElement.style.fill = color;
                provinceElement.setAttribute('title', `${item.location}: ${score} Avg Score`);
                
                // Optional: Add hover effect
                provinceElement.addEventListener('mouseover', () => {
                    provinceElement.style.opacity = "0.7";
                });
                provinceElement.addEventListener('mouseout', () => {
                    provinceElement.style.opacity = "1";
                });
            }
        });
    }

    loadDashboardData();

}

