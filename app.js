// Dashboard Logic - Antigravity Quant
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
});

async function loadDashboardData() {
    try {
        // Load Summary Metrics - Pointing to project/reports/
        const summaryResponse = await fetch('./project/reports/summary.csv');
        const summaryText = await summaryResponse.text();
        const summaryData = Papa.parse(summaryText, { header: true }).data[0];
        renderMetrics(summaryData);

        // Load Equity Curve
        const equityResponse = await fetch('./project/reports/equity_curve.csv');
        const equityText = await equityResponse.text();
        const equityData = Papa.parse(equityText, { header: true }).data;
        renderEquityCharts(equityData);

        // Load Sector Exposure
        const sectorResponse = await fetch('./project/reports/sector_exposure.csv');
        const sectorText = await sectorResponse.text();
        const sectorData = Papa.parse(sectorText, { header: false }).data;
        renderSectorChart(sectorData);

        // Load Recent Trades
        const tradesResponse = await fetch('./project/reports/trades.csv');
        const tradesText = await tradesResponse.text();
        const tradesData = Papa.parse(tradesText, { header: true }).data;
        renderTradesTable(tradesData.slice(-15).reverse()); // Last 15 trades

    } catch (error) {
        console.error("Error loading dashboard data:", error);
        alert("Could not load report data. Please ensure you have run the backtest and the reports exist in project/reports/");
    }
}

function renderMetrics(data) {
    const container = document.getElementById('metrics-container');
    container.innerHTML = '';

    const metricsToShow = [
        { label: 'CAGR', value: data['CAGR %'] + '%', color: 'positive' },
        { label: 'Max Drawdown', value: data['Max Drawdown %'] + '%', color: 'negative' },
        { label: 'Sharpe Ratio', value: data['Sharpe Ratio'], color: '' },
        { label: 'Win Rate', value: data['Win Rate %'] + '%', color: 'positive' },
        { label: 'Profit Factor', value: data['Profit Factor'], color: '' },
        { label: 'Total PnL', value: '₹' + parseFloat(data['Total Net PnL']).toLocaleString(), color: 'positive' }
    ];

    metricsToShow.forEach(m => {
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
            <div class="metric-label">${m.label}</div>
            <div class="metric-value ${m.color}">${m.value}</div>
        `;
        container.appendChild(card);
    });
}

function renderEquityCharts(data) {
    // Filter out invalid rows
    const validData = data.filter(d => d.date && d.equity);
    const labels = validData.map(d => d.date.split(' ')[0]);
    const values = validData.map(d => parseFloat(d.equity));
    
    // 1. Equity Curve
    new Chart(document.getElementById('equityChart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Equity (₹)',
                data: values,
                borderColor: '#00d2ff',
                backgroundColor: 'rgba(0, 210, 255, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#7d8590' } },
                x: { grid: { display: false }, ticks: { color: '#7d8590', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } }
            }
        }
    });

    // 2. Drawdown Chart
    const peaks = [];
    let currentPeak = 0;
    const drawdowns = values.map(v => {
        if (v > currentPeak) currentPeak = v;
        return ((v - currentPeak) / currentPeak) * 100;
    });

    new Chart(document.getElementById('drawdownChart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Drawdown %',
                data: drawdowns,
                borderColor: '#da3633',
                backgroundColor: 'rgba(218, 54, 51, 0.2)',
                fill: true,
                tension: 0.1,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#7d8590' } },
                x: { grid: { display: false }, ticks: { color: '#7d8590', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } }
            }
        }
    });
}

function renderSectorChart(data) {
    const validData = data.filter(d => d[0] && d[1] && d[0] !== 'sector').slice(0, 8); // Top 8 sectors
    const labels = validData.map(d => d[0]);
    const values = validData.map(d => parseFloat(d[1]));

    new Chart(document.getElementById('sectorChart'), {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#3a7bd5', '#00d2ff', '#238636', '#da3633', 
                    '#f85149', '#8957e5', '#d29922', '#30363d'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#7d8590', padding: 20, font: { size: 11 } }
                }
            }
        }
    });
}

function renderTradesTable(trades) {
    const tbody = document.getElementById('trades-body');
    tbody.innerHTML = '';

    trades.forEach(t => {
        if (!t.symbol) return;
        const row = document.createElement('tr');
        const pnl = parseFloat(t.pnl);
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        
        row.innerHTML = `
            <td>${t.exit_date ? t.exit_date.split(' ')[0] : t.entry_date.split(' ')[0]}</td>
            <td><strong>${t.symbol}</strong></td>
            <td>₹${parseFloat(t.entry_price).toFixed(1)}</td>
            <td>₹${parseFloat(t.exit_price || 0).toFixed(1)}</td>
            <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}</td>
            <td><span class="status-badge" style="background: ${pnl >= 0 ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)'}; color: ${pnl >= 0 ? '#3fb950' : '#f85149'}; padding: 4px 8px; border-radius: 4px; font-size: 11px;">${pnl >= 0 ? 'PROFIT' : 'LOSS'}</span></td>
        `;
        tbody.appendChild(row);
    });
}
