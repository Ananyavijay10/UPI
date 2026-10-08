/**
 * ==============================================================================
 * UPI Fraud Detection System - Analytics & Visualizations (charts.js)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
    const analyticsContainer = document.getElementById('analytics-content-container');
    const noDataPlaceholder = document.getElementById('no-data-placeholder');

    try {
        const response = await fetch('/api/statistics');
        const result = await response.json();

        if (!result.success || !result.has_data || result.total_transactions === 0) {
            if (analyticsContainer) analyticsContainer.classList.add('hidden');
            if (noDataPlaceholder) noDataPlaceholder.classList.remove('hidden');
            return;
        }

        if (noDataPlaceholder) noDataPlaceholder.classList.add('hidden');
        if (analyticsContainer) analyticsContainer.classList.remove('hidden');

        // Set Chart.js Defaults for Dark Fintech UI
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
        Chart.defaults.font.family = "'Inter', sans-serif";

        // 1. Chart: Status Breakdown (Doughnut)
        const ctxStatus = document.getElementById('chart-status-breakdown');
        if (ctxStatus) {
            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Safe', 'Suspicious', 'Fraud Likely'],
                    datasets: [{
                        data: [
                            result.status_breakdown['SAFE'] || 0,
                            result.status_breakdown['SUSPICIOUS'] || 0,
                            result.status_breakdown['FRAUD LIKELY'] || 0
                        ],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 0,
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 16 } }
                    },
                    cutout: '72%'
                }
            });
        }

        // 2. Chart: Fraud by Transaction Type (Bar)
        const ctxType = document.getElementById('chart-type-distribution');
        if (ctxType) {
            const types = Object.keys(result.type_distribution);
            const totalByType = types.map(t => result.type_distribution[t] || 0);
            const fraudByType = types.map(t => result.type_fraud_distribution[t] || 0);

            new Chart(ctxType, {
                type: 'bar',
                data: {
                    labels: types,
                    datasets: [
                        {
                            label: 'Total Transactions',
                            data: totalByType,
                            backgroundColor: 'rgba(99, 102, 241, 0.5)',
                            borderRadius: 6
                        },
                        {
                            label: 'Fraud Flagged',
                            data: fraudByType,
                            backgroundColor: '#ef4444',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, ticks: { precision: 0 } }
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12 } }
                    }
                }
            });
        }

        // 3. Chart: Transactions by Hour & Fraud Trend (Line)
        const ctxHour = document.getElementById('chart-hourly-trend');
        if (ctxHour) {
            const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
            new Chart(ctxHour, {
                type: 'line',
                data: {
                    labels: hours,
                    datasets: [
                        {
                            label: 'Volume',
                            data: result.hourly_totals,
                            borderColor: '#06b6d4',
                            backgroundColor: 'rgba(6, 182, 212, 0.1)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2
                        },
                        {
                            label: 'Fraud Count',
                            data: result.hourly_fraud,
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.15)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 } }
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12 } }
                    }
                }
            });
        }

        // 4. Chart: Risk Score Bins (Bar)
        const ctxScore = document.getElementById('chart-score-bins');
        if (ctxScore) {
            const binLabels = Object.keys(result.score_bins);
            const binValues = Object.values(result.score_bins);

            new Chart(ctxScore, {
                type: 'bar',
                data: {
                    labels: binLabels,
                    datasets: [{
                        label: 'Transactions Count',
                        data: binValues,
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.7)',
                            'rgba(6, 182, 212, 0.7)',
                            'rgba(245, 158, 11, 0.7)',
                            'rgba(239, 68, 68, 0.7)',
                            'rgba(220, 38, 38, 0.9)'
                        ],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

    } catch (err) {
        console.error("Error loading analytics:", err);
        if (analyticsContainer) analyticsContainer.classList.add('hidden');
        if (noDataPlaceholder) noDataPlaceholder.classList.remove('hidden');
    }
});
