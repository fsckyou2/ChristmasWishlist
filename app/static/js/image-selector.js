/**
 * Image Selector Component
 * Allows users to select from multiple scraped images
 */

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
                if (img && !this.images.includes(img)) {
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
                if (img && !this.images.includes(img)) {
                    this.images.push(img);
                }
            });
        }

        // Set selected image
        this.selectedImage = imageUrl || this.defaultImageUrl;

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
     * Render the image selector UI
     */
    render() {
        if (!this.container) return;

        // Only show if there are multiple images to choose from
        if (this.images.length <= 1) {
            this.container.innerHTML = '';
            this.container.style.display = 'none';
            return;
        }

        this.container.style.display = 'block';

        const html = `
            <div class="bg-gray-700 rounded-lg p-4 mt-4">
                <label class="block text-gray-200 font-semibold mb-3">
                    Select Image
                    <span class="text-sm font-normal text-gray-400">(Click to choose)</span>
                </label>
                <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
                    ${this.images.map((img, index) => `
                        <div
                            class="image-option cursor-pointer rounded-lg overflow-hidden border-2 transition-all
                                   ${img === this.selectedImage ? 'border-green-500 ring-2 ring-green-500' : 'border-gray-600 hover:border-gray-400'}"
                            data-image-url="${img}"
                            onclick="window.imageSelector.selectImage('${img.replace(/'/g, "\\'")}')"
                        >
                            <div class="aspect-square bg-gray-800 flex items-center justify-center p-2">
                                <img
                                    src="${img}"
                                    alt="Option ${index + 1}"
                                    class="max-w-full max-h-full object-contain"
                                    onerror="this.src='${this.defaultImageUrl}'"
                                />
                            </div>
                            ${img === this.defaultImageUrl ?
                                '<div class="bg-gray-600 px-2 py-1 text-xs text-center text-gray-300">Default</div>' :
                                '<div class="bg-gray-600 px-2 py-1 text-xs text-center text-gray-300">Image ' + (index) + '</div>'
                            }
                        </div>
                    `).join('')}
                </div>
                <p class="text-xs text-gray-400 mt-3">
                    The first option is a default gift icon. Other images were found on the product page.
                </p>
            </div>
        `;

        this.container.innerHTML = html;
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
