/**
 * Image Selector Component
 * Allows users to select from multiple scraped images
 */

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

/** Same rule as the server: http(s) URLs or our own /static/ files. */
function isSafeImageUrl(value) {
    if (typeof value !== 'string' || !value) return false;
    if (/^\/static\/[A-Za-z0-9_\-./]+$/.test(value) && !value.includes('..')) return true;
    try {
        const url = new URL(value);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (e) {
        return false;
    }
}

class ImageSelector {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.images = [];
        this.selectedImage = null;
        this.imageUrlInput = null;
        this.availableImagesInput = null;
        this.defaultImageUrl = '/static/images/default-gift.svg';
    }

    /**
     * Initialize the image selector
     */
    init(imageUrlInputSelector, availableImagesInputSelector = null) {
        this.imageUrlInput = document.querySelector(imageUrlInputSelector);

        // Create or find hidden input for available_images
        if (availableImagesInputSelector) {
            this.availableImagesInput = document.querySelector(availableImagesInputSelector);
        } else {
            // Create hidden input if it doesn't exist
            this.availableImagesInput = document.createElement('input');
            this.availableImagesInput.type = 'hidden';
            this.availableImagesInput.name = 'available_images';
            this.availableImagesInput.id = 'available-images-input';
            this.imageUrlInput.parentElement.appendChild(this.availableImagesInput);
        }

        this.render();
    }

    /**
     * Set available images from scraped data
     */
    setImages(images) {
        // Always include default image as first option
        this.images = [this.defaultImageUrl];

        if (images && Array.isArray(images) && images.length > 0) {
            // Add scraped images, avoiding duplicates
            images.forEach(img => {
                if (isSafeImageUrl(img) && !this.images.includes(img)) {
                    this.images.push(img);
                }
            });
        }

        // Set selected to first scraped image (or default if no images)
        this.selectedImage = this.images.length > 1 ? this.images[1] : this.images[0];

        // Update inputs
        this.updateInputs();
        this.render();
    }

    /**
     * Load images from existing data (for edit form)
     */
    loadExisting(imageUrl, availableImages) {
        // Start with default image
        this.images = [this.defaultImageUrl];

        if (availableImages && Array.isArray(availableImages) && availableImages.length > 0) {
            availableImages.forEach(img => {
                if (isSafeImageUrl(img) && !this.images.includes(img)) {
                    this.images.push(img);
                }
            });
        }

        // Set selected image
        this.selectedImage = isSafeImageUrl(imageUrl) ? imageUrl : this.defaultImageUrl;

        // Make sure selected image is in the list
        if (this.selectedImage && !this.images.includes(this.selectedImage)) {
            this.images.push(this.selectedImage);
        }

        this.updateInputs();
        this.render();
    }

    /**
     * Select an image
     */
    selectImage(imageUrl) {
        if (!isSafeImageUrl(imageUrl)) return;
        this.selectedImage = imageUrl;
        this.updateInputs();
        this.render();
    }

    /**
     * Update form inputs
     */
    updateInputs() {
        if (this.imageUrlInput) {
            this.imageUrlInput.value = this.selectedImage || '';
        }
        if (this.availableImagesInput) {
            this.availableImagesInput.value = JSON.stringify(this.images);
        }
    }

    /**
     * Render the image selector UI. Built with DOM APIs so scraped URLs are never parsed as HTML.
     */
    render() {
        if (!this.container) return;
        this.container.replaceChildren();

        if (this.images.length === 0) {
            this.container.style.display = 'none';
            return;
        }
        this.container.style.display = 'block';

        const wrapper = el('div', 'bg-gray-700 rounded-lg p-4 mt-4');
        const label = el('label', 'block text-gray-200 font-semibold mb-3', 'Select Image ');
        label.appendChild(el('span', 'text-sm font-normal text-gray-400', '(Click to choose)'));
        wrapper.appendChild(label);

        const grid = el('div', 'grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3');
        this.images.forEach((img, index) => {
            const selected = img === this.selectedImage;
            const option = el(
                'div',
                'image-option cursor-pointer rounded-lg overflow-hidden border-2 transition-all ' +
                    (selected ? 'border-green-500 ring-2 ring-green-500' : 'border-gray-600 hover:border-gray-400')
            );
            option.dataset.imageUrl = img;
            option.addEventListener('click', () => this.selectImage(img));

            const frame = el('div', 'aspect-square bg-gray-800 flex items-center justify-center p-2');
            const image = el('img', 'max-w-full max-h-full object-contain');
            image.alt = `Option ${index + 1}`;
            image.referrerPolicy = 'no-referrer';
            image.addEventListener('error', () => {
                if (image.src !== new URL(this.defaultImageUrl, location.href).href) image.src = this.defaultImageUrl;
            }, { once: true });
            image.src = img;
            frame.appendChild(image);
            option.appendChild(frame);
            option.appendChild(el(
                'div',
                'bg-gray-600 px-2 py-1 text-xs text-center text-gray-300',
                img === this.defaultImageUrl ? 'Default' : `Image ${index}`
            ));
            grid.appendChild(option);
        });
        wrapper.appendChild(grid);
        wrapper.appendChild(el(
            'p',
            'text-xs text-gray-400 mt-3',
            'The first option is a default gift icon. Other images were found on the product page.'
        ));
        this.container.appendChild(wrapper);
    }

    /**
     * Clear all images
     */
    clear() {
        this.images = [this.defaultImageUrl];
        this.selectedImage = this.defaultImageUrl;
        this.updateInputs();
        this.render();
    }
}

// Make it available globally
window.ImageSelector = ImageSelector;
window.isSafeImageUrl = isSafeImageUrl;
