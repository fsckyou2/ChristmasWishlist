/**
 * One-time banner after an email-link or password login: offer to save a passkey on this device so the next
 * login is a fingerprint/face tap instead of an email round trip. Requires passkey.js.
 */
(function () {
    const banner = document.getElementById('passkey-offer');
    if (!banner) return;

    function hide() {
        banner.remove();
    }

    function dismiss() {
        fetch('/passkey/dismiss-offer', { method: 'POST' }).catch(() => {});
        hide();
    }

    if (!window.passkey || !window.passkey.isSupported()) {
        dismiss();
        return;
    }
    banner.classList.remove('hidden');

    function deviceName() {
        const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || '';
        const kind = /android|iphone|ipad|mobile/i.test(navigator.userAgent) ? 'phone' : 'computer';
        return platform ? `My ${platform} ${kind}` : `My ${kind}`;
    }

    banner.querySelector('[data-passkey-offer="later"]').addEventListener('click', dismiss);
    banner.querySelector('[data-passkey-offer="setup"]').addEventListener('click', async (event) => {
        const button = event.currentTarget;
        const status = banner.querySelector('[data-passkey-offer="status"]');
        button.disabled = true;
        try {
            await window.passkey.register(deviceName());
            status.textContent = 'Done! Next time, just use your fingerprint or face to log in.';
            banner.querySelectorAll('button').forEach((b) => b.remove());
            setTimeout(hide, 4000);
        } catch (error) {
            // Cancelled, or this device already has one: don't nag, just stop offering this session
            status.textContent = 'No problem. You can set this up any time in Account Settings.';
            button.disabled = false;
            setTimeout(dismiss, 3000);
        }
    });
})();
