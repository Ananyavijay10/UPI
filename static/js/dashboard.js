/**
 * ==============================================================================
 * UPI Fraud Detection System - Dashboard & History Controllers (dashboard.js)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // --------------------------------------------------------------------------
    // History Table Live Filter & Pagination
    // --------------------------------------------------------------------------
    const historyTableBody = document.getElementById('history-table-body');
    const searchInput = document.getElementById('history-search');
    const statusFilter = document.getElementById('history-status-filter');
    const typeFilter = document.getElementById('history-type-filter');
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');
    const pageIndicator = document.getElementById('page-indicator');
    const totalRecordsText = document.getElementById('total-records-count');

    let currentPage = 1;
    let totalPages = 1;

    async function loadHistory(page = 1) {
        if (!historyTableBody) return;

        const search = searchInput ? encodeURIComponent(searchInput.value.trim()) : '';
        const status = statusFilter ? encodeURIComponent(statusFilter.value) : '';
        const type = typeFilter ? encodeURIComponent(typeFilter.value) : '';

        try {
            historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:24px;"><span class="spinner-border"></span> Loading records...</td></tr>`;

            const res = await fetch(`/api/history?page=${page}&per_page=10&search=${search}&status=${status}&type=${type}`);
            const data = await res.json();

            if (!res.ok || !data.success) {
                historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#ef4444; padding:24px;">Failed to load history records.</td></tr>`;
                return;
            }

            currentPage = data.page;
            totalPages = data.total_pages || 1;

            if (pageIndicator) pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
            if (totalRecordsText) totalRecordsText.textContent = `${data.total} Total Transactions`;

            if (prevBtn) prevBtn.disabled = currentPage <= 1;
            if (nextBtn) nextBtn.disabled = currentPage >= totalPages;

            if (data.data.length === 0) {
                historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#94a3b8; padding:32px;">No matching transactions found.</td></tr>`;
                return;
            }

            historyTableBody.innerHTML = '';
            data.data.forEach(item => {
                const tr = document.createElement('tr');

                let statusBadgeClass = 'safe';
                if (item.status === 'FRAUD LIKELY') statusBadgeClass = 'fraud';
                else if (item.status === 'SUSPICIOUS') statusBadgeClass = 'suspicious';

                let riskLevelClass = 'safe';
                if (item.risk_level === 'CRITICAL' || item.risk_level === 'HIGH') riskLevelClass = 'fraud';
                else if (item.risk_level === 'MEDIUM') riskLevelClass = 'suspicious';

                tr.innerHTML = `
                    <td><strong>#${item.id}</strong></td>
                    <td>${item.created_at}</td>
                    <td><strong>₹${item.amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong></td>
                    <td>${item.transaction_type}</td>
                    <td>${item.time}</td>
                    <td><span class="status-pill ${riskLevelClass}">${item.risk_score} / 100</span></td>
                    <td><span class="status-pill ${statusBadgeClass}">${item.status}</span></td>
                    <td>
                        <a href="/transaction/${item.id}" class="nav-btn nav-btn-secondary" style="padding:4px 10px; font-size:0.75rem;">
                            View
                        </a>
                    </td>
                `;
                historyTableBody.appendChild(tr);
            });

        } catch (e) {
            console.error(e);
            historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#ef4444; padding:24px;">Network error loading records.</td></tr>`;
        }
    }

    if (searchInput) {
        let debounceTimer = null;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => loadHistory(1), 350);
        });
    }

    if (statusFilter) statusFilter.addEventListener('change', () => loadHistory(1));
    if (typeFilter) typeFilter.addEventListener('change', () => loadHistory(1));

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) loadHistory(currentPage - 1);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentPage < totalPages) loadHistory(currentPage + 1);
        });
    }

    // Initial load
    if (historyTableBody) {
        loadHistory(1);
    }
});
