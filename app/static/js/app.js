/**
 * Site-wide behaviour. Loaded in <head> on every page, before page scripts.
 *
 * - Adds the CSRF token to same-origin, state-changing fetch() calls.
 * - Confirmation prompts via data-confirm="..." on forms or submit buttons (no inline handlers; see the CSP).
 * - Navigation toggles.
 */
(function () {
    const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS'];

    function csrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    const nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
        init = init || {};
        const method = (init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
        const url = new URL(input instanceof Request ? input.url : input, window.location.href);
        if (!SAFE_METHODS.includes(method) && url.origin === window.location.origin) {
            const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
            if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', csrfToken());
            init = Object.assign({}, init, { headers: headers });
        }
        return nativeFetch(input, init);
    };

    window.csrfToken = csrfToken;

    /** Escape text for insertion into HTML built from template strings. */
    window.escapeHtml = function (value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    document.addEventListener('submit', function (event) {
        const form = event.target;
        const button = event.submitter;
        const message = (button && button.dataset.confirm) || form.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });

    document.addEventListener('click', function (event) {
        const toggle = event.target.closest('[data-toggle-target]');
        if (toggle) {
            const target = document.getElementById(toggle.dataset.toggleTarget);
            if (target) target.classList.toggle('hidden');
            const icon = toggle.dataset.toggleIcon && document.getElementById(toggle.dataset.toggleIcon);
            if (icon) icon.classList.toggle('rotate-180');
        }
    });
})();
