/**
 * ==============================================================================
 * UPI Fraud Detection System - Main Global Scripts (main.js)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Drawer Toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('app-sidebar');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');

    const closeSidebar = () => {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('hidden');
    };

    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (sidebarBackdrop) sidebarBackdrop.classList.toggle('hidden');
        });

        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener('click', closeSidebar);
        }

        // Close sidebar if viewport grows to desktop width
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 1024) closeSidebar();
        });
    }

    // 2. Interactive Toggle Card Visual State
    document.querySelectorAll('.toggle-card').forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (checkbox) {
            if (checkbox.checked) card.classList.add('checked');
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) card.classList.add('checked');
                else card.classList.remove('checked');
            });
        }
    });

    // 3. Auto-dismiss Flash Alerts
    setTimeout(() => {
        document.querySelectorAll('.flash-alert').forEach(alert => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        });
    }, 5000);
});

// Global Toast Notification Helper
function showToast(message, type = 'danger') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; bottom:24px; right:24px; z-index:9999; display:flex; flex-direction:column; gap:10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `glass-card flash-alert ${type}`;
    toast.style.cssText = 'min-width:280px; padding:12px 18px; box-shadow:0 8px 24px rgba(0,0,0,0.5); animation:toastIn 0.3s ease;';
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

// Global INR Currency Formatter
function formatINR(val) {
    const num = parseFloat(val) || 0;
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
