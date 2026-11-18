/**
 * Gifts I'm Giving (wishlist/my_claims.html): Bought / Arrived / Wrapped checkboxes, the private "My price"
 * field, and the totals that follow them - "N to buy · N to wrap · N done", the progress bar and the spend.
 *
 * Totals are recomputed in the browser from each card's own numbers, so one saved price updates the recipient
 * and overall figures without reloading the page.
 */
(function () {
    const COLORS = { purchased: 'text-blue-600', received: 'text-green-600', wrapped: 'text-purple-600' };

    const money = (value) => '$' + value.toFixed(2);

    /** What this card counts towards the spend: the giver's own price if they gave one, else the item's. */
    function effectivePrice(claim) {
        const input = claim.querySelector('[data-claim-price]');
        const own = input ? input.value.trim() : '';
        const raw = own !== '' ? own : (claim.dataset.itemPrice || '').trim();
        if (raw === '') return null;
        const price = Number(raw);
        return Number.isFinite(price) ? price : null;
    }

    function totals(scope) {
        const result = { toBuy: 0, toWrap: 0, done: 0, total: 0, spend: 0, unpriced: 0 };
        scope.querySelectorAll('[data-claim]').forEach((claim) => {
            const ticked = (status) => {
                const box = claim.querySelector(`.status-checkbox[data-status="${status}"]`);
                return box && box.checked;
            };
            result.total += 1;
            if (ticked('wrapped')) result.done += 1;
            else if (ticked('purchased')) result.toWrap += 1;
            else result.toBuy += 1;

            const price = effectivePrice(claim);
            if (price === null) result.unpriced += 1;
            else result.spend += price * (Number(claim.dataset.quantity) || 1);
        });
        return result;
    }

    function show(scope, container) {
        const t = totals(scope);
        const target = container || scope;
        target.querySelector('[data-to-buy]').textContent = t.toBuy;
        target.querySelector('[data-to-wrap]').textContent = t.toWrap;
        target.querySelector('[data-done]').textContent = t.done;

        const spend = target.querySelector('[data-spend]');
        if (spend) spend.textContent = money(t.spend);
        const unpriced = target.querySelector('[data-unpriced]');
        if (unpriced) unpriced.textContent = t.unpriced;
        const note = target.querySelector('[data-unpriced-note]');
        if (note) note.classList.toggle('hidden', t.unpriced === 0);
        return t;
    }

    function refresh() {
        document.querySelectorAll('[data-recipient]').forEach((section) => show(section));
        const overall = document.querySelector('[data-overall]');
        if (!overall) return;
        const t = show(document, overall);
        const bar = overall.querySelector('[data-progress-bar]');
        bar.style.width = (t.total ? Math.round((100 * t.done) / t.total) : 0) + '%';
        bar.parentElement.setAttribute('aria-valuenow', t.done);
    }

    /** Redraw one card's own line total from whatever price now applies to it. */
    function showLineTotal(claim) {
        const line = claim.querySelector('[data-line-total]');
        if (!line) return;
        const price = effectivePrice(claim);
        line.classList.toggle('hidden', price === null);
        if (price !== null) line.textContent = money(price * (Number(claim.dataset.quantity) || 1));
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

    document.querySelectorAll('[data-claim-price]').forEach((input) => {
        const claim = input.closest('[data-claim]');
        const state = claim && claim.querySelector('[data-price-state]');
        let saved = input.value;

        input.addEventListener('change', async function () {
            if (this.value === saved) return;
            if (state) state.textContent = 'Saving…';
            try {
                const response = await fetch(`/wishlist/update-claim-price/${this.dataset.claimPrice}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ price: this.value.trim() }),
                });
                const body = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(body.error || 'save failed');
                // Show the figure the server actually stored (rounded to cents, or cleared).
                this.value = body.price === null || body.price === undefined ? '' : Number(body.price).toFixed(2);
                saved = this.value;
                if (state) state.textContent = 'Saved';
                showLineTotal(claim);
                refresh();
            } catch (error) {
                this.value = saved;
                if (state) state.textContent = '';
                window.alert(error.message || "Couldn't save that. Please try again.");
            }
        });
    });

    refresh();
})();
