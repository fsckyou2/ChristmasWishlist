/**
 * Client-side product scraper
 * Uses CORS proxy to fetch product pages and extract information
 */

const CORS_PROXIES = [
    'https://corsproxy.io/?',
    'https://api.allorigins.win/raw?url=',
    'https://cors-anywhere.herokuapp.com/'
];

/**
 * Scrape Amazon product page
 */
function scrapeAmazon(doc) {
    const data = {};

    // Title - prioritize actual product title over meta tags
    const titleSelectors = [
        '#productTitle',
        'h1 span#productTitle',
        'h1#title',
        '#title',
        '[data-feature-name="title"] h1',
        'meta[property="og:title"]'
    ];

    for (const selector of titleSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const title = elem.getAttribute('content') || elem.textContent || '';
            const trimmedTitle = title.trim();
            // Skip if we got "Amazon.com" or similar site name
            if (trimmedTitle && !trimmedTitle.toLowerCase().startsWith('amazon')) {
                data.name = trimmedTitle;
                break;
            }
        }
    }

    // Fallback to meta title tag, but clean it up
    if (!data.name) {
        const metaTitle = doc.querySelector('meta[name="title"]');
        if (metaTitle) {
            let title = metaTitle.getAttribute('content') || '';
            // Remove "Amazon.com: " prefix if present
            if (title.startsWith('Amazon.com: ')) {
                title = title.replace('Amazon.com: ', '');
            }
            // Remove trailing store name like " : Tools & Home Improvement"
            if (title.includes(' : ')) {
                title = title.split(' : ')[0];
            }
            if (title.trim()) {
                data.name = title.trim();
            }
        }
    }

    // Price - prioritize meta tags and try multiple selectors
    const priceSelectors = [
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
        '.a-price .a-offscreen',
        '.a-price-whole',
        '#priceblock_ourprice',
        '#priceblock_dealprice',
        '.a-price[data-a-size="xl"] .a-offscreen',
        'span.priceToPay .a-offscreen'
    ];

    for (const selector of priceSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const priceText = elem.textContent || elem.getAttribute('content') || '';
            const match = priceText.replace(/[^\d.]/g, '').match(/(\d+\.?\d*)/);
            if (match && match[1]) {
                data.price = parseFloat(match[1]);
                break;
            }
        }
    }

    // Description - prioritize meta tags
    const descSelectors = [
        'meta[property="og:description"]',
        'meta[name="description"]',
        '#feature-bullets',
        '#productDescription',
        '[data-feature-name="featurebullets"]',
        '.product-description'
    ];

    for (const selector of descSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const desc = elem.getAttribute('content') || elem.textContent || '';
            if (desc.trim() && desc.trim().length > 20) {
                data.description = desc.trim().substring(0, 500);
                break;
            }
        }
    }

    // Images - collect multiple, prioritize meta tags
    const images = [];

    // Try og:image first (most reliable)
    const ogImg = doc.querySelector('meta[property="og:image"]');
    if (ogImg) {
        let imgUrl = ogImg.getAttribute('content');
        if (imgUrl && imgUrl.startsWith('http')) {
            imgUrl = imgUrl.split('._')[0] + '.jpg'; // Get full resolution
            images.push(imgUrl);
            data.image_url = imgUrl;
        }
    }

    // Try other image sources
    const imgSelectors = [
        '#landingImage',
        '#imgBlkFront',
        '.a-dynamic-image',
        '#imageBlock img',
        '[data-old-hires]'
    ];

    // Get primary image if we don't have one yet
    if (!data.image_url) {
        for (const selector of imgSelectors) {
            const elem = doc.querySelector(selector);
            if (elem) {
                let imgUrl = elem.getAttribute('data-old-hires') ||
                              elem.getAttribute('data-a-dynamic-image') ||
                              elem.src;
                if (imgUrl && imgUrl.startsWith('http')) {
                    imgUrl = imgUrl.split('._')[0] + '.jpg'; // Get full resolution
                    if (!images.includes(imgUrl)) {
                        images.push(imgUrl);
                    }
                    data.image_url = imgUrl;
                    break;
                }
            }
        }
    }

    // Get additional gallery images
    const galleryImgs = doc.querySelectorAll('.a-dynamic-image');
    for (const img of galleryImgs) {
        if (images.length >= 5) break;
        let imgUrl = img.getAttribute('data-old-hires') || img.src;
        if (imgUrl && imgUrl.startsWith('http')) {
            imgUrl = imgUrl.split('._')[0] + '.jpg';
            if (!images.includes(imgUrl)) {
                images.push(imgUrl);
            }
        }
    }

    if (images.length > 0) {
        data.images = images;
    }

    return data;
}

/**
 * Scrape eBay product page
 */
