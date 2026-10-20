"""Input validation shared by forms, JSON endpoints and templates.

Every write path for wishlist items goes through clean_item_fields(), so the HTML form, the table view's JSON
endpoints and the delegate views all enforce the same rules. The display_* helpers are the render-time guard for
anything already stored in the database.
"""

import json
import math
import re
from urllib.parse import urlsplit

MAX_URL_LENGTH = 500
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000
MAX_QUANTITY = 999
MAX_PRICE = 1_000_000
MAX_AVAILABLE_IMAGES = 20
DEFAULT_GIFT_IMAGE = "/static/images/default-gift.svg"

_STATIC_PATH_RE = re.compile(r"^/static/[A-Za-z0-9_\-./]+$")


class ValidationError(ValueError):
    """Raised when user-supplied item data is invalid. The message is safe to show to the user."""


def clean_http_url(value, field="URL"):
    """Return a stripped http(s) URL, None for empty input, or raise ValidationError."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    value = value.strip()
    if not value:
        return None
    if len(value) > MAX_URL_LENGTH:
        raise ValidationError(f"{field} must be at most {MAX_URL_LENGTH} characters.")
    if any(ord(c) < 0x20 or c in "\"'<>\\` " for c in value):
        raise ValidationError(f"{field} contains characters that are not allowed.")
    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValidationError(f"{field} must start with http:// or https://")
    return value


def clean_image_url(value):
    """Images may be http(s) URLs or one of our own /static/ files."""
    if isinstance(value, str) and value.strip().startswith("/"):
        value = value.strip()
        if _STATIC_PATH_RE.match(value) and ".." not in value:
            return value
        raise ValidationError("Image URL must be http(s) or a /static/ path.")
    return clean_http_url(value, field="Image URL")


def clean_available_images(value):
    """Accept a list or a JSON-encoded list of image URLs; return a JSON string or None. Invalid entries are dropped."""
    if value in (None, "", []):
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError("Available images must be a JSON list.")
    if not isinstance(value, list):
        raise ValidationError("Available images must be a list.")
    cleaned = []
    for candidate in value:
        try:
            url = clean_image_url(candidate)
        except ValidationError:
            continue
        if url and url not in cleaned:
            cleaned.append(url)
        if len(cleaned) >= MAX_AVAILABLE_IMAGES:
            break
    return json.dumps(cleaned) if cleaned else None


def clean_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Item name is required.")
    value = value.strip()
    if len(value) > MAX_NAME_LENGTH:
        raise ValidationError(f"Item name must be at most {MAX_NAME_LENGTH} characters.")
    return value


def clean_description(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("Description must be text.")
    value = value.strip()
    if len(value) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters.")
    return value or None


def clean_price(value):
    if value in (None, ""):
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Price must be a number.")
    if not math.isfinite(price) or price < 0 or price > MAX_PRICE:
        raise ValidationError("Price must be between 0 and 1,000,000.")
    return round(price, 2)


def clean_quantity(value):
    if isinstance(value, bool):
        raise ValidationError("Quantity must be a whole number.")
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Quantity must be a whole number.")
    if isinstance(value, float) and not value.is_integer():
        raise ValidationError("Quantity must be a whole number.")
    if not 1 <= quantity <= MAX_QUANTITY:
        raise ValidationError(f"Quantity must be between 1 and {MAX_QUANTITY}.")
    return quantity


_CLEANERS = {
    "name": clean_name,
    "url": clean_http_url,
    "description": clean_description,
    "price": clean_price,
    "image_url": clean_image_url,
    "quantity": clean_quantity,
    "available_images": clean_available_images,
}


def clean_item_fields(data, partial=False):
    """Validate a dict of item fields. With partial=True only the keys present are validated (and returned)."""
    if not isinstance(data, dict):
        raise ValidationError("Expected an object of item fields.")
    cleaned = {}
    for field, cleaner in _CLEANERS.items():
        if field in data:
            cleaned[field] = cleaner(data[field])
        elif not partial:
            if field == "name":
                raise ValidationError("Item name is required.")
            if field == "quantity":
                cleaned[field] = 1
    return cleaned


# --- WTForms adapters -------------------------------------------------------------------------------------------


def wtf_validator(cleaner):
    """Wrap a clean_* function as a WTForms validator."""
    from wtforms.validators import ValidationError as WTFValidationError

    def _validator(form, field):
        try:
            cleaner(field.data)
        except ValidationError as exc:
            raise WTFValidationError(str(exc))

    return _validator


# --- Render-time guards (Jinja filters) -------------------------------------------------------------------------


def display_url(value):
    """Return the URL if it is safe to put in an href, else an empty string."""
    try:
        return clean_http_url(value) or ""
    except ValidationError:
        return ""


def display_image_url(value):
    """Return the image URL if it is safe to put in a src, else the default gift image."""
    try:
        return clean_image_url(value) or DEFAULT_GIFT_IMAGE
    except ValidationError:
        return DEFAULT_GIFT_IMAGE
