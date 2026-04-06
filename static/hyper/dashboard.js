function initDashboard() {
const ppiScoreEl = document.getElementById("ppiAvgScore");
    const totalClientsEl = document.getElementById("totalClients");
    const totalPagtaluboEl = document.getElementById("totalPagtalubo");
    const totalRegularEl = document.getElementById("totalRegular");
    const filterSelect = document.getElementById("summaryFilter");
    
    let chartInstance = null;

    const format = (val) => new Intl.NumberFormat().format(val);

    async function loadDashboardSummary() {
        // Visual loading feedback
        [ppiScoreEl, totalClientsEl, totalPagtaluboEl, totalRegularEl].forEach(el => el.classList.add('loading-pulse'));

        try {
            // Using relative path to prevent "Unexpected token <" errors from common local setups
            const response = await fetch('/api/dashboard/summary');
            
            // Check if response is actually JSON
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new TypeError("Oops, we didn't get JSON from the server!");
            }

            const result = await response.json();

            if (result.success) {
                renderUI(result.data);
            }
        } catch (error) {
            console.error("Dashboard Fetch Error:", error);
            // Show error state in UI
            ppiScoreEl.innerText = "Err";
        } finally {
            [ppiScoreEl, totalClientsEl, totalPagtaluboEl, totalRegularEl].forEach(el => el.classList.remove('loading-pulse'));
        }
    }

    function renderUI(data) {
        // .toFixed(2) ensures 58.26 shows exactly like that
        ppiScoreEl.innerText = parseFloat(data.totalPpiAverage).toFixed(2);
        
        totalClientsEl.innerText = format(data.totalClients);
        totalPagtaluboEl.innerText = format(data.totalPagtalubo);
        totalRegularEl.innerText = format(data.totalRegular);

        renderSummaryChart(data);
    }

    function renderSummaryChart(data) {
        const ctx = document.getElementById('ppiChartVariation').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['2021', '2022', '2023', '2024', '2025'],
                datasets: [
                    {
                        label: 'Pagtalubo',
                        data: [12, 14, 15, 18, 24],
                        borderColor: '#5d87ff', // Your blue color
                        backgroundColor: '#5d87ff',
                        borderDash: [5, 5],      // <--- THIS CREATES THE DOTS
                        pointRadius: 5,         // Visible dots at data points
                        tension: 0.4            // Smooth curves as seen in your image
                    },
                    {
                        label: 'Regular',
                        data: [10, 12, 16, 17, 20],
                        borderColor: '#a392f3', // Your purple color
                        backgroundColor: '#a392f3',
                        borderDash: [5, 5],      // <--- THIS CREATES THE DOTS
                        pointRadius: 5,
                        tension: 0.4
                    }
                ]
            },
            options: {
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true, // <--- MAKES LEGEND ICONS CIRCLES
                            pointStyle: 'circle'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 30, // Adjust based on your data
                        grid: {
                            drawBorder: false // Cleaner look like your screenshot
                        }
                    },
                    x: {
                        grid: {
                            display: false // Removes vertical lines
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    /* Initial Execute */
    loadDashboardSummary();

}

