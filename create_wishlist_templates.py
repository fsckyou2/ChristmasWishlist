"""
Script to create wishlist and admin templates
"""

import os

TEMPLATES_DIR = 'app/templates'

TEMPLATES = {
    'wishlist/my_list.html': '''{% extends "base.html" %}

{% block title %}My Wishlist{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
        <h1 class="text-4xl font-bold">My Wishlist</h1>
        <a href="{{ url_for('wishlist.add_item') }}" class="bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700">
            + Add Item
        </a>
    </div>

    {% if items %}
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for item in items %}
                <div class="bg-white rounded-lg shadow-lg overflow-hidden {% if item.is_fully_purchased %}purchased{% endif %}">
                    {% if item.image_url %}
                        <img src="{{ item.image_url }}" alt="{{ item.name }}" class="w-full h-48 object-cover">
                    {% else %}
                        <div class="w-full h-48 bg-gray-200 flex items-center justify-center text-6xl">🎁</div>
                    {% endif %}

                    <div class="p-4">
                        <h3 class="text-xl font-bold mb-2">{{ item.name }}</h3>
                        {% if item.description %}
                            <p class="text-gray-600 text-sm mb-3 line-clamp-2">{{ item.description }}</p>
                        {% endif %}

                        <div class="flex justify-between items-center mb-3">
                            {% if item.price %}
                                <span class="text-lg font-semibold text-green-600">${{ "%.2f"|format(item.price) }}</span>
                            {% else %}
                                <span class="text-gray-400">No price</span>
                            {% endif %}
                            <span class="text-sm text-gray-600">Qty: {{ item.quantity }}</span>
                        </div>

                        {% if item.is_fully_purchased %}
                            <div class="bg-green-100 text-green-800 px-3 py-2 rounded text-center mb-3">
                                ✓ Fully Purchased
                            </div>
                        {% elif item.total_purchased > 0 %}
                            <div class="bg-yellow-100 text-yellow-800 px-3 py-2 rounded text-center mb-3">
                                {{ item.total_purchased }}/{{ item.quantity }} Purchased
                            </div>
                        {% endif %}

                        <div class="flex gap-2">
                            {% if item.url %}
                                <a href="{{ item.url }}" target="_blank" class="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-center text-sm hover:bg-blue-700">
                                    View
                                </a>
                            {% endif %}
                            <a href="{{ url_for('wishlist.edit_item', item_id=item.id) }}" class="flex-1 bg-gray-600 text-white px-3 py-2 rounded text-center text-sm hover:bg-gray-700">
                                Edit
                            </a>
                            <form method="POST" action="{{ url_for('wishlist.delete_item', item_id=item.id) }}" class="flex-1">
                                <button type="submit" onclick="return confirm('Delete this item?')" class="w-full bg-red-600 text-white px-3 py-2 rounded text-sm hover:bg-red-700">
                                    Delete
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="bg-white rounded-lg shadow p-12 text-center">
            <div class="text-6xl mb-4">📝</div>
            <h2 class="text-2xl font-bold mb-4">Your wishlist is empty</h2>
            <p class="text-gray-600 mb-6">Start adding items to let others know what you'd like!</p>
            <a href="{{ url_for('wishlist.add_item') }}" class="inline-block bg-green-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-green-700">
                Add Your First Item
            </a>
        </div>
    {% endif %}
</div>
{% endblock %}
''',

    'wishlist/add_item.html': '''{% extends "base.html" %}

{% block title %}Add Item{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Add Item to Wishlist</h1>

    <div class="bg-white rounded-lg shadow-lg p-8">
        <div class="mb-6 p-4 bg-blue-50 rounded">
            <p class="text-sm text-gray-700">
                <strong>Tip:</strong> Paste a URL from Amazon, eBay, or Walmart and we'll try to automatically fill in the details!
            </p>
        </div>

        <form method="POST" id="itemForm" class="space-y-4">
            {{ form.hidden_tag() }}

            <div>
                {{ form.url.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.url(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", id="url-input", placeholder="https://www.amazon.com/product...") }}
                <button type="button" id="scrape-btn" class="mt-2 bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
                    Auto-Fill from URL
                </button>
                {% if form.url.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.url.errors[0] }}</p>
                {% endif %}
            </div>

            <div>
                {{ form.name.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.name(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", id="name-input", required=true) }}
                {% if form.name.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.name.errors[0] }}</p>
                {% endif %}
            </div>

            <div>
                {{ form.description.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.description(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", rows=3, id="description-input") }}
                {% if form.description.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.description.errors[0] }}</p>
                {% endif %}
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div>
                    {{ form.price.label(class="block text-gray-700 font-semibold mb-2") }}
                    {{ form.price(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", step="0.01", id="price-input") }}
                    {% if form.price.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.price.errors[0] }}</p>
                    {% endif %}
                </div>

                <div>
                    {{ form.quantity.label(class="block text-gray-700 font-semibold mb-2") }}
                    {{ form.quantity(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
                    {% if form.quantity.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.quantity.errors[0] }}</p>
                    {% endif %}
                </div>
            </div>

            <div>
                {{ form.image_url.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.image_url(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", id="image-input") }}
                {% if form.image_url.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.image_url.errors[0] }}</p>
                {% endif %}
            </div>

            <div class="flex gap-4">
                {{ form.submit(class="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 cursor-pointer") }}
                <a href="{{ url_for('wishlist.my_list') }}" class="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 text-center">
                    Cancel
                </a>
            </div>
        </form>
    </div>
</div>

<script>
document.getElementById('scrape-btn').addEventListener('click', async function() {
    const url = document.getElementById('url-input').value;
    if (!url) {
        alert('Please enter a URL first');
        return;
    }

    this.disabled = true;
    this.textContent = 'Loading...';

    try {
        const response = await fetch('{{ url_for("wishlist.scrape_url") }}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (response.ok) {
            if (data.name) document.getElementById('name-input').value = data.name;
            if (data.description) document.getElementById('description-input').value = data.description;
            if (data.price) document.getElementById('price-input').value = data.price;
            if (data.image_url) document.getElementById('image-input').value = data.image_url;
            alert('Product information loaded!');
        } else {
            alert(data.error || 'Could not extract product information');
        }
    } catch (error) {
        alert('Error loading product information');
    } finally {
        this.disabled = false;
        this.textContent = 'Auto-Fill from URL';
    }
});
</script>
{% endblock %}
''',

    'wishlist/edit_item.html': '''{% extends "base.html" %}

{% block title %}Edit Item{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Edit Wishlist Item</h1>

    <div class="bg-white rounded-lg shadow-lg p-8">
        <form method="POST" class="space-y-4">
            {{ form.hidden_tag() }}

            <div>
                {{ form.url.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.url(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
                {% if form.url.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.url.errors[0] }}</p>
                {% endif %}
            </div>

            <div>
                {{ form.name.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.name(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", required=true) }}
                {% if form.name.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.name.errors[0] }}</p>
                {% endif %}
            </div>

            <div>
                {{ form.description.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.description(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", rows=3) }}
                {% if form.description.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.description.errors[0] }}</p>
                {% endif %}
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div>
                    {{ form.price.label(class="block text-gray-700 font-semibold mb-2") }}
                    {{ form.price(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", step="0.01") }}
                    {% if form.price.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.price.errors[0] }}</p>
                    {% endif %}
                </div>

                <div>
                    {{ form.quantity.label(class="block text-gray-700 font-semibold mb-2") }}
                    {{ form.quantity(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
                    {% if form.quantity.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.quantity.errors[0] }}</p>
                    {% endif %}
                </div>
            </div>

            <div>
                {{ form.image_url.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.image_url(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
                {% if form.image_url.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.image_url.errors[0] }}</p>
                {% endif %}
            </div>

            <div class="flex gap-4">
                {{ form.submit(class="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 cursor-pointer") }}
                <a href="{{ url_for('wishlist.my_list') }}" class="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 text-center">
                    Cancel
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
''',

    'wishlist/view_list.html': '''{% extends "base.html" %}

{% block title %}{{ user.name }}'s Wishlist{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">{{ user.name }}'s Wishlist</h1>

    {% if items %}
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for item in items %}
                <div class="bg-white rounded-lg shadow-lg overflow-hidden {% if item.is_fully_purchased %}purchased{% endif %}">
                    {% if item.image_url %}
                        <img src="{{ item.image_url }}" alt="{{ item.name }}" class="w-full h-48 object-cover">
                    {% else %}
                        <div class="w-full h-48 bg-gray-200 flex items-center justify-center text-6xl">🎁</div>
                    {% endif %}

                    <div class="p-4">
                        <h3 class="text-xl font-bold mb-2">{{ item.name }}</h3>
                        {% if item.description %}
                            <p class="text-gray-600 text-sm mb-3">{{ item.description[:100] }}{% if item.description|length > 100 %}...{% endif %}</p>
                        {% endif %}

                        <div class="flex justify-between items-center mb-3">
                            {% if item.price %}
                                <span class="text-lg font-semibold text-green-600">${{ "%.2f"|format(item.price) }}</span>
                            {% else %}
                                <span class="text-gray-400">No price</span>
                            {% endif %}
                            <span class="text-sm text-gray-600">Qty: {{ item.quantity }}</span>
                        </div>

                        {% if item.is_fully_purchased %}
                            <div class="bg-green-100 text-green-800 px-3 py-2 rounded text-center mb-3">
                                ✓ Fully Purchased
                            </div>
                        {% elif item.total_purchased > 0 %}
                            <div class="bg-yellow-100 text-yellow-800 px-3 py-2 rounded text-center mb-3">
                                {{ item.total_purchased }}/{{ item.quantity }} Purchased
                            </div>
                        {% endif %}

                        <div class="flex gap-2">
                            {% if item.url %}
                                <a href="{{ item.url }}" target="_blank" class="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-center text-sm hover:bg-blue-700">
                                    View Product
                                </a>
                            {% endif %}
                            {% if not item.is_fully_purchased %}
                                <a href="{{ url_for('wishlist.purchase_item', item_id=item.id) }}" class="flex-1 bg-green-600 text-white px-3 py-2 rounded text-center text-sm hover:bg-green-700">
                                    Mark Purchased
                                </a>
                            {% endif %}
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="bg-white rounded-lg shadow p-12 text-center">
            <div class="text-6xl mb-4">📝</div>
            <h2 class="text-2xl font-bold mb-4">No items on this wishlist yet</h2>
        </div>
    {% endif %}

    <div class="mt-8">
        <a href="{{ url_for('wishlist.all_users') }}" class="text-red-600 hover:underline">← Back to All Users</a>
    </div>
</div>
{% endblock %}
''',

    'wishlist/all_users.html': '''{% extends "base.html" %}

{% block title %}Browse Wishlists{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Browse Wishlists</h1>

    {% if users %}
        <div class="bg-white rounded-lg shadow-lg overflow-hidden">
            <div class="divide-y">
                {% for user in users %}
                    <a href="{{ url_for('wishlist.view_user_list', user_id=user.id) }}" class="block p-6 hover:bg-gray-50 transition">
                        <div class="flex justify-between items-center">
                            <div>
                                <h3 class="text-xl font-bold text-gray-800">{{ user.name }}</h3>
                                <p class="text-gray-600 text-sm">{{ user.email }}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-2xl font-bold text-red-600">{{ user.wishlist_items.count() }}</p>
                                <p class="text-sm text-gray-600">items</p>
                            </div>
                        </div>
                    </a>
                {% endfor %}
            </div>
        </div>
    {% else %}
        <div class="bg-white rounded-lg shadow p-12 text-center">
            <div class="text-6xl mb-4">👥</div>
            <h2 class="text-2xl font-bold mb-4">No other users yet</h2>
            <p class="text-gray-600">Invite family and friends to create accounts!</p>
        </div>
    {% endif %}
</div>
{% endblock %}
''',

    'wishlist/purchase_item.html': '''{% extends "base.html" %}

{% block title %}Purchase Item{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Mark as Purchased</h1>

    <div class="bg-white rounded-lg shadow-lg p-8 mb-6">
        <div class="flex gap-6 mb-6">
            {% if item.image_url %}
                <img src="{{ item.image_url }}" alt="{{ item.name }}" class="w-32 h-32 object-cover rounded">
            {% else %}
                <div class="w-32 h-32 bg-gray-200 flex items-center justify-center text-4xl rounded">🎁</div>
            {% endif %}

            <div>
                <h2 class="text-2xl font-bold mb-2">{{ item.name }}</h2>
                {% if item.price %}
                    <p class="text-xl text-green-600 font-semibold mb-2">${{ "%.2f"|format(item.price) }}</p>
                {% endif %}
                <p class="text-gray-600">Wanted: {{ item.quantity }}</p>
                <p class="text-gray-600">Already purchased: {{ item.total_purchased }}</p>
                <p class="text-gray-600 font-semibold">Remaining: {{ remaining }}</p>
            </div>
        </div>

        <div class="bg-blue-50 p-4 rounded mb-6">
            <p class="text-sm text-gray-700">
                <strong>Note:</strong> {{ item.user.name }} will be able to see that {{ remaining }} of this item has been purchased, but they won't know who purchased it. This keeps the surprise!
            </p>
        </div>

        <form method="POST" class="space-y-4">
            {{ form.hidden_tag() }}

            <div>
                {{ form.quantity.label(class="block text-gray-700 font-semibold mb-2") }}
                {{ form.quantity(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", max=remaining) }}
                <p class="text-sm text-gray-600 mt-1">Maximum: {{ remaining }}</p>
                {% if form.quantity.errors %}
                    <p class="text-red-600 text-sm mt-1">{{ form.quantity.errors[0] }}</p>
                {% endif %}
            </div>

            <div class="flex gap-4">
                {{ form.submit(class="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 cursor-pointer") }}
                <a href="{{ url_for('wishlist.view_user_list', user_id=item.user_id) }}" class="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 text-center">
                    Cancel
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
''',
}

# Create templates
for template_path, content in TEMPLATES.items():
    full_path = os.path.join(TEMPLATES_DIR, template_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Created: {full_path}")

print(f"\n✓ Created {len(TEMPLATES)} wishlist template files")
