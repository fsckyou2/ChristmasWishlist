/**
 * Gifts I'm Giving (wishlist/my_claims.html): Bought / Arrived / Wrapped checkboxes, and the
 * "N to buy · N to wrap · N done" counts and progress bar that follow them.
 */
(function () {
    const COLORS = { purchased: 'text-blue-600', received: 'text-green-600', wrapped: 'text-purple-600' };

    function counts(scope) {
        const result = { toBuy: 0, toWrap: 0, done: 0, total: 0 };
        scope.querySelectorAll('[data-claim]').forEach((claim) => {
            const ticked = (status) => {
                const box = claim.querySelector(`.status-checkbox[data-status="${status}"]`);
                return box && box.checked;
            };
            result.total += 1;
            if (ticked('wrapped')) result.done += 1;
            else if (ticked('purchased')) result.toWrap += 1;
            else result.toBuy += 1;
        });
        return result;
    }

    function show(scope, container) {
        const c = counts(scope);
        const target = container || scope;
        target.querySelector('[data-to-buy]').textContent = c.toBuy;
        target.querySelector('[data-to-wrap]').textContent = c.toWrap;
        target.querySelector('[data-done]').textContent = c.done;
        return c;
    }

    function refresh() {
        document.querySelectorAll('[data-recipient]').forEach((section) => show(section));
        const overall = document.querySelector('[data-overall]');
        if (!overall) return;
        const c = show(document, overall);
        const bar = overall.querySelector('[data-progress-bar]');
        bar.style.width = (c.total ? Math.round((100 * c.done) / c.total) : 0) + '%';
        bar.parentElement.setAttribute('aria-valuenow', c.done);
    }

    document.querySelectorAll('.status-checkbox').forEach((checkbox) => {
        checkbox.addEventListener('change', async function () {
            const status = this.dataset.status;
            const isChecked = this.checked;
            try {
                const response = await fetch(`/wishlist/update-claim-status/${this.dataset.claimId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ [status]: isChecked }),
                });
                if (!response.ok) throw new Error('save failed');
                const label = this.nextElementSibling;
                label.classList.toggle('text-gray-400', !isChecked);
                label.classList.toggle(COLORS[status], isChecked);
                refresh();
            } catch (error) {
                this.checked = !isChecked;
                window.alert("Couldn't save that. Please try again.");
            }
        });
    });

    refresh();
})();
