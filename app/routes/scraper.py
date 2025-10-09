"""
Server-side product scraping routes
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
import requests
from bs4 import BeautifulSoup
import re

bp = Blueprint('scraper', __name__, url_prefix='/scraper')


@bp.route('/scrape', methods=['POST'])
@login_required
def scrape_url():
    """Server-side URL scraping endpoint"""
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'URL parameter is required'}), 400

        url = data['url']

        # Validate URL format
        if not url or not url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL format'}), 400

        # Detect site type
        hostname = requests.utils.urlparse(url).hostname.lower()

        # Check for Etsy (has strong bot protection)
        if 'etsy.' in hostname:
            return jsonify({
                'error': 'Etsy has strong bot protection. Please manually copy the product details from the Etsy page.'
            }), 400

        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract product information based on site
        product_data = {}

        if 'ebay.' in hostname:
            product_data = scrape_ebay(soup)
        elif 'amazon.' in hostname:
            product_data = scrape_amazon(soup)
        elif 'walmart.' in hostname:
            product_data = scrape_walmart(soup)
        else:
            product_data = scrape_generic(soup)

        # Ensure we got at least a title
        if not product_data.get('title') and not product_data.get('name'):
            # Try generic scraper as fallback
            product_data = scrape_generic(soup)

            if not product_data.get('title') and not product_data.get('name'):
                return jsonify({'error': 'Could not extract product information from this URL'}), 400

        return jsonify(product_data), 200

    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Scraping error: {str(e)}'}), 500


def scrape_ebay(soup):
    """Extract product data from eBay"""
    data = {}

    # Title
    title_selectors = [
        ('h1', {'class': 'x-item-title__mainTitle'}),
        ('h1', {'class': 'x-item-title'}),
        ('meta', {'property': 'og:title'}),
        ('h1', {})
    ]

    for tag, attrs in title_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == 'meta':
                data['title'] = elem.get('content', '').strip()
            else:
                data['title'] = elem.get_text(strip=True)
            if data['title']:
                break

    # Price
    price_selectors = [
        ('div', {'class': 'x-price-primary'}),
        ('span', {'itemprop': 'price'}),
        ('meta', {'property': 'product:price:amount'})
    ]

    for tag, attrs in price_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == 'meta':
                price_text = elem.get('content', '')
            else:
                price_text = elem.get_text(strip=True)

            # Extract numeric price
            match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if match:
                try:
                    data['price'] = float(match.group())
                    break
                except ValueError:
                    pass

    # Description
    desc_selectors = [
        ('meta', {'property': 'og:description'}),
        ('meta', {'name': 'description'}),
        ('div', {'class': 'x-item-description'})
    ]

    for tag, attrs in desc_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == 'meta':
                desc = elem.get('content', '').strip()
            else:
                desc = elem.get_text(strip=True)
            if desc and len(desc) > 20:
                data['description'] = desc[:500]
                break

    # Image
    img_selectors = [
        ('meta', {'property': 'og:image'}),
        ('img', {'id': 'icImg'}),
        ('img', {'itemprop': 'image'})
    ]

    for tag, attrs in img_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            if tag == 'meta':
                img_url = elem.get('content', '')
            else:
                img_url = elem.get('src', '') or elem.get('data-src', '')
            if img_url and img_url.startswith('http'):
                data['image'] = img_url
                break

    return data


def scrape_amazon(soup):
    """Extract product data from Amazon"""
    data = {}

    # Title
    title_elem = soup.find('span', {'id': 'productTitle'})
    if title_elem:
        data['title'] = title_elem.get_text(strip=True)

    # Price
    price_selectors = [
        ('span', {'class': 'a-price-whole'}),
        ('span', {'id': 'priceblock_ourprice'}),
        ('span', {'id': 'priceblock_dealprice'})
    ]

    for tag, attrs in price_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            price_text = elem.get_text(strip=True).replace(',', '')
            match = re.search(r'[\d.]+', price_text)
            if match:
                try:
                    data['price'] = float(match.group())
                    break
                except ValueError:
                    pass

    # Description
    desc_elem = soup.find('div', {'id': 'feature-bullets'})
    if desc_elem:
        data['description'] = desc_elem.get_text(strip=True)[:500]

    # Image
    img_elem = soup.find('img', {'id': 'landingImage'})
    if img_elem:
        data['image'] = img_elem.get('src', '')

    return data


def scrape_walmart(soup):
    """Extract product data from Walmart"""
    data = {}

    # Title
    title_elem = soup.find('h1', {'itemprop': 'name'})
    if title_elem:
        data['title'] = title_elem.get_text(strip=True)

    # Price
    price_elem = soup.find('span', {'itemprop': 'price'})
    if price_elem:
        price_text = price_elem.get_text(strip=True).replace(',', '')
        match = re.search(r'[\d.]+', price_text)
        if match:
            try:
                data['price'] = float(match.group())
            except ValueError:
                pass

    # Description
    desc_elem = soup.find('div', {'itemprop': 'description'})
    if desc_elem:
        data['description'] = desc_elem.get_text(strip=True)[:500]

    # Image
    img_elem = soup.find('img', {'itemprop': 'image'})
    if img_elem:
        data['image'] = img_elem.get('src', '')

    return data


def scrape_generic(soup):
    """Generic scraper using meta tags and common patterns"""
    data = {}

    # Title from meta tags
    meta_title = soup.find('meta', {'property': 'og:title'})
    if meta_title:
        data['title'] = meta_title.get('content', '').strip()
    elif soup.title:
        data['title'] = soup.title.string.strip()

    # Price from meta tags
    meta_price = soup.find('meta', {'property': 'product:price:amount'})
    if meta_price:
        try:
            data['price'] = float(meta_price.get('content', ''))
        except ValueError:
            pass

    # Description from meta tags
    meta_desc = soup.find('meta', {'property': 'og:description'}) or soup.find('meta', {'name': 'description'})
    if meta_desc:
        data['description'] = meta_desc.get('content', '').strip()[:500]

    # Image from meta tags
    meta_img = soup.find('meta', {'property': 'og:image'})
    if meta_img:
        data['image'] = meta_img.get('content', '')

    return data
