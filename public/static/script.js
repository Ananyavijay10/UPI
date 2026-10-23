/**
 * ==============================================================================
 * UPI Fraud Detection Dashboard - Frontend Controller (script.js)
 * ==============================================================================
 * Handles:
 * - Real-time client-side form validation
 * - Dynamic synchronization between Time Number input and Range Slider
 * - Asynchronous Fetch requests to /predict endpoint
 * - SVG Radial Gauge stroke animation and animated percentage counter
 * - Dynamic status card themes, accessible badges, and system reason injection
 * - Preset test scenario loading for quick scenario testing
 * - Live model metadata polling from /api/model-info
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // --------------------------------------------------------------------------
    // DOM Element References
    // --------------------------------------------------------------------------
    const form = document.getElementById('fraud-form');
    const amountInput = document.getElementById('amount');
    const timeInput = document.getElementById('time-input');
    const timeSlider = document.getElementById('time-slider');
    const timeBadge = document.getElementById('time-badge');
    const reasonSelect = document.getElementById('reason');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnLoader = document.getElementById('btn-loader');

    // Errors
    const amountError = document.getElementById('amount-error');
    const timeError = document.getElementById('time-error');
    const reasonError = document.getElementById('reason-error');
    const errorToast = document.getElementById('error-toast');
    const toastMessage = document.getElementById('toast-message');

    // Result Section Elements
    const emptyStateCard = document.getElementById('empty-state-card');
    const resultSection = document.getElementById('result-section');
    const gaugeCircle = document.getElementById('gauge-circle');
    const probabilityValue = document.getElementById('probability-value');
    const riskLevelTag = document.getElementById('risk-level-tag');
    const statusCard = document.getElementById('status-card');
    const statusTitle = document.getElementById('status-title');
    const statusDesc = document.getElementById('status-desc');
    const statusIconBox = document.getElementById('status-icon-box');

    // Summary Elements
    const summaryAmount = document.getElementById('summary-amount');
    const summaryTime = document.getElementById('summary-time');
    const summaryReason = document.getElementById('summary-reason');
    const summaryTimeRisk = document.getElementById('summary-time-risk');
    const systemReasonsList = document.getElementById('system-reasons-list');
    const recommendationBox = document.getElementById('recommendation-box');
    const recHeadline = document.getElementById('rec-headline');
    const recSubline = document.getElementById('rec-subline');

    // Quick chip buttons & scenario presets
    const quickChips = document.querySelectorAll('.chip');
    const presetButtons = document.querySelectorAll('.preset-btn');

    // Live footer specs
    const liveAccuracy = document.getElementById('live-accuracy');
    const liveSamples = document.getElementById('live-samples');

    // SVG Gauge Circle Circumference (r = 68 -> 2 * PI * 68 = 427.256)
    const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 68;
    gaugeCircle.style.strokeDasharray = `${GAUGE_CIRCUMFERENCE} ${GAUGE_CIRCUMFERENCE}`;
    gaugeCircle.style.strokeDashoffset = `${GAUGE_CIRCUMFERENCE}`;

    // --------------------------------------------------------------------------
    // 1. Time Slider & Number Synchronization
    // --------------------------------------------------------------------------
    function formatTimeLabel(hour) {
        const h = parseInt(hour, 10);
        if (isNaN(h) || h < 0 || h > 23) return '--:--';
        
        const period = h >= 12 ? 'PM' : 'AM';
        const displayH = h % 12 === 0 ? 12 : h % 12;
        const timeFormatted = `${String(displayH).padStart(2, '0')}:00 ${period}`;

        if (h >= 0 && h <= 5) {
            return `${timeFormatted} • High Risk (Night)`;
        } else if (h >= 6 && h <= 18) {
            return `${timeFormatted} • Low Risk (Day)`;
        } else {
            return `${timeFormatted} • Medium Risk (Eve)`;
        }
    }

    function syncTime(hour) {
        const validHour = Math.min(23, Math.max(0, parseInt(hour, 10) || 0));
        timeInput.value = validHour;
        timeSlider.value = validHour;
        timeBadge.textContent = formatTimeLabel(validHour);

        // Visual cue on badge depending on risk
        if (validHour <= 5) {
            timeBadge.style.color = '#ef4444';
            timeBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            timeBadge.style.background = 'rgba(239, 68, 68, 0.1)';
        } else if (validHour >= 19) {
            timeBadge.style.color = '#f59e0b';
            timeBadge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
            timeBadge.style.background = 'rgba(245, 158, 11, 0.1)';
        } else {
            timeBadge.style.color = '#06b6d4';
            timeBadge.style.borderColor = 'rgba(6, 182, 212, 0.3)';
            timeBadge.style.background = 'rgba(6, 182, 212, 0.12)';
        }
    }

    timeInput.addEventListener('input', (e) => syncTime(e.target.value));
    timeSlider.addEventListener('input', (e) => syncTime(e.target.value));

    // Initialize time badge on startup
    if (timeInput && timeInput.value !== '') {
        syncTime(timeInput.value);
    }

    // --------------------------------------------------------------------------
    // 2. Quick Amount Chips
    // --------------------------------------------------------------------------
    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const val = chip.getAttribute('data-val');
            amountInput.value = val;
            clearErrors();
            amountInput.focus();
        });
    });

    // --------------------------------------------------------------------------
    // 3. Quick Scenario Presets
    // --------------------------------------------------------------------------
    presetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const amt = btn.getAttribute('data-amount');
            const hr = btn.getAttribute('data-time');
            const rsn = btn.getAttribute('data-reason');

            amountInput.value = amt;
            syncTime(hr);
            reasonSelect.value = rsn;
            clearErrors();

            // Automatically analyze to showcase instant response
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        });
    });

    // --------------------------------------------------------------------------
    // 4. Input Validation
    // --------------------------------------------------------------------------
    function clearErrors() {
        amountError.textContent = '';
        timeError.textContent = '';
        reasonError.textContent = '';
    }

    function showToast(msg) {
        toastMessage.textContent = msg;
        errorToast.classList.remove('hidden');
        setTimeout(() => {
            errorToast.classList.add('hidden');
        }, 5000);
    }

    function validateInputs(amount, time, reason) {
        clearErrors();
        let isValid = true;

        if (isNaN(amount) || amount <= 0) {
            amountError.textContent = 'Please enter a valid positive amount (> ₹0).';
            isValid = false;
        }

        if (isNaN(time) || time < 0 || time > 23 || !Number.isInteger(time)) {
            timeError.textContent = 'Transaction hour must be an integer between 0 and 23.';
            isValid = false;
        }

        if (!reason || reason.trim() === '') {
            reasonError.textContent = 'Please select a valid transaction category.';
            isValid = false;
        }

        return isValid;
    }

    // --------------------------------------------------------------------------
    // 5. Form Submission & API Request
    // --------------------------------------------------------------------------
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const amountVal = parseFloat(amountInput.value);
        const timeVal = parseInt(timeInput.value, 10);
        const reasonVal = reasonSelect.value;

        if (!validateInputs(amountVal, timeVal, reasonVal)) {
            return;
        }

        // Set Loading State
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    amount: amountVal,
                    time: timeVal,
                    reason: reasonVal
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                const errMsg = data.error || `Server returned error (${response.status})`;
                showToast(errMsg);
                return;
            }

            // Update UI with response data
            renderResults(data);

        } catch (err) {
            console.error('Fetch error:', err);
            showToast('Network error: Unable to reach the UPI Fraud Detection API.');
        } finally {
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            btnLoader.classList.add('hidden');
        }
    });

    // --------------------------------------------------------------------------
    // 6. Result Dashboard Rendering & Gauge Animation
    // --------------------------------------------------------------------------
    function renderResults(res) {
        // Reveal result section, hide empty state placeholder
        emptyStateCard.classList.add('hidden');
        resultSection.classList.remove('hidden');

        // Scroll result card into view smoothly on mobile/narrow screens
        if (window.innerWidth < 992) {
            resultSection.scrollIntoView({ behavior: 'smooth' });
        }

        const prob = res.fraud_probability; // e.g. 0.63
        const percentage = Math.round(prob * 100); // 63%

        // Animate percentage counter
        animateCounter(probabilityValue, 0, percentage, 800);

        // Animate Radial Gauge stroke
        const strokeOffset = GAUGE_CIRCUMFERENCE - (prob * GAUGE_CIRCUMFERENCE);
        gaugeCircle.style.strokeDashoffset = strokeOffset;

        // Apply dynamic risk theme (Safe, Suspicious, or Fraud Likely)
        applyStatusTheme(res.status, prob);

        // Transaction Summary
        summaryAmount.textContent = `₹${res.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        const hrStr = String(res.time).padStart(2, '0');
        summaryTime.textContent = `${hrStr}:00 (${res.time >= 12 ? 'PM' : 'AM'})`;
        summaryReason.textContent = res.reason;
        
        let trText = 'Low (0.0)';
        if (res.time_risk === 1.0) trText = 'High (1.0)';
        else if (res.time_risk === 0.5) trText = 'Medium (0.5)';
        summaryTimeRisk.textContent = trText;

        // System Analysis Reasons
        renderSystemReasons(res.system_reasons, res.status);
    }

    // --------------------------------------------------------------------------
    // 7. Counter Animation Helper
    // --------------------------------------------------------------------------
    function animateCounter(element, start, end, duration) {
        let startTime = null;
        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const current = Math.floor(progress * (end - start) + start);
            element.textContent = `${current}%`;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                element.textContent = `${end}%`;
            }
        }
        window.requestAnimationFrame(step);
    }

    // --------------------------------------------------------------------------
    // 8. Dynamic Status Theme Application
    // --------------------------------------------------------------------------
    function applyStatusTheme(status, prob) {
        // Reset class states
        statusCard.className = 'status-card';
        recommendationBox.className = 'recommendation-box';

        if (status === 'Fraud Likely') {
            // High Risk Danger Theme
            gaugeCircle.style.stroke = '#ef4444';
            riskLevelTag.textContent = 'High Risk';
            riskLevelTag.style.background = 'rgba(239, 68, 68, 0.2)';
            riskLevelTag.style.color = '#ef4444';

            statusCard.classList.add('status-fraud');
            statusTitle.textContent = 'FRAUD LIKELY';
            statusDesc.textContent = 'High probability of fraudulent activity. Pattern deviates strongly from legitimate behavior.';

            statusIconBox.innerHTML = `
                <svg class="status-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
            `;

            recommendationBox.classList.add('fraud');
            recHeadline.textContent = 'Recommendation: Block & Require OTP Verification';
            recSubline.textContent = 'Immediate risk threshold exceeded. Transaction halted pending security review.';

        } else if (status === 'Suspicious Transaction') {
            // Medium Risk Warning Theme
            gaugeCircle.style.stroke = '#f59e0b';
            riskLevelTag.textContent = 'Medium Risk';
            riskLevelTag.style.background = 'rgba(245, 158, 11, 0.2)';
            riskLevelTag.style.color = '#f59e0b';

            statusCard.classList.add('status-suspicious');
            statusTitle.textContent = 'SUSPICIOUS TRANSACTION';
            statusDesc.textContent = 'Elevated transaction anomaly detected. Caution and biometric verification advised.';

            statusIconBox.innerHTML = `
                <svg class="status-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            `;

            recommendationBox.classList.add('suspicious');
            recHeadline.textContent = 'Recommendation: Prompt 2-Factor Biometric Confirmation';
            recSubline.textContent = 'Elevated risk parameters detected. User re-authentication recommended.';

        } else {
            // Safe Theme
            gaugeCircle.style.stroke = '#10b981';
            riskLevelTag.textContent = 'Low Risk';
            riskLevelTag.style.background = 'rgba(16, 185, 129, 0.2)';
            riskLevelTag.style.color = '#10b981';

            statusCard.classList.add('status-safe');
            statusTitle.textContent = 'TRANSACTION SAFE';
            statusDesc.textContent = 'Parameters align with normal behavioral baselines. Safe to proceed.';

            statusIconBox.innerHTML = `
                <svg class="status-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <path d="M9 12l2 2 4-4"/>
                </svg>
            `;

            recommendationBox.classList.add('safe');
            recHeadline.textContent = 'Recommendation: Allow Transaction';
            recSubline.textContent = 'Standard low-risk transaction. Instant clearing approved.';
        }
    }

    // --------------------------------------------------------------------------
    // 9. Render System Reasons
    // --------------------------------------------------------------------------
    function renderSystemReasons(reasons, status) {
        systemReasonsList.innerHTML = '';

        if (!reasons || reasons.length === 0) {
            const cleanItem = document.createElement('div');
            cleanItem.className = 'reason-item clean';
            cleanItem.innerHTML = `
                <span class="reason-icon">✓</span>
                <span>No suspicious patterns detected</span>
            `;
            systemReasonsList.appendChild(cleanItem);
            return;
        }

        reasons.forEach(r => {
            const item = document.createElement('div');
            item.className = 'reason-item suspicious';
            item.innerHTML = `
                <span class="reason-icon">✓</span>
                <span>${escapeHtml(r)}</span>
            `;
            systemReasonsList.appendChild(item);
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --------------------------------------------------------------------------
    // 10. Fetch Live Model Specs for Footer
    // --------------------------------------------------------------------------
    async function loadModelSpecs() {
        try {
            const res = await fetch('/api/model-info');
            if (res.ok) {
                const info = await res.json();
                if (info.metrics && info.metrics.accuracy) {
                    liveAccuracy.textContent = `Accuracy: ${info.metrics.accuracy}%`;
                }
                if (info.metrics && info.metrics.total_samples) {
                    liveSamples.textContent = `${info.metrics.total_samples.toLocaleString()} Dataset Samples`;
                }
            }
        } catch (e) {
            // Silently fallback to static footer stats
        }
    }

    loadModelSpecs();
});
