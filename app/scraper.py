import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re


class ProductScraper:
    """Scrape product information from URLs"""

    @staticmethod
    def scrape_url(url):
        """
        Scrape product information from a URL
        Returns dict with name, description, price, image_url
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            domain = urlparse(url).netloc

            # Try domain-specific scrapers first
            if 'amazon' in domain:
                return ProductScraper._scrape_amazon(soup)
            elif 'ebay' in domain:
                return ProductScraper._scrape_ebay(soup)
            elif 'walmart' in domain:
                return ProductScraper._scrape_walmart(soup)
            else:
                # Generic scraper
                return ProductScraper._scrape_generic(soup)

        except Exception as e:
            print(f"Error scraping URL: {e}")
            return None

    @staticmethod
    def _scrape_amazon(soup):
        """Scrape Amazon product page"""
        data = {}

        # Product name
        title = soup.find('span', {'id': 'productTitle'})
        if title:
            data['name'] = title.get_text().strip()

        # Description
        desc = soup.find('div', {'id': 'feature-bullets'})
        if desc:
            data['description'] = desc.get_text().strip()[:500]

        # Price - try multiple selectors
        price = None
        price_selectors = [
            {'class_': 'a-price-whole'},
            {'class_': 'a-offscreen'},
        ]
        for selector in price_selectors:
            price_elem = soup.find('span', selector)
            if price_elem:
                price_text = price_elem.get_text()
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    price = float(price_match.group())
                    break
        if price:
            data['price'] = price

        # Image
        img = soup.find('img', {'id': 'landingImage'})
        if not img:
            img = soup.find('img', {'class': 'a-dynamic-image'})
        if img and img.get('src'):
            data['image_url'] = img['src']

        return data if data else None

    @staticmethod
    def _scrape_ebay(soup):
        """Scrape eBay product page"""
        data = {}

        # Product name
        title = soup.find('h1', {'class': 'x-item-title__mainTitle'})
        if title:
            data['name'] = title.get_text().strip()

        # Price
        price = soup.find('div', {'class': 'x-price-primary'})
        if price:
            price_text = price.get_text()
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                data['price'] = float(price_match.group())

        # Image
        img = soup.find('img', {'id': 'icImg'})
        if img and img.get('src'):
            data['image_url'] = img['src']

        return data if data else None

    @staticmethod
    def _scrape_walmart(soup):
        """Scrape Walmart product page"""
        data = {}

        # Product name
        title = soup.find('h1', {'itemprop': 'name'})
        if title:
            data['name'] = title.get_text().strip()

        # Price
        price = soup.find('span', {'itemprop': 'price'})
        if price:
            price_text = price.get_text()
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                data['price'] = float(price_match.group())

        # Image
        img = soup.find('img', {'class': 'hover-zoom-hero-image'})
        if img and img.get('src'):
            data['image_url'] = img['src']

        return data if data else None

    @staticmethod
    def _scrape_generic(soup):
        """Generic scraper for unknown sites"""
        data = {}

        # Try common patterns for product name
        title = (
            soup.find('h1', {'class': re.compile('product.*title', re.I)}) or
            soup.find('h1', {'itemprop': 'name'}) or
            soup.find('meta', {'property': 'og:title'}) or
            soup.find('title')
        )
        if title:
            if title.get('content'):
                data['name'] = title['content'].strip()
            else:
                data['name'] = title.get_text().strip()

        # Try common patterns for description
        desc = (
            soup.find('meta', {'name': 'description'}) or
            soup.find('meta', {'property': 'og:description'})
        )
        if desc and desc.get('content'):
            data['description'] = desc['content'].strip()[:500]

        # Try common patterns for price
        price = (
            soup.find('span', {'class': re.compile('price', re.I)}) or
            soup.find('meta', {'property': 'product:price:amount'})
        )
        if price:
            price_text = price.get('content') if price.get('content') else price.get_text()
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                data['price'] = float(price_match.group())

        # Try common patterns for image
        img = (
            soup.find('meta', {'property': 'og:image'}) or
            soup.find('img', {'class': re.compile('product.*image', re.I)}) or
            soup.find('img', {'itemprop': 'image'})
        )
        if img:
            if img.get('content'):
                data['image_url'] = img['content']
            elif img.get('src'):
                data['image_url'] = img['src']

        return data if data else None
