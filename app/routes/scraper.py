"""
Server-side product scraping routes
"""

import json
import re

import requests
from bs4 import BeautifulSoup
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app import limiter
from app.net import BlockedDestination, ResponseTooLarge, check_url, fetch_text
from app.validation import ValidationError, clean_available_images, clean_http_url, display_image_url

bp = Blueprint("scraper", __name__, url_prefix="/scraper")

SCRAPER_API_ENDPOINT = "https://api.scraperapi.com/"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

SITE_SCRAPERS = {}  # filled in below the scraper definitions


def _scraper_rate_key():
    return f"user:{current_user.get_id()}"


def _pick_scraper(hostname):
    for marker, scraper in SITE_SCRAPERS.items():
        if marker in hostname:
            return scraper
    return scrape_generic


def _normalize(product_data):
    """Server uses "title"/"image"; the client expects "name"/"image_url". Image URLs are filtered to http(s)."""
    images = clean_available_images(product_data.get("images") or [])
    image = product_data.get("image") or ""
    return {
        "name": (product_data.get("title") or product_data.get("name") or "")[:200],
        "price": product_data.get("price"),
        "description": (product_data.get("description") or "")[:5000],
        "image_url": display_image_url(image) if image else "",
        "images": json.loads(images) if images else [],
    }


@bp.route("/scrape", methods=["POST"])
@login_required
@limiter.limit("20 per minute;200 per day", key_func=_scraper_rate_key)
def scrape_url():
    """Server-side URL scraping endpoint"""
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        url = clean_http_url(data["url"])
        if not url:
            raise ValidationError("URL is required")
        check_url(url)
    except (ValidationError, BlockedDestination) as exc:
        return jsonify({"error": f"Invalid URL: {exc}"}), 400

    hostname = (requests.utils.urlparse(url).hostname or "").lower()
    max_bytes = current_app.config["SCRAPER_MAX_BYTES"]
    scraper_api_key = current_app.config.get("SCRAPER_API_KEY")

    try:
        if scraper_api_key and ("amazon." in hostname or "etsy." in hostname):
            # ScraperAPI fetches the page from its own network; the key travels over HTTPS as a query param
            html = fetch_text(
                SCRAPER_API_ENDPOINT,
                params={"api_key": scraper_api_key, "url": url},
                timeout=60,
                max_bytes=max_bytes,
            )
        else:
            html = fetch_text(url, headers=BROWSER_HEADERS, timeout=10, max_bytes=max_bytes)
    except BlockedDestination as exc:
        return jsonify({"error": f"Invalid URL: {exc}"}), 400
    except ResponseTooLarge as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException as exc:
        current_app.logger.warning("Scrape fetch failed for %s: %s", hostname, exc.__class__.__name__)
        return jsonify({"error": "Could not fetch that page. You can enter the details manually."}), 400

    if "api-services-support@amazon" in html or "Robot Check" in html:
        return (
            jsonify(
                {
                    "error": "Amazon detected automated access. "
                    "Please manually copy the product details, or try again in a few minutes."
                }
            ),
            400,
        )

    try:
        soup = BeautifulSoup(html, "html.parser")
        product_data = _pick_scraper(hostname)(soup)
        if not product_data.get("title") and not product_data.get("name"):
            product_data = scrape_generic(soup)
    except Exception:
        current_app.logger.exception("Scraper parse error for %s", hostname)
        return jsonify({"error": "Could not read product information from this page."}), 500

    if not product_data.get("title") and not product_data.get("name"):
        return jsonify({"error": "Could not extract product information from this URL"}), 400

    current_app.logger.info("Scraped %s", hostname)
    return jsonify({"success": True, "data": _normalize(product_data)}), 200


