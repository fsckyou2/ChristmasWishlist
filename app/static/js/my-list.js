/**
 * My Wishlist (wishlist/my_list.html): add from a link, edit in place, ★ Most wanted, and reordering.
 *
 * Reordering works by dragging (mouse) or the ↑ ↓ buttons (everywhere, including phones). Items only move within
 * their own group: Most wanted items always stay above the rest.
 */
(function () {
    async function postJson(url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
        return data;
    }

    function reloadAt(hash) {
        window.location.hash = hash;
        window.location.reload();
    }

    // --- Add from a link -----------------------------------------------------------------------------------------
    const quickAdd = document.querySelector('[data-quick-add]');
    const quickStatus = document.querySelector('[data-quick-add-status]');
    let adding = false;

    async function addFromLink() {
        const url = quickAdd.value.trim();
        if (adding || !/^https?:\/\/\S+\.\S+/i.test(url)) return;
        adding = true;
        quickAdd.disabled = true;
        quickStatus.className = 'text-sm text-blue-300 mt-2';
        quickStatus.textContent = 'Looking up the product…';
        const scraped = await window.scrapeProductUrl(url);
        const data = scraped.success ? scraped.data : {};
        const body = {
            url: url,
            name: data.name || 'Item from ' + new URL(url).hostname.replace(/^www\./, ''),
            description: data.description || '',
            price: data.price || '',
            image_url: data.image_url || '',
            images: data.images || [],
        };
        try {
            const result = await postJson('/wishlist/add-item-from-scraped-data', body);
            const id = result.item_id;
            // Couldn't read the page: open the new item's editor so the details can be filled in
            reloadAt(scraped.success ? 'item-' + id : 'edit-' + id);
        } catch (error) {
            quickStatus.className = 'text-sm text-yellow-300 mt-2';
            quickStatus.textContent = error.message;
            quickAdd.disabled = false;
            adding = false;
        }
    }

    if (quickAdd) {
        quickAdd.addEventListener('paste', () => setTimeout(addFromLink, 0));
        quickAdd.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                addFromLink();
            }
        });
    }

    // Opened with #edit-<id>: show that item's editor
    const hashEdit = /^#edit-(\d+)$/.exec(window.location.hash);
    if (hashEdit) {
        const panel = document.getElementById('edit-' + hashEdit[1]);
        if (panel) {
            panel.classList.remove('hidden');
            panel.closest('li').scrollIntoView({ block: 'center' });
            const name = panel.querySelector('[data-field="name"]');
            if (name) name.focus();
        }
    }

    // --- Edit in place and ★ Most wanted --------------------------------------------------------------------------
    document.addEventListener('click', async (event) => {
        const save = event.target.closest('[data-save]');
        if (save) {
            const id = save.dataset.save;
            const panel = document.getElementById('edit-' + id);
            const error = panel.querySelector('[data-edit-error]');
            const body = {};
            panel.querySelectorAll('[data-field]').forEach((input) => {
                body[input.dataset.field] = input.value;
            });
            save.disabled = true;
            save.textContent = 'Saving…';
            try {
                await postJson('/wishlist/update-item/' + id, body);
                reloadAt('item-' + id);
            } catch (e) {
                error.textContent = e.message;
                save.disabled = false;
                save.textContent = 'Save changes';
            }
            return;
        }

        const star = event.target.closest('[data-star]');
        if (star) {
            star.disabled = true;
            try {
                await postJson('/wishlist/update-item/' + star.dataset.star, {
                    most_wanted: star.getAttribute('aria-pressed') !== 'true',
                });
                reloadAt('item-' + star.dataset.star);
            } catch (e) {
                star.disabled = false;
                window.alert(e.message);
            }
        }
    });

    // --- Reorder ----------------------------------------------------------------------------------------------------
    const list = document.querySelector('[data-sortable]');
    if (!list) return;
    const orderStatus = document.querySelector('[data-order-status]');
    const orderHint = orderStatus ? orderStatus.textContent : '';

    function sameGroup(a, b) {
        return a && b && a.dataset.mostWanted === b.dataset.mostWanted;
    }

    let saveTimer = null;
    function saveOrder() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(async () => {
            const ids = Array.from(list.children).map((li) => Number(li.dataset.itemId));
            try {
                await postJson('/wishlist/reorder', { item_ids: ids });
                if (orderStatus) orderStatus.textContent = '✓ Order saved.';
            } catch (e) {
                if (orderStatus) orderStatus.textContent = e.message;
            }
            setTimeout(() => {
                if (orderStatus) orderStatus.textContent = orderHint;
            }, 2500);
        }, 300);
    }

    list.addEventListener('click', (event) => {
        const move = event.target.closest('[data-move]');
        if (!move) return;
        const li = move.closest('li');
        if (move.dataset.move === 'up') {
            const prev = li.previousElementSibling;
            if (!sameGroup(prev, li)) return;
            list.insertBefore(li, prev);
        } else {
            const next = li.nextElementSibling;
            if (!sameGroup(next, li)) return;
            list.insertBefore(next, li);
        }
        move.focus();
        saveOrder();
    });

    // Drag and drop (mouse): only by the ⠿ handle, so text in the card stays selectable
    let dragged = null;
    list.querySelectorAll('[data-drag-handle]').forEach((handle) => {
        const li = handle.closest('li');
        handle.addEventListener('mousedown', () => li.setAttribute('draggable', 'true'));
        handle.addEventListener('mouseup', () => li.removeAttribute('draggable'));
    });
    list.addEventListener('dragstart', (event) => {
        dragged = event.target.closest('li');
        event.dataTransfer.effectAllowed = 'move';
        dragged.classList.add('opacity-50');
    });
    list.addEventListener('dragover', (event) => {
        const over = event.target.closest('li');
        if (!dragged || !over || over === dragged || !sameGroup(over, dragged)) return;
        event.preventDefault();
        const box = over.getBoundingClientRect();
        const after = event.clientY > box.top + box.height / 2;
        list.insertBefore(dragged, after ? over.nextElementSibling : over);
    });
    list.addEventListener('drop', (event) => event.preventDefault());
    list.addEventListener('dragend', () => {
        if (!dragged) return;
        dragged.classList.remove('opacity-50');
        dragged.removeAttribute('draggable');
        dragged = null;
        saveOrder();
    });
})();
