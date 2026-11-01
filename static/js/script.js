/* =========================================================
   SpotBook — macOS / iOS Glassmorphism Engine Script
   Dual Dark/Light Mode Theme Toggle, Active States, Apple
   Toasts, and Shared UI Interactions.
   ========================================================= */

// Immediate Theme Initialization (prevents FOUC)
(function () {
    const savedTheme = localStorage.getItem('spotbook-theme') ||
        (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', savedTheme);
})();

document.addEventListener('DOMContentLoaded', function () {
    initThemeEngine();
    initAppleToasts();
    initPasswordToggle();
    initConfirmActions();
    initActiveNavLink();
});


/**
 * macOS Dynamic Dark / Light Mode Switcher
 * Persists user preference to localStorage and updates DOM.
 */
function initThemeEngine() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    updateToggleButtons(currentTheme);

    // Delegate click on any theme toggle element
    document.querySelectorAll('.theme-toggle-btn, .js-theme-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const activeTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('spotbook-theme', newTheme);
            updateToggleButtons(newTheme);

            // Optional custom event for charts or dynamic components
            window.dispatchEvent(new CustomEvent('spotbook-theme-change', { detail: { theme: newTheme } }));
        });
    });
}

function updateToggleButtons(theme) {
    document.querySelectorAll('.theme-toggle-btn, .js-theme-toggle').forEach(function (btn) {
        btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        btn.setAttribute('title', theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        const icon = btn.querySelector('.theme-toggle-thumb i, .theme-toggle-icon');
        if (icon) {
            if (theme === 'dark') {
                icon.className = 'bi bi-moon-stars-fill';
            } else {
                icon.className = 'bi bi-sun-fill';
            }
        }
    });
}


/**
 * Apple-style Toast / Floating Notification System
 * Auto-dismisses alerts smoothly with scale and fade.
 */
function initAppleToasts() {
    const alerts = document.querySelectorAll('.alert, .apple-toast-card, .js-alert');
    alerts.forEach(function (alertBox) {
        // Auto dismiss after 4.5 seconds
        setTimeout(function () {
            dismissToast(alertBox);
        }, 4500);

        // Click on close button
        const closeBtn = alertBox.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function (e) {
                e.preventDefault();
                dismissToast(alertBox);
            });
        }
    });
}

function dismissToast(el) {
    if (!el || !el.parentNode) return;
    el.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-20px) scale(0.96)';
    setTimeout(function () {
        if (el.parentNode) {
            el.remove();
        }
    }, 360);
}


/**
 * Show / hide a password field.
 */
function initPasswordToggle() {
    document.querySelectorAll('.js-toggle-password').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const field = document.getElementById(btn.getAttribute('data-target'));
            if (!field) return;

            const isHidden = field.type === 'password';
            field.type = isHidden ? 'text' : 'password';
            btn.textContent = isHidden ? 'Hide Password' : 'Show Password';
        });
    });
}


/**
 * Native confirmation modal before destructive actions.
 */
function initConfirmActions() {
    document.querySelectorAll('.js-confirm').forEach(function (el) {
        el.addEventListener('click', function (event) {
            const message = el.getAttribute('data-message') || 'Are you sure you want to perform this action?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
}


/**
 * Highlight active navigation link.
 */
function initActiveNavLink() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar nav a, .navbar-nav a, .site-nav a').forEach(function (link) {
        const linkPath = link.getAttribute('href');
        if (!linkPath || linkPath === '#') return;
        if (linkPath === currentPath) {
            link.classList.add('active');
        }
    });
}