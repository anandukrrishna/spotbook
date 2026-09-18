/* =========================================================
   SpotBook — Base Script
   Shared behaviour for every page. Hooks by class/data-*
   attribute so templates never need inline JS.
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    initPasswordToggle();
    initConfirmActions();
    initActiveNavLink();
    initDismissibleAlerts();

});


/**
 * Show / hide a password field.
 * Usage:
 *   <input type="password" id="password">
 *   <button class="js-toggle-password" data-target="password">Show Password</button>
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
 * Ask for confirmation before following a destructive link.
 * Usage:
 *   <a href="#" class="js-confirm" data-message="Delete this slot?">Delete</a>
 */
function initConfirmActions() {

    document.querySelectorAll('.js-confirm').forEach(function (el) {

        el.addEventListener('click', function (event) {

            const message = el.getAttribute('data-message') || 'Are you sure?';

            if (!window.confirm(message)) {
                event.preventDefault();
            }

        });

    });

}


/**
 * Highlight the sidebar / nav link matching the current page.
 * Matches on exact path, or "starts with" for parent sections
 * (e.g. /admin_app/parking/ won't wrongly highlight for
 * /admin_app/parking/slots/).
 */
function initActiveNavLink() {

    const currentPath = window.location.pathname;

    document.querySelectorAll('.sidebar nav a, .site-nav a').forEach(function (link) {

        const linkPath = link.getAttribute('href');
        if (!linkPath || linkPath === '#') return;

        if (linkPath === currentPath) {
            link.classList.add('active');
        }

    });

}


/**
 * Let the user dismiss any alert by clicking it, and
 * auto-dismiss success alerts after a short delay so they
 * don't clutter the page on repeat visits.
 * Usage:
 *   <div class="alert alert-success js-alert">Saved.</div>
 */
function initDismissibleAlerts() {

    document.querySelectorAll('.js-alert').forEach(function (alertBox) {

        alertBox.style.cursor = 'pointer';
        alertBox.title = 'Click to dismiss';

        alertBox.addEventListener('click', function () {
            alertBox.remove();
        });

        if (alertBox.classList.contains('alert-success')) {
            setTimeout(function () {
                alertBox.remove();
            }, 4000);
        }

    });

}