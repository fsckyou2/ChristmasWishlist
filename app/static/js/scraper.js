/**
 * Product auto-fill. Asks our own server to read the product page (/scraper/scrape), which validates the URL,
 * blocks private-network addresses, and returns {success, data: {name, price, description, image_url, images}}.
 *
 * This used to fetch pages in the browser through public CORS proxies, which sent every product URL to third
 * parties; it now goes through the server only.
 */
async function scrapeProductUrl(url) {
    try {
        if (!url || !/^https?:\/\//i.test(url)) {
            throw new Error('Please enter a URL starting with http:// or https://');
        }
        const response = await fetch('/scraper/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Could not extract product information');
        }
        return { success: true, data: result.data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

window.scrapeProductUrl = scrapeProductUrl;