function scrapeEbay(doc) {
    const data = {};

    // Title
    const titleSelectors = [
        'h1.x-item-title__mainTitle',
        '.x-item-title',
        '[data-testid="x-item-title"]',
        'meta[property="og:title"]',
        'h1'
    ];

    for (const selector of titleSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const title = elem.getAttribute('content') || elem.textContent || '';
            if (title.trim()) {
                data.name = title.trim();
                break;
            }
        }
    }

    // Price
    const priceSelectors = [
        '.x-price-primary span',
        '.x-price-primary',
        '[itemprop="price"]',
        '.display-price',
        'meta[property="product:price:amount"]'
    ];

    for (const selector of priceSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const priceText = elem.getAttribute('content') || elem.textContent || '';
            const match = priceText.replace(/[^\d.]/g, '').match(/(\d+\.?\d*)/);
            if (match && match[1]) {
                data.price = parseFloat(match[1]);
                break;
            }
        }
    }

    // Description - try multiple approaches including meta tags
    const descSelectors = [
        'meta[property="og:description"]',
        'meta[name="description"]',
        '[data-testid="x-item-description"]',
        '.x-item-description',
        '#desc_div',
        '[itemprop="description"]',
        '.item-description',
        '#viTabs_0_panel'
    ];

    for (const selector of descSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const desc = elem.getAttribute('content') || elem.textContent || '';
            if (desc.trim() && desc.trim().length > 20) {
                data.description = desc.trim().substring(0, 500);
                break;
            }
        }
    }

    // Images - collect multiple
    const images = [];
    const imgSelectors = [
        'meta[property="og:image"]',
        '#icImg',
        '.ux-image-carousel-item img',
        '.img-pct img',
        '[data-testid="ux-image-carousel-item"] img',
        'img[itemprop="image"]',
        '.vi-image-gallery img'
    ];

    // Get primary image
    for (const selector of imgSelectors.slice(0, 3)) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const imgUrl = elem.getAttribute('content') ||
                          elem.getAttribute('data-src') ||
                          elem.src || '';
            if (imgUrl && imgUrl.startsWith('http')) {
                images.push(imgUrl);
                data.image_url = imgUrl;
                break;
            }
        }
    }

    // Get additional gallery images
    const galleryImgs = doc.querySelectorAll('.ux-image-carousel-item img, .vi-image-gallery img');
    for (const img of galleryImgs) {
        if (images.length >= 5) break;
        const imgUrl = img.getAttribute('data-src') || img.src;
        if (imgUrl && imgUrl.startsWith('http') && !images.includes(imgUrl)) {
            images.push(imgUrl);
        }
    }

    if (images.length > 0) {
        data.images = images;
    }

    return data;
}

/**
 * Scrape Walmart product page
 */
function scrapeWalmart(doc) {
    const data = {};

    // Title
    const titleSelectors = [
        'h1[itemprop="name"]',
        'h1.prod-ProductTitle',
        '[data-testid="product-title"]',
        'h1'
    ];

    for (const selector of titleSelectors) {
        const elem = doc.querySelector(selector);
        if (elem && elem.textContent.trim()) {
            data.name = elem.textContent.trim();
            break;
        }
    }

    // Price
    const priceSelectors = [
        '[itemprop="price"]',
        '.price-characteristic',
        '[data-testid="price-wrap"]',
        'span[class*="price"]'
    ];

    for (const selector of priceSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const priceText = elem.textContent || elem.getAttribute('content') || '';
            const match = priceText.replace(/[^\d.]/g, '').match(/(\d+\.?\d*)/);
            if (match && match[1]) {
                data.price = parseFloat(match[1]);
                break;
            }
        }
    }

    // Description
    const descSelectors = [
        '[itemprop="description"]',
        '.product-description',
        '[data-testid="product-description"]'
    ];

    for (const selector of descSelectors) {
        const elem = doc.querySelector(selector);
        if (elem && elem.textContent.trim()) {
            data.description = elem.textContent.trim().substring(0, 500);
            break;
        }
    }

    // Images - collect multiple
    const images = [];
    const imgSelectors = [
        'img[itemprop="image"]',
        '.hover-zoom-hero-image',
        '[data-testid="hero-image-container"] img'
    ];

    // Get primary image
    for (const selector of imgSelectors) {
        const elem = doc.querySelector(selector);
        if (elem && elem.src && elem.src.startsWith('http')) {
            images.push(elem.src);
            data.image_url = elem.src;
            break;
        }
    }

    // Get additional gallery images
    const galleryImgs = doc.querySelectorAll('.hover-zoom-hero-image, [class*="product-image"]');
    for (const img of galleryImgs) {
        if (images.length >= 5) break;
        if (img.src && img.src.startsWith('http') && !images.includes(img.src)) {
            images.push(img.src);
        }
    }

    if (images.length > 0) {
        data.images = images;
    }

    return data;
}

/**
 * Generic scraper using meta tags and common patterns
 */
