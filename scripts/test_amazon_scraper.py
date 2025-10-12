#!/usr/bin/env python3
"""
Debug script to test Amazon scraping
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# Example Amazon URL
test_url = "https://www.amazon.com/dp/B08N5WRWNW"  # Example product

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

print(f"Testing Amazon scraper with URL: {test_url}")
print("-" * 80)

try:
    response = requests.get(test_url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} bytes")
    print("-" * 80)

    soup = BeautifulSoup(response.text, "html.parser")

    # Check for CAPTCHA or bot detection
    if "Enter the characters you see below" in response.text or "robot" in response.text.lower():
        print("⚠️  Amazon bot detection triggered!")
        print()

    # Test title extraction
    print("Title extraction attempts:")
    title_elem = soup.find("span", {"id": "productTitle"})
    if title_elem:
        print(f"  ✓ productTitle: {title_elem.get_text(strip=True)[:100]}")
    else:
        print("  ✗ productTitle not found")

    og_title = soup.find("meta", {"property": "og:title"})
    if og_title:
        print(f"  ✓ og:title: {og_title.get('content', '')[:100]}")
    else:
        print("  ✗ og:title not found")

    print()

    # Test image extraction
    print("Image extraction attempts:")
    og_img = soup.find("meta", {"property": "og:image"})
    if og_img:
        print(f"  ✓ og:image: {og_img.get('content', '')[:100]}")
    else:
        print("  ✗ og:image not found")

    landing_img = soup.find("img", {"id": "landingImage"})
    if landing_img:
        print(f"  ✓ landingImage: {landing_img.get('src', '')[:100]}")
    else:
        print("  ✗ landingImage not found")

    print()

    # Test price extraction
    print("Price extraction attempts:")
    price_whole = soup.find("span", {"class": "a-price-whole"})
    if price_whole:
        print(f"  ✓ a-price-whole: {price_whole.get_text(strip=True)}")
    else:
        print("  ✗ a-price-whole not found")

    price_offscreen = soup.find("span", {"class": "a-offscreen"})
    if price_offscreen:
        print(f"  ✓ a-offscreen: {price_offscreen.get_text(strip=True)}")
    else:
        print("  ✗ a-offscreen not found")

    print()

    # Test description extraction
    print("Description extraction attempts:")
    feature_bullets = soup.find("div", {"id": "feature-bullets"})
    if feature_bullets:
        print(f"  ✓ feature-bullets: {feature_bullets.get_text(strip=True)[:100]}...")
    else:
        print("  ✗ feature-bullets not found")

    og_desc = soup.find("meta", {"property": "og:description"})
    if og_desc:
        print(f"  ✓ og:description: {og_desc.get('content', '')[:100]}...")
    else:
        print("  ✗ og:description not found")

    print()
    print("-" * 80)
    print("Note: Amazon often returns different HTML to bots. The og: meta tags are most reliable for scraping.")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
