function initScholarshipDashboard() {
	// Target elements based on the updated HTML structure
	const totalEligibleEl = document.querySelector(".bg-beige .stat-number");
	const totalHighPriorityEl = document.querySelector(".bg-blue .stat-number");
	const totalDependentsEl = document.querySelector(".bg-green .stat-number");
	const tableBody = document.querySelector(".table-container tbody");

	let chartInstance = null;

	const format = (val) => new Intl.NumberFormat().format(val);

	async function loadScholarshipDashboard() {
		try {
			const response = await fetch('http://localhost:5000/api/scholarship/dashboard');
			
			if (!response.ok) throw new Error("Network response was not ok");
			
			const result = await response.json();

			if (result.success) {
				renderSummary(result.data.summary);
				renderTable(result.data.highPriorityDependents);
				renderDistributionChart(result.data.educationLevelDistribution);
			}
		} catch (error) {
			console.error("Dashboard Fetch Error:", error);
		}
	}

	function renderSummary(summary) {
		totalEligibleEl.innerText = format(summary.eligibleDependents);
		totalHighPriorityEl.innerText = format(summary.highPriorityDependents);
		totalDependentsEl.innerText = format(summary.totalDependents);
	}

	function renderTable(dependents) {
		// Clear existing empty rows
		tableBody.innerHTML = "";

		dependents.forEach(item => {
			const row = `
				<tr>
					<td>${item.nameOfClient}</td>
					<td>${item.area}</td>
					<td>${item.unit}</td>
					<td>${item.center}</td>
				</tr>
			`;
			tableBody.insertAdjacentHTML('beforeend', row);
		});
	}

	function renderDistributionChart(distribution) {
		const ctx = document.getElementById('ppiChartVariation').getContext('2d');
		
		// Extract labels and counts from API
		const labels = distribution.map(d => d.educationLevel);
		const counts = distribution.map(d => d.count);

		if (chartInstance) {
			chartInstance.destroy();
		}

		chartInstance = new Chart(ctx, {
			type: 'bar', // Horizontal bar chart
			data: {
				labels: labels,
				datasets: [{
					label: 'Count',
					data: counts,
					backgroundColor: '#5d87ff', // Matching the blue in your screenshot
					borderRadius: 5,
					barThickness: 40
				}]
			},
			options: {
				indexAxis: 'y', // Makes it horizontal
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false } // Matches screenshot
				},
				scales: {
					x: {
						beginAtZero: true,
						grid: { display: false },
						ticks: { stepSize: 5 }
					},
					y: {
						grid: { display: false },
						ticks: {
							font: { weight: 'bold' }
						}
					}
				}
			}
		});
	}
	loadScholarshipDashboard();

}