def scrape_ebay(soup):
    """Extract product data from eBay"""
    data = {}

    # Title
    title_selectors = [
        ("h1", {"class": "x-item-title__mainTitle"}),
        ("h1", {"class": "x-item-title"}),
        ("meta", {"property": "og:title"}),
        ("h1", {}),
    ]

    for tag, attrs in title_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                data["title"] = elem.get("content", "").strip()
            else:
                data["title"] = elem.get_text(strip=True)
            if data["title"]:
                break

    # Price
    price_selectors = [
        ("div", {"class": "x-price-primary"}),
        ("span", {"itemprop": "price"}),
        ("meta", {"property": "product:price:amount"}),
    ]

    for tag, attrs in price_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                price_text = elem.get("content", "")
            else:
                price_text = elem.get_text(strip=True)

            # Extract numeric price
            match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
            if match:
                try:
                    data["price"] = float(match.group())
                    break
                except ValueError:
                    pass

    # Description
    desc_selectors = [
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
        ("div", {"class": "x-item-description"}),
    ]

    for tag, attrs in desc_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                desc = elem.get("content", "").strip()
            else:
                desc = elem.get_text(strip=True)
            if desc and len(desc) > 20:
                data["description"] = desc[:500]
                break

    # Images - collect multiple
    images = []
    img_selectors = [
        ("meta", {"property": "og:image"}),
        ("img", {"id": "icImg"}),
        ("img", {"itemprop": "image"}),
        ("div", {"class": "ux-image-carousel-item"}),
        ("img", {"class": "img-pct"}),
    ]

    # First get the primary image
    for tag, attrs in img_selectors[:3]:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                img_url = elem.get("content", "")
            else:
                img_url = elem.get("src", "") or elem.get("data-src", "")
            if img_url and img_url.startswith("http") and img_url not in images:
                images.append(img_url)
                data["image"] = img_url
                break

    # Get additional gallery images
    carousel_imgs = soup.find_all("img", {"class": "ux-image-carousel-item"})
    for img in carousel_imgs[:5]:
        img_url = img.get("src", "") or img.get("data-src", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            images.append(img_url)

    if images:
        data["images"] = images[:5]  # Limit to 5 images

    return data


def scrape_amazon(soup):
    """Extract product data from Amazon"""
    data = {}

    # Title - try multiple selectors (prioritize actual product title over meta tags)
    title_selectors = [
        ("span", {"id": "productTitle"}),
        ("h1", {"id": "title"}),
        ("meta", {"property": "og:title"}),
    ]

    for tag, attrs in title_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                title = elem.get("content", "").strip()
            else:
                title = elem.get_text(strip=True)

            # Skip if we got "Amazon.com" or similar site name
            if title and not title.lower().startswith("amazon"):
                data["title"] = title
                break

    # Fallback to meta title tag, but clean it up
    if not data.get("title"):
        meta_title = soup.find("meta", {"name": "title"})
        if meta_title:
            title = meta_title.get("content", "").strip()
            # Remove "Amazon.com: " prefix if present
            if title.startswith("Amazon.com: "):
                title = title.replace("Amazon.com: ", "", 1)
            # Remove trailing store name like " : Tools & Home Improvement"
            if " : " in title:
                title = title.split(" : ")[0]
            data["title"] = title

    # Price - try multiple selectors
    price_selectors = [
        ("span", {"class": "a-price-whole"}),
        ("span", {"class": "a-offscreen"}),
        ("span", {"id": "priceblock_ourprice"}),
        ("span", {"id": "priceblock_dealprice"}),
        ("span", {"id": "price_inside_buybox"}),
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "og:price:amount"}),
    ]

    for tag, attrs in price_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                price_text = elem.get("content", "")
            else:
                price_text = elem.get_text(strip=True)

            # Remove currency symbols and extract number
            price_text = price_text.replace("$", "").replace(",", "").strip()
            match = re.search(r"[\d.]+", price_text)
            if match:
                try:
                    data["price"] = float(match.group())
                    break
                except ValueError:
                    pass

    # Description - try multiple selectors
    desc_selectors = [
        ("div", {"id": "feature-bullets"}),
        ("div", {"id": "productDescription"}),
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
    ]

    for tag, attrs in desc_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                desc = elem.get("content", "").strip()
            else:
                desc = elem.get_text(strip=True)
            if desc and len(desc) > 20:
                data["description"] = desc[:500]
                break

    # Images - collect multiple from various sources
    images = []

    # Try og:image first (most reliable)
    og_img = soup.find("meta", {"property": "og:image"})
    if og_img:
        img_url = og_img.get("content", "")
        if img_url and img_url.startswith("http"):
            # Remove size parameters for full resolution
            img_url = img_url.split("._")[0] + ".jpg" if "._" in img_url else img_url
            images.append(img_url)
            data["image"] = img_url

    # Primary product image
    img_selectors = [
        ("img", {"id": "landingImage"}),
        ("img", {"id": "imgBlkFront"}),
        ("img", {"data-a-image-name": "landingImage"}),
    ]

    for tag, attrs in img_selectors:
        img_elem = soup.find(tag, attrs)
        if img_elem:
            img_url = img_elem.get("src", "") or img_elem.get("data-old-hires", "")
            if img_url and img_url.startswith("http") and img_url not in images:
                # Get full resolution by removing size parameters
                img_url = img_url.split("._")[0] + ".jpg" if "._" in img_url else img_url
                images.append(img_url)
                if not data.get("image"):
                    data["image"] = img_url

    # Additional images from gallery thumbnails
    thumb_imgs = soup.find_all("img", {"class": "a-dynamic-image"})
    for img in thumb_imgs[:5]:
        img_url = img.get("data-old-hires") or img.get("src", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            img_url = img_url.split("._")[0] + ".jpg" if "._" in img_url else img_url
            images.append(img_url)

    # Try alternate gallery structure
    alt_imgs = soup.find_all("img", {"class": "imageThumbnail"})
    for img in alt_imgs[:5]:
        img_url = img.get("src", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            img_url = img_url.split("._")[0] + ".jpg" if "._" in img_url else img_url
            images.append(img_url)

    if images:
        data["images"] = images[:5]  # Limit to 5 images

    return data


def scrape_walmart(soup):
    """Extract product data from Walmart"""
    data = {}

    # Title
    title_elem = soup.find("h1", {"itemprop": "name"})
    if title_elem:
        data["title"] = title_elem.get_text(strip=True)

    # Price
    price_elem = soup.find("span", {"itemprop": "price"})
    if price_elem:
        price_text = price_elem.get_text(strip=True).replace(",", "")
        match = re.search(r"[\d.]+", price_text)
        if match:
            try:
                data["price"] = float(match.group())
            except ValueError:
                pass

    # Description
    desc_elem = soup.find("div", {"itemprop": "description"})
    if desc_elem:
        data["description"] = desc_elem.get_text(strip=True)[:500]

    # Images - collect multiple
    images = []

    # Primary image
    img_elem = soup.find("img", {"itemprop": "image"})
    if img_elem:
        img_url = img_elem.get("src", "")
        if img_url and img_url.startswith("http"):
            images.append(img_url)
            data["image"] = img_url

    # Additional images from gallery
    gallery_imgs = soup.find_all("img", {"class": ["hover-zoom-hero-image", "prod-hero-image"]})
    for img in gallery_imgs[:5]:
        img_url = img.get("src", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            images.append(img_url)

    if images:
        data["images"] = images[:5]  # Limit to 5 images

    return data


def scrape_etsy(soup):
    """Extract product data from Etsy"""
    data = {}

    # Title
    title_selectors = [
        ("h1", {"data-buy-box-listing-title": True}),
        ("h1", {"class": "wt-text-body-03"}),
        ("meta", {"property": "og:title"}),
        ("h1", {}),
    ]

    for tag, attrs in title_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                data["title"] = elem.get("content", "").strip()
            else:
                data["title"] = elem.get_text(strip=True)
            if data["title"]:
                break

    # Price
    price_selectors = [
        ("div", {"class": "wt-text-title-03"}),
        ("p", {"class": "wt-text-title-03"}),
        ("meta", {"property": "product:price:amount"}),
    ]

    for tag, attrs in price_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                price_text = elem.get("content", "")
            else:
                price_text = elem.get_text(strip=True)

            # Extract numeric price
            match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
            if match:
                try:
                    data["price"] = float(match.group())
                    break
                except ValueError:
                    pass

    # Description
    desc_selectors = [
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
        ("div", {"data-product-details-description": True}),
        ("p", {"class": "wt-text-body-01"}),
    ]

    for tag, attrs in desc_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == "meta":
                desc = elem.get("content", "").strip()
            else:
                desc = elem.get_text(strip=True)
            if desc and len(desc) > 20:
                data["description"] = desc[:500]
                break

    # Images - collect multiple
    images = []

    # Primary image from meta tag
    og_img = soup.find("meta", {"property": "og:image"})
    if og_img:
        img_url = og_img.get("content", "")
        if img_url and img_url.startswith("http"):
            images.append(img_url)
            data["image"] = img_url

    # Additional images from gallery
    gallery_imgs = soup.find_all("img", {"data-listing-card-listing-image": True})
    for img in gallery_imgs[:5]:
        img_url = img.get("src", "") or img.get("data-src", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            images.append(img_url)

    # Fallback to common image patterns
    if len(images) < 3:
        product_imgs = soup.find_all("img", {"class": ["wt-max-width-full", "listing-image"]}, limit=5)
        for img in product_imgs:
            img_url = img.get("src", "") or img.get("data-src", "")
            if img_url and img_url.startswith("http") and img_url not in images:
                images.append(img_url)

    if images:
        data["images"] = images[:5]  # Limit to 5 images

    return data


def scrape_generic(soup):
    """Generic scraper using meta tags and common patterns"""
    data = {}

    # Title from meta tags
    meta_title = soup.find("meta", {"property": "og:title"})
    if meta_title:
        data["title"] = meta_title.get("content", "").strip()
    elif soup.title:
        data["title"] = soup.title.string.strip()

    # Price from meta tags
    meta_price = soup.find("meta", {"property": "product:price:amount"})
    if meta_price:
        try:
            data["price"] = float(meta_price.get("content", ""))
        except ValueError:
            pass

    # Description from meta tags
    meta_desc = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
    if meta_desc:
        data["description"] = meta_desc.get("content", "").strip()[:500]

    # Images - collect multiple from meta tags and common patterns
    images = []

    # Primary og:image
    meta_img = soup.find("meta", {"property": "og:image"})
    if meta_img:
        img_url = meta_img.get("content", "")
        if img_url and img_url.startswith("http"):
            images.append(img_url)
            data["image"] = img_url

    # Additional meta images
    meta_imgs = soup.find_all("meta", {"property": ["og:image", "og:image:secure_url", "twitter:image"]})
    for meta in meta_imgs[:5]:
        img_url = meta.get("content", "")
        if img_url and img_url.startswith("http") and img_url not in images:
            images.append(img_url)

    # Fallback to common image patterns
    if len(images) < 3:
        common_imgs = soup.find_all("img", {"class": ["product-image", "main-image"]}, limit=3)
        for img in common_imgs:
            img_url = img.get("src", "") or img.get("data-src", "")
            if img_url and img_url.startswith("http") and img_url not in images:
                images.append(img_url)

    if images:
        data["images"] = images[:5]  # Limit to 5 images

    return data


SITE_SCRAPERS.update(
    {
        "ebay.": scrape_ebay,
        "amazon.": scrape_amazon,
        "walmart.": scrape_walmart,
        "etsy.": scrape_etsy,
    }
)
