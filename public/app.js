// Dashboard Logic - MoneyFlow - ANTIGRAVITY QUANT
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
});

async function loadDashboardData() {
    try {
        // 1. Load Summary Metrics
        const summaryResponse = await fetch('reports/summary.csv');
        const summaryText = await summaryResponse.text();
        const summaryData = Papa.parse(summaryText, { header: true }).data[0];

        // 2. Load Equity Curve (Prioritize Live)
        let equityData;
        let isLive = false;
        try {
            const liveResponse = await fetch('reports/live_equity.csv');
            if (liveResponse.ok) {
                const liveText = await liveResponse.text();
                equityData = Papa.parse(liveText, { header: true }).data;
                // Check if we have more than just the header
                if (equityData.length > 0 && equityData[0].date) isLive = true;
            }
        } catch (e) { console.log("No live data found."); }

        if (!isLive) {
            const backtestResponse = await fetch('reports/equity_curve.csv');
            const backtestText = await backtestResponse.text();
            equityData = Papa.parse(backtestText, { header: true }).data;
        }

        renderHeader(isLive, equityData);
        renderMetrics(summaryData, equityData);
        renderEquityCharts(equityData);

        // 3. Load Sector Exposure
        const sectorResponse = await fetch('reports/sector_exposure.csv');
        const sectorText = await sectorResponse.text();
        const sectorData = Papa.parse(sectorText, { header: false }).data;
        renderSectorChart(sectorData);

        // 4. Load Recent Trades
        const tradesResponse = await fetch('reports/trades.csv');
        const tradesText = await tradesResponse.text();
        const tradesData = Papa.parse(tradesText, { header: true }).data;
        renderTradesTable(tradesData.filter(t => t.symbol).slice(-15).reverse());

    } catch (error) {
        console.error("Dashboard error:", error);
        alert("Dashboard sync error. Please ensure data exists in reports/ folder.");
    }
}

function renderHeader(isLive, data) {
    const badge = document.getElementById('last-updated');
    if (isLive) {
        badge.innerHTML = `<span style="color: #3fb950; font-weight: bold;">● Live Strategy Mode</span> | Last Update: ${data[data.length-1].date}`;
    } else {
        badge.innerHTML = `Backtest Mode | Period: 2021 - 2026`;
    }
}

function renderMetrics(summary, equity) {
    const container = document.getElementById('metrics-container');
    container.innerHTML = '';

    const lastRow = equity[equity.length - 1];
    const cash = lastRow.cash || (parseFloat(summary['Ending Capital']) * 0.15);
    const deployed = lastRow.deployed || (parseFloat(summary['Ending Capital']) - cash);

    const metricsToShow = [
        { label: 'Cagr', value: summary['CAGR %'] + '%', color: 'positive' },
        { label: 'Max drawdown', value: summary['Max Drawdown %'] + '%', color: 'negative' },
        { label: 'Sharpe ratio', value: summary['Sharpe Ratio'], color: '' },
        { label: 'Capital deployed', value: '₹' + parseFloat(deployed).toLocaleString(), color: 'accent' },
        { label: 'Cash balance', value: '₹' + parseFloat(cash).toLocaleString(), color: 'text-secondary' },
        { label: 'Net liquidity', value: '₹' + parseFloat(summary['Ending Capital']).toLocaleString(), color: 'positive' }
    ];

    metricsToShow.forEach(m => {
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
            <div class="metric-label">${m.label}</div>
            <div class="metric-value ${m.color || ''}" style="${m.color==='accent'?'color:var(--accent-color)':''}">${m.value}</div>
        `;
        container.appendChild(card);
    });
}

function renderEquityCharts(data) {
    const validData = data.filter(d => d.date && d.equity);
    const labels = validData.map(d => String(d.date).split(' ')[0]);
    const values = validData.map(d => parseFloat(d.equity));
    
    const ctx = document.getElementById('equityChart');
    if (window.equityChartObj) window.equityChartObj.destroy();
    
    window.equityChartObj = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity (₹)',
                data: values,
                borderColor: '#00d2ff',
                backgroundColor: 'rgba(0, 210, 255, 0.05)',
                fill: true,
                tension: 0.1,
                pointRadius: values.length > 100 ? 0 : 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                y: { 
                    grid: { color: 'rgba(255,255,255,0.05)' }, 
                    min: 900000,
                    ticks: { color: '#7d8590', font: { size: 10 }, callback: v => (v/100000).toFixed(1) + 'L' } 
                },
                x: { grid: { display: false }, ticks: { color: '#7d8590', font: { size: 10 }, autoSkip: true, maxTicksLimit: 12 } }
            }
        }
    });

    const drawdowns = [];
    let peak = 0;
    values.forEach(v => {
        if (v > peak) peak = v;
        drawdowns.push(((v - peak) / peak) * 100);
    });

    const ddCtx = document.getElementById('drawdownChart');
    if (window.ddChartObj) window.ddChartObj.destroy();
    window.ddChartObj = new Chart(ddCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Drawdown %',
                data: drawdowns,
                borderColor: '#da3633',
                backgroundColor: 'rgba(218, 54, 51, 0.1)',
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#7d8590', font: { size: 10 }, callback: v => v + '%' } },
                x: { grid: { display: false }, ticks: { display: false } }
            }
        }
    });
}

function renderSectorChart(data) {
    const validData = data.filter(d => d[0] && d[1] && d[0] !== 'sector').slice(0, 10);
    new Chart(document.getElementById('sectorChart'), {
        type: 'doughnut',
        data: {
            labels: validData.map(d => d[0]),
            datasets: [{
                data: validData.map(d => parseFloat(d[1])),
                backgroundColor: ['#3a7bd5', '#00d2ff', '#238636', '#da3633', '#f85149', '#8957e5', '#d29922', '#30363d', '#444c56', '#546371'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { left: 10, right: 10, bottom: 20 } },
            plugins: {
                legend: { 
                    position: 'right', 
                    labels: { color: '#7d8590', boxWidth: 10, font: { size: 9 } } 
                }
            }
        }
    });
}

function renderTradesTable(trades) {
    const tbody = document.getElementById('trades-body');
    tbody.innerHTML = '';
    trades.forEach(t => {
        const pnl = parseFloat(t.pnl);
        const entry = parseFloat(t.entry_price);
        const exit = parseFloat(t.exit_price || entry);
        const pnlPct = ((exit - entry) / entry) * 100;
        const qty = Math.round(83333 / entry); 
        const invested = (qty * entry).toFixed(0);

        const row = document.createElement('tr');
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        
        row.innerHTML = `
            <td>${(t.exit_date || t.entry_date).split(' ')[0]}</td>
            <td><strong>${t.symbol}</strong></td>
            <td>₹${parseFloat(invested).toLocaleString()}</td>
            <td>${qty}</td>
            <td>₹${entry.toFixed(1)}</td>
            <td>₹${exit.toFixed(1)}</td>
            <td class="${pnlClass}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}</td>
            <td class="${pnlClass}">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%</td>
        `;
        tbody.appendChild(row);
    });
}
