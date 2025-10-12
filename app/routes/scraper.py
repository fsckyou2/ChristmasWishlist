"""
Server-side product scraping routes
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
import requests
from bs4 import BeautifulSoup
import re

bp = Blueprint("scraper", __name__, url_prefix="/scraper")


@bp.route("/scrape", methods=["POST"])
@login_required
def scrape_url():
    """Server-side URL scraping endpoint"""
    try:
        data = request.get_json()

        if not data or "url" not in data:
            return jsonify({"error": "URL parameter is required"}), 400

        url = data["url"]

        # Validate URL format
        if not url or not url.startswith(("http://", "https://")):
            return jsonify({"error": "Invalid URL format"}), 400

        # Detect site type
        hostname = requests.utils.urlparse(url).hostname.lower()

        # Check for Etsy (has strong bot protection)
        if "etsy." in hostname:
            error_msg = (
                "Etsy has strong bot protection. " "Please manually copy the product details from the Etsy page."
            )
            return jsonify({"error": error_msg}), 400

        # Fetch the page
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract product information based on site
        product_data = {}

        if "ebay." in hostname:
            product_data = scrape_ebay(soup)
            current_app.logger.info(f"eBay scrape result: {product_data}")
        elif "amazon." in hostname:
            product_data = scrape_amazon(soup)
            current_app.logger.info(f"Amazon scrape result: {product_data}")
        elif "walmart." in hostname:
            product_data = scrape_walmart(soup)
            current_app.logger.info(f"Walmart scrape result: {product_data}")
        else:
            product_data = scrape_generic(soup)
            current_app.logger.info(f"Generic scrape result: {product_data}")

        # Ensure we got at least a title
        if not product_data.get("title") and not product_data.get("name"):
            # Try generic scraper as fallback
            current_app.logger.warning(f"No title found with primary scraper, trying generic for {hostname}")
            product_data = scrape_generic(soup)

            if not product_data.get("title") and not product_data.get("name"):
                current_app.logger.error(f"Failed to extract any product data from {url}")
                return jsonify({"error": "Could not extract product information from this URL"}), 400

        # Normalize keys for consistency with client-side scraper
        # Server uses "title" and "image", client uses "name" and "image_url"
        normalized_data = {
            "success": True,
            "data": {
                "name": product_data.get("title", ""),
                "price": product_data.get("price"),
                "description": product_data.get("description", ""),
                "image_url": product_data.get("image", ""),
                "images": product_data.get("images", []),
            },
        }

        return jsonify(normalized_data), 200

    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Scraping error: {str(e)}"}), 500


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
