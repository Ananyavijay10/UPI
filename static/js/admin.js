/**
 * ==============================================================================
 * UPI Fraud Detection System - Admin Dashboard Controller (admin.js)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    const retrainBtn = document.getElementById('btn-retrain-model');
    const retrainStatus = document.getElementById('retrain-status-msg');

    if (retrainBtn) {
        retrainBtn.addEventListener('click', async () => {
            if (!confirm('Initiate complete ML re-training across all 4 algorithms on current dataset?')) {
                return;
            }

            retrainBtn.disabled = true;
            retrainBtn.innerHTML = `
                <span class="spinner-border" style="width:14px; height:14px;"></span>
                <span>Training Models...</span>
            `;

            if (retrainStatus) {
                retrainStatus.className = 'flash-alert info';
                retrainStatus.textContent = 'Model training started... Comparing Random Forest, Gradient Boosting, Logistic Regression, and Decision Tree.';
                retrainStatus.classList.remove('hidden');
            }

            try {
                const response = await fetch('/admin/retrain', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    if (retrainStatus) {
                        retrainStatus.className = 'flash-alert success';
                        retrainStatus.textContent = '✓ Model training completed successfully. Production model updated.';
                    }
                    showToast('ML Pipeline retrained successfully!', 'success');
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    if (retrainStatus) {
                        retrainStatus.className = 'flash-alert danger';
                        retrainStatus.textContent = `Retraining failed: ${data.error || 'Server error'}`;
                    }
                    showToast(data.error || 'Model retraining failed.', 'danger');
                }

            } catch (err) {
                console.error(err);
                if (retrainStatus) {
                    retrainStatus.className = 'flash-alert danger';
                    retrainStatus.textContent = 'Network error communicating with ML training daemon.';
                }
                showToast('Network error during retraining.', 'danger');
            } finally {
                retrainBtn.disabled = false;
                retrainBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                    <span>Retrain Model</span>
                `;
            }
        });
    }
});
