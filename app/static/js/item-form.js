/**
 * The shared item form (_item_form.html): image picker + auto-fill on paste.
 *
 * Pasting (or typing and leaving) a product link asks our server to read the page (/scraper/scrape) and fills in
 * the details. Fields that already have something in them are left alone, unless "Fetch details again" is used.
 */
(function () {
    const form = document.querySelector('[data-item-form]');
    if (!form) return;

    const urlInput = form.querySelector('[data-autofill-url]');
    const status = form.querySelector('[data-autofill-status]');
    const refresh = form.querySelector('[data-autofill-refresh]');
    const fields = {
        name: form.querySelector('#name-input'),
        description: form.querySelector('#description-input'),
        price: form.querySelector('#price-input'),
    };

    // Image picker, preloaded with the item's current choices when editing
    const container = document.getElementById('image-selector-container');
    window.imageSelector = new ImageSelector('#image-selector-container');
    window.imageSelector.init('#image-input');
    let existing = [];
    try {
        existing = JSON.parse(container.dataset.images || '[]');
    } catch (e) {
        existing = [];
    }
    if (container.dataset.currentImage || existing.length) {
        window.imageSelector.loadExisting(container.dataset.currentImage, existing);
    }

    let lastFetched = urlInput.value.trim();

    function say(text, tone) {
        status.textContent = text;
        status.className = 'text-sm ' + ({ ok: 'text-green-400', error: 'text-yellow-300', busy: 'text-blue-300' }[tone] || 'text-gray-400');
    }

    function looksLikeLink(value) {
        return /^https?:\/\/\S+\.\S+/i.test(value);
    }

    async function autofill(overwrite) {
        const url = urlInput.value.trim();
        if (!looksLikeLink(url)) return;
        lastFetched = url;
        say('Looking up the product…', 'busy');
        refresh.classList.add('hidden');
        const result = await window.scrapeProductUrl(url);
        refresh.classList.remove('hidden');
        if (!result.success) {
            say(`Couldn't read that page (${result.error}). Fill in the details yourself.`, 'error');
            return;
        }
        const data = result.data;
        let filled = 0;
        for (const [key, input] of Object.entries(fields)) {
            const value = data[key];
            if (input && value !== undefined && value !== null && value !== '' && (overwrite || !input.value.trim())) {
                input.value = value;
                filled += 1;
            }
        }
        const images = (data.images && data.images.length) ? data.images : (data.image_url ? [data.image_url] : []);
        if (images.length && (overwrite || !form.querySelector('#image-input').value)) {
            window.imageSelector.setImages(images);
        }
        say(filled || images.length
            ? '✓ Filled in from the page. Check the details and change anything you like.'
            : 'Found the page but no product details. Fill them in yourself.', filled ? 'ok' : 'error');
    }

    urlInput.addEventListener('paste', () => setTimeout(() => autofill(false), 0));
    urlInput.addEventListener('change', () => {
        if (urlInput.value.trim() !== lastFetched) autofill(false);
    });
    refresh.addEventListener('click', () => autofill(true));
    if (lastFetched) refresh.classList.remove('hidden');
})();
