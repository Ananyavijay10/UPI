/**
 * ==============================================================================
 * UPI Fraud Detection System - Transaction Analysis Script (analyze.js)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transaction-form');
    const amountInput = document.getElementById('amount');

    const timeInput = document.getElementById('time-input');
    const timeSlider = document.getElementById('time-slider');
    const timeBadge = document.getElementById('time-badge');

    const typeSelect = document.getElementById('transaction_type');
    const paymentModeSelect = document.getElementById('payment_mode');
    const upiIdInput = document.getElementById('upi_id');
    const recipientNameInput = document.getElementById('recipient_name');

    // Midnight High-Value Alert Box & Reason Elements
    const midnightAlertBox = document.getElementById('midnight-alert-box');
    const highTxReasonInput = document.getElementById('high_tx_reason');
    const highTxReasonError = document.getElementById('high-tx-reason-error');

    const submitBtn = document.getElementById('analyze-submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnLoader = document.getElementById('btn-loader');

    // Result Card Elements
    const emptyState = document.getElementById('empty-analysis-state');
    const resultCard = document.getElementById('analysis-result-card');
    const gaugeCircle = document.getElementById('gauge-circle');
    const probNumber = document.getElementById('prob-number');
    const riskScoreVal = document.getElementById('risk-score-val');
    const riskLevelBadge = document.getElementById('risk-level-badge');
    const statusPill = document.getElementById('status-pill');
    const statusAlertBanner = document.getElementById('status-alert-banner');
    const alertTitle = document.getElementById('alert-title');
    const alertDesc = document.getElementById('alert-desc');

    const indicatorsList = document.getElementById('indicators-list');
    const summaryAmt = document.getElementById('sum-amount');
    const summaryTime = document.getElementById('sum-time');
    const summaryType = document.getElementById('sum-type');
    const summaryMode = document.getElementById('sum-mode');
    const sumReasonBox = document.getElementById('sum-reason-box');
    const sumReason = document.getElementById('sum-reason');

    // Verification Action Controls
    const verificationBox = document.getElementById('verification-action-box');
    const btnVerify = document.getElementById('btn-verify-tx');
    const btnCancel = document.getElementById('btn-cancel-tx');

    let currentTransactionId = null;

    // SVG Gauge Circumference: r=68 -> 2 * PI * 68 = 427.256
    const CIRCUMFERENCE = 2 * Math.PI * 68;
    if (gaugeCircle) {
        gaugeCircle.style.strokeDasharray = `${CIRCUMFERENCE} ${CIRCUMFERENCE}`;
        gaugeCircle.style.strokeDashoffset = `${CIRCUMFERENCE}`;
    }

    // 1. Time Synchronization
    function syncTime(hour) {
        if (hour === '' || hour === null || hour === undefined || isNaN(hour)) {
            if (timeBadge) {
                timeBadge.textContent = '--:--';
                timeBadge.style.color = 'var(--text-muted)';
                timeBadge.style.background = 'rgba(255,255,255,0.06)';
            }
            checkMidnightAlert();
            return;
        }
        const h = Math.min(23, Math.max(0, parseInt(hour, 10) || 0));
        if (timeInput) timeInput.value = h;
        if (timeSlider) timeSlider.value = h;

        if (timeBadge) {
            const period = h >= 12 ? 'PM' : 'AM';
            const displayH = h % 12 === 0 ? 12 : h % 12;
            const timeStr = `${String(displayH).padStart(2, '0')}:00 ${period}`;
            
            if (h <= 5) {
                timeBadge.textContent = `${timeStr} (High Risk Night)`;
                timeBadge.style.color = '#ef4444';
            } else if (h >= 19) {
                timeBadge.textContent = `${timeStr} (Medium Risk Eve)`;
                timeBadge.style.color = '#f59e0b';
            } else {
                timeBadge.textContent = `${timeStr} (Low Risk Day)`;
                timeBadge.style.color = '#10b981';
            }
        }

        checkMidnightAlert();
    }

    if (timeInput) timeInput.addEventListener('input', (e) => syncTime(e.target.value));
    if (timeSlider) timeSlider.addEventListener('input', (e) => syncTime(e.target.value));
    if (timeInput && timeInput.value !== '') {
        syncTime(timeInput.value);
    } else {
        syncTime('');
    }

    // 2. Real-Time Check for Midnight High-Value Alert (12 AM - 6 AM & Amount > ₹200,000)
    function checkMidnightAlert() {
        const amt = parseFloat(amountInput ? amountInput.value : 0) || 0;
        const hrVal = timeInput ? timeInput.value.trim() : '';

        // Only trigger if time is explicitly entered AND in 12 AM to 6 AM window (hours 0–6)
        const isMidnightWindow = (hrVal !== '') && (parseInt(hrVal, 10) >= 0 && parseInt(hrVal, 10) <= 6);
        const isHighAmount = (amt > 200000);

        if (midnightAlertBox) {
            if (isMidnightWindow && isHighAmount) {
                midnightAlertBox.classList.remove('hidden');
                if (highTxReasonInput) {
                    highTxReasonInput.setAttribute('required', 'true');
                }
            } else {
                midnightAlertBox.classList.add('hidden');
                if (highTxReasonInput) {
                    highTxReasonInput.removeAttribute('required');
                    if (highTxReasonError) highTxReasonError.style.display = 'none';
                }
            }
        }
    }

    if (amountInput) amountInput.addEventListener('input', checkMidnightAlert);

    if (highTxReasonInput) {
        highTxReasonInput.addEventListener('input', () => {
            if (highTxReasonInput.value.trim() && highTxReasonError) {
                highTxReasonError.style.display = 'none';
            }
        });
    }

    // 3. Quick Scenario Presets
    document.querySelectorAll('.preset-chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const amt = btn.getAttribute('data-amount');
            const hr = btn.getAttribute('data-time');
            const type = btn.getAttribute('data-type');
            const upi = btn.getAttribute('data-upi') || '';
            const mode = btn.getAttribute('data-mode') || 'UPI ID / VPA';
            const reason = btn.getAttribute('data-reason') || '';

            if (amountInput) amountInput.value = amt;
            syncTime(hr);
            if (typeSelect) typeSelect.value = type;
            if (upiIdInput) upiIdInput.value = upi;
            if (paymentModeSelect) paymentModeSelect.value = mode;

            checkMidnightAlert();

            if (highTxReasonInput) {
                highTxReasonInput.value = reason;
            }

            // Trigger submit
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        });
    });

    // 4. Form Submit
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const amt = parseFloat(amountInput.value);
            const hr = parseInt(timeInput.value, 10);
            const type = typeSelect ? typeSelect.value : '';
            const reason = highTxReasonInput ? highTxReasonInput.value.trim() : '';
            const mode = paymentModeSelect ? paymentModeSelect.value : 'UPI ID / VPA';
            const upi = upiIdInput ? upiIdInput.value.trim() : '';
            const recipient = recipientNameInput ? recipientNameInput.value.trim() : '';

            if (isNaN(amt) || amt <= 0) {
                showToast('Please specify a positive transaction amount (> ₹0).', 'danger');
                return;
            }

            if (isNaN(hr) || hr < 0 || hr > 23) {
                showToast('Please select a valid hour between 0 and 23.', 'danger');
                return;
            }

            if (!type || type === '') {
                showToast('Please select a valid transaction category.', 'danger');
                return;
            }

            // Midnight High-Value Validation (12 AM - 6 AM & Amount > ₹200,000)
            if (hr <= 6 && amt > 200000) {
                if (!reason) {
                    if (highTxReasonError) {
                        highTxReasonError.style.display = 'block';
                    }
                    if (highTxReasonInput) {
                        highTxReasonInput.focus();
                    }
                    showToast('⚠️ Mandatory: Please provide a reason for high-value transaction exceeding ₹2,00,000 between 12 AM and 6 AM.', 'danger');
                    return;
                }
            }

            if (highTxReasonError) {
                highTxReasonError.style.display = 'none';
            }

            // Set loading
            submitBtn.disabled = true;
            btnText.classList.add('hidden');
            btnLoader.classList.remove('hidden');

            const payload = {
                amount: amt,
                time: hr,
                transaction_type: type,
                payment_mode: mode,
                upi_id: upi,
                recipient_name: recipient,
                high_tx_reason: reason
            };

            try {
                // Try saving to DB via /api/transaction
                let response = await fetch('/api/transaction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                // If unauthorized (unauthenticated guest), fallback to /predict
                if (response.status === 401) {
                    response = await fetch('/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                }

                const data = await response.json();

                if (!response.ok || !data.success) {
                    showToast(data.error || 'Prediction analysis failed.', 'danger');
                    return;
                }

                currentTransactionId = data.transaction_id || null;
                renderAnalysisResults(data, payload);

            } catch (err) {
                console.error(err);
                showToast('Network error: Could not connect to fraud detection service.', 'danger');
            } finally {
                submitBtn.disabled = false;
                btnText.classList.remove('hidden');
                btnLoader.classList.add('hidden');
            }
        });
    }

    // 5. Render Results Function
    function renderAnalysisResults(res, reqPayload) {
        if (emptyState) emptyState.classList.add('hidden');
        if (resultCard) {
            resultCard.classList.remove('hidden');
            if (window.innerWidth < 1024) {
                resultCard.scrollIntoView({ behavior: 'smooth' });
            }
        }

        const prob = res.fraud_probability;
        const score = res.risk_score;
        const level = res.risk_level;
        const status = res.status;

        // Counter animation
        animateValue(probNumber, 0, Math.round(prob * 100), 800, '%');
        if (riskScoreVal) riskScoreVal.textContent = `${score} / 100`;

        // SVG Radial Gauge Animation
        const offset = CIRCUMFERENCE - (prob * CIRCUMFERENCE);
        gaugeCircle.style.strokeDashoffset = offset;

        // Status Card, Alert Banner & Theme
        applyTheme(status, level, prob);

        // Transaction Summary
        if (summaryAmt) summaryAmt.textContent = formatINR(reqPayload.amount);
        if (summaryTime) {
            const h = reqPayload.time;
            const period = h >= 12 ? 'PM' : 'AM';
            const displayH = h % 12 === 0 ? 12 : h % 12;
            summaryTime.textContent = `${String(displayH).padStart(2, '0')}:00 ${period}`;
        }
        if (summaryType) summaryType.textContent = reqPayload.transaction_type;
        if (summaryMode) summaryMode.textContent = reqPayload.payment_mode || 'UPI ID / VPA';

        // High Transaction Reason Display
        if (sumReasonBox && sumReason) {
            if (reqPayload.high_tx_reason) {
                sumReason.textContent = reqPayload.high_tx_reason;
                sumReasonBox.classList.remove('hidden');
            } else {
                sumReasonBox.classList.add('hidden');
            }
        }

        // Risk Indicators
        renderIndicators(res.system_reasons);

        // Verification Actions box
        if (verificationBox) {
            if (score >= 60 && currentTransactionId) {
                verificationBox.classList.remove('hidden');
            } else {
                verificationBox.classList.add('hidden');
            }
        }
    }

    function applyTheme(status, level, prob) {
        if (status === 'FRAUD LIKELY' || level === 'CRITICAL' || level === 'HIGH') {
            gaugeCircle.style.stroke = '#ef4444';
            statusPill.className = 'status-pill fraud';
            statusPill.textContent = 'FRAUD LIKELY';

            riskLevelBadge.className = 'status-pill fraud';
            riskLevelBadge.textContent = level;

            statusAlertBanner.className = 'alert-banner critical';
            alertTitle.textContent = '🚨 HIGH RISK TRANSACTION DETECTED';
            alertDesc.textContent = 'Multi-factor anomaly thresholds exceeded. Secondary verification or suspension advised.';
        } else if (status === 'SUSPICIOUS' || level === 'MEDIUM') {
            gaugeCircle.style.stroke = '#f59e0b';
            statusPill.className = 'status-pill suspicious';
            statusPill.textContent = 'SUSPICIOUS';

            riskLevelBadge.className = 'status-pill suspicious';
            riskLevelBadge.textContent = level;

            statusAlertBanner.className = 'alert-banner suspicious';
            alertTitle.textContent = '⚠ SUSPICIOUS TRANSACTION';
            alertDesc.textContent = 'Elevated behavioral risk detected. Biometric / OTP confirmation recommended.';
        } else {
            gaugeCircle.style.stroke = '#10b981';
            statusPill.className = 'status-pill safe';
            statusPill.textContent = 'SAFE';

            riskLevelBadge.className = 'status-pill safe';
            riskLevelBadge.textContent = level;

            statusAlertBanner.className = 'alert-banner safe';
            alertTitle.textContent = '✓ TRANSACTION SAFE';
            alertDesc.textContent = 'Transaction parameters conform to standard consumer patterns. Safe to authorize.';
        }
    }

    function renderIndicators(indicators) {
        if (!indicatorsList) return;
        indicatorsList.innerHTML = '';

        if (!indicators || indicators.length === 0) {
            const li = document.createElement('li');
            li.style.cssText = 'color: #10b981; display:flex; align-items:center; gap:8px;';
            li.innerHTML = `<span>✓</span> <span>No major rule-based risk indicators detected</span>`;
            indicatorsList.appendChild(li);
            return;
        }

        indicators.forEach(ind => {
            const li = document.createElement('li');
            li.style.cssText = 'color: #fde68a; display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;';
            li.innerHTML = `<span style="color:#f59e0b; font-weight:bold;">⚠</span> <span>${escapeHtml(ind)}</span>`;
            indicatorsList.appendChild(li);
        });
    }

    // Number animation helper
    function animateValue(obj, start, end, duration, suffix = '') {
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start) + suffix;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // 6. Handle Verification & Cancel Actions
    if (btnVerify) {
        btnVerify.addEventListener('click', async () => {
            if (!currentTransactionId) return;
            try {
                const res = await fetch(`/api/transaction/${currentTransactionId}/verify`, { method: 'POST' });
                const d = await res.json();
                if (d.success) {
                    showToast('Transaction verified and cleared successfully!', 'success');
                    verificationBox.classList.add('hidden');
                }
            } catch (e) {
                showToast('Action failed.', 'danger');
            }
        });
    }

    if (btnCancel) {
        btnCancel.addEventListener('click', async () => {
            if (!currentTransactionId) return;
            try {
                const res = await fetch(`/api/transaction/${currentTransactionId}/cancel`, { method: 'POST' });
                const d = await res.json();
                if (d.success) {
                    showToast('Transaction flagged and cancelled.', 'warning');
                    verificationBox.classList.add('hidden');
                }
            } catch (e) {
                showToast('Action failed.', 'danger');
            }
        });
    }
});