function scrapeGeneric(doc) {
    const data = {};

    // Title - try meta tags first, then h1
    const titleSelectors = [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        'meta[property="twitter:title"]',
        'title',
        'h1'
    ];

    for (const selector of titleSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const title = elem.getAttribute('content') || elem.textContent || '';
            if (title.trim()) {
                data.name = title.trim();
                break;
            }
        }
    }

    // Price - try various common patterns including all meta tags
    const priceSelectors = [
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
        'meta[name="price"]',
        'meta[itemprop="price"]',
        '[itemprop="price"]',
        '[class*="price"]',
        '[id*="price"]',
        '[data-price]',
        'span.price',
        '.product-price',
        '.price'
    ];

    for (const selector of priceSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const priceText = elem.getAttribute('content') ||
                            elem.getAttribute('data-price') ||
                            elem.textContent || '';
            const match = priceText.replace(/[^\d.]/g, '').match(/(\d+\.?\d*)/);
            if (match && match[1]) {
                data.price = parseFloat(match[1]);
                break;
            }
        }
    }

    // Description - try meta tags and common content areas
    const descSelectors = [
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[name="twitter:description"]',
        'meta[itemprop="description"]',
        '[itemprop="description"]',
        '.description',
        '.product-description',
        '#description'
    ];

    for (const selector of descSelectors) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const desc = elem.getAttribute('content') || elem.textContent || '';
            if (desc.trim() && desc.trim().length > 20) {
                data.description = desc.trim().substring(0, 500);
                break;
            }
        }
    }

    // Images - collect multiple from meta tags and common patterns
    const images = [];
    const imgSelectors = [
        'meta[property="og:image"]',
        'meta[property="og:image:secure_url"]',
        'meta[name="twitter:image"]',
        'meta[name="twitter:image:src"]',
        'meta[itemprop="image"]',
        '[itemprop="image"]',
        'img.product-image',
        '.product-image img',
        '[class*="product"] img',
        'img[src*="product"]'
    ];

    // Get primary image from meta tags
    for (const selector of imgSelectors.slice(0, 6)) {
        const elem = doc.querySelector(selector);
        if (elem) {
            const imgUrl = elem.getAttribute('content') ||
                          elem.getAttribute('src') ||
                          elem.getAttribute('data-src') || '';
            if (imgUrl && imgUrl.startsWith('http')) {
                images.push(imgUrl);
                data.image_url = imgUrl;
                break;
            }
        }
    }

    // Get additional images
    const additionalImgs = doc.querySelectorAll('img.product-image, .product-image img, [class*="product"] img');
    for (const img of additionalImgs) {
        if (images.length >= 5) break;
        const imgUrl = img.src || img.getAttribute('data-src');
        if (imgUrl && imgUrl.startsWith('http') && !images.includes(imgUrl)) {
            images.push(imgUrl);
        }
    }

    if (images.length > 0) {
        data.images = images;
    }

    return data;
}

/**
 * Fetch page content with fallback proxies
 */
async function fetchWithProxy(url) {
    let lastError;

    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = proxy + encodeURIComponent(url);
            const response = await fetch(proxyUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const html = await response.text();

            if (!html || html.length < 100) {
                throw new Error('Invalid response');
            }

            return html;
        } catch (error) {
            console.warn(`Proxy ${proxy} failed:`, error.message);
            lastError = error;
            continue;
        }
    }

    throw new Error(`All proxies failed. Last error: ${lastError?.message || 'Unknown error'}`);
}

/**
 * Main scraper function - detects site and calls appropriate scraper
 */
async function scrapeProductUrl(url) {
    try {
        // Validate URL
        if (!url || !url.match(/^https?:\/\//)) {
            throw new Error('Invalid URL');
        }

        console.log('Attempting to scrape:', url);

        const hostname = new URL(url).hostname.toLowerCase();
        console.log('Detected hostname:', hostname);

        // Etsy has strong bot protection - prompt user to enter manually
        if (hostname.includes('etsy.')) {
            throw new Error('Etsy has strong bot protection. Please manually copy the product details from the Etsy page.');
        }

        // Client-side scraping for other sites
        // Fetch page through CORS proxy with fallbacks
        const html = await fetchWithProxy(url);
        console.log('Successfully fetched HTML, length:', html.length);

        // Parse HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Detect site and scrape accordingly
        let data = {};

        if (hostname.includes('amazon.')) {
            console.log('Using Amazon scraper');
            data = scrapeAmazon(doc);
        } else if (hostname.includes('ebay.')) {
            console.log('Using eBay scraper');
            data = scrapeEbay(doc);
        } else if (hostname.includes('walmart.')) {
            console.log('Using Walmart scraper');
            data = scrapeWalmart(doc);
        } else {
            console.log('Using Generic scraper');
            data = scrapeGeneric(doc);
        }

        console.log('Scraped data:', data);

        // Ensure we got at least a name
        if (!data.name) {
            // Try generic scraper as fallback
            console.log('No name found, trying generic scraper as fallback');
            data = scrapeGeneric(doc);

            if (!data.name) {
                throw new Error('Could not extract product information');
            }
        }

        return { success: true, data: data };

    } catch (error) {
        console.error('Scraping error:', error);
        return { success: false, error: error.message };
    }
}

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { scrapeProductUrl };
}
