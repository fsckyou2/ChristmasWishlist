"""
Script to create minimal admin templates
"""

import os

TEMPLATES_DIR = 'app/templates'

TEMPLATES = {
    'admin/dashboard.html': '''{% extends "base.html" %}

{% block title %}Admin Dashboard{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Admin Dashboard</h1>

    <div class="grid md:grid-cols-3 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-lg p-6">
            <h3 class="text-gray-600 text-sm font-semibold mb-2">Total Users</h3>
            <p class="text-4xl font-bold text-blue-600">{{ stats.total_users }}</p>
        </div>
        <div class="bg-white rounded-lg shadow-lg p-6">
            <h3 class="text-gray-600 text-sm font-semibold mb-2">Total Wishlist Items</h3>
            <p class="text-4xl font-bold text-green-600">{{ stats.total_items }}</p>
        </div>
        <div class="bg-white rounded-lg shadow-lg p-6">
            <h3 class="text-gray-600 text-sm font-semibold mb-2">Total Purchases</h3>
            <p class="text-4xl font-bold text-red-600">{{ stats.total_purchases }}</p>
        </div>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-white rounded-lg shadow-lg p-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-2xl font-bold">Quick Links</h2>
            </div>
            <div class="space-y-2">
                <a href="{{ url_for('admin.users') }}" class="block p-3 bg-gray-50 rounded hover:bg-gray-100">
                    👥 Manage Users
                </a>
                <a href="{{ url_for('admin.items') }}" class="block p-3 bg-gray-50 rounded hover:bg-gray-100">
                    📝 View All Items
                </a>
                <a href="{{ url_for('admin.purchases') }}" class="block p-3 bg-gray-50 rounded hover:bg-gray-100">
                    🎁 View All Purchases
                </a>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow-lg p-6">
            <h2 class="text-2xl font-bold mb-4">Recent Users</h2>
            <div class="space-y-2">
                {% for user in recent_users %}
                    <a href="{{ url_for('admin.view_user', user_id=user.id) }}" class="block p-2 hover:bg-gray-50 rounded">
                        <span class="font-semibold">{{ user.name }}</span>
                        <span class="text-sm text-gray-600">- {{ user.email }}</span>
                    </a>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
''',

    'admin/users.html': '''{% extends "base.html" %}

{% block title %}Manage Users{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">Manage Users</h1>

    <div class="bg-white rounded-lg shadow-lg overflow-hidden">
        <table class="w-full">
            <thead class="bg-gray-100">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Name</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Email</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Admin</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                {% for user in users %}
                    <tr class="hover:bg-gray-50">
                        <td class="px-6 py-4 whitespace-nowrap">{{ user.name }}</td>
                        <td class="px-6 py-4 whitespace-nowrap">{{ user.email }}</td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            {% if user.is_admin %}
                                <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">Admin</span>
                            {% endif %}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm">
                            <a href="{{ url_for('admin.view_user', user_id=user.id) }}" class="text-blue-600 hover:underline mr-3">View</a>
                            <a href="{{ url_for('admin.impersonate', user_id=user.id) }}" class="text-purple-600 hover:underline mr-3">Impersonate</a>
                            {% if user.id != current_user.id %}
                                <form method="POST" action="{{ url_for('admin.toggle_admin', user_id=user.id) }}" class="inline">
                                    <button type="submit" class="text-orange-600 hover:underline mr-3">
                                        {% if user.is_admin %}Remove Admin{% else %}Make Admin{% endif %}
                                    </button>
                                </form>
                                <form method="POST" action="{{ url_for('admin.delete_user', user_id=user.id) }}" class="inline">
                                    <button type="submit" onclick="return confirm('Delete this user?')" class="text-red-600 hover:underline">
                                        Delete
                                    </button>
                                </form>
                            {% endif %}
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
''',

    'admin/view_user.html': '''{% extends "base.html" %}

{% block title %}User Details{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
        <h1 class="text-4xl font-bold">User Details</h1>
        <a href="{{ url_for('admin.users') }}" class="text-red-600 hover:underline">← Back to Users</a>
    </div>

    <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h2 class="text-2xl font-bold mb-4">{{ user.name }}</h2>
        <div class="grid md:grid-cols-2 gap-4">
            <div>
                <p class="text-gray-600"><strong>Email:</strong> {{ user.email }}</p>
                <p class="text-gray-600"><strong>Admin:</strong> {% if user.is_admin %}Yes{% else %}No{% endif %}</p>
                <p class="text-gray-600"><strong>Joined:</strong> {{ user.created_at.strftime('%Y-%m-%d') }}</p>
            </div>
            <div>
                <p class="text-gray-600"><strong>Wishlist Items:</strong> {{ wishlist_items|length }}</p>
                <p class="text-gray-600"><strong>Purchases Made:</strong> {{ purchases|length }}</p>
            </div>
        </div>
    </div>

    <div class="bg-white rounded-lg shadow-lg p-6">
        <h3 class="text-xl font-bold mb-4">Wishlist Items</h3>
        {% if wishlist_items %}
            <div class="space-y-2">
                {% for item in wishlist_items %}
                    <div class="p-3 bg-gray-50 rounded">
                        <p class="font-semibold">{{ item.name }}</p>
                        {% if item.price %}<p class="text-sm text-gray-600">${{ "%.2f"|format(item.price) }}</p>{% endif %}
                    </div>
                {% endfor %}
            </div>
        {% else %}
            <p class="text-gray-600">No items</p>
        {% endif %}
    </div>
</div>
{% endblock %}
''',

    'admin/items.html': '''{% extends "base.html" %}

{% block title %}All Items{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">All Wishlist Items</h1>

    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for item in items %}
            <div class="bg-white rounded-lg shadow p-4">
                <h3 class="font-bold text-lg mb-2">{{ item.name }}</h3>
                <p class="text-sm text-gray-600 mb-2">Owner: {{ item.user.name }}</p>
                {% if item.price %}<p class="text-green-600 font-semibold mb-2">${{ "%.2f"|format(item.price) }}</p>{% endif %}
                <form method="POST" action="{{ url_for('admin.delete_item', item_id=item.id) }}">
                    <button type="submit" onclick="return confirm('Delete this item?')" class="text-red-600 hover:underline text-sm">
                        Delete
                    </button>
                </form>
            </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
''',

    'admin/purchases.html': '''{% extends "base.html" %}

{% block title %}All Purchases{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <h1 class="text-4xl font-bold mb-8">All Purchases</h1>

    <div class="bg-white rounded-lg shadow-lg overflow-hidden">
        <table class="w-full">
            <thead class="bg-gray-100">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Item</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Owner</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Purchased By</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Quantity</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Date</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                {% for purchase in purchases %}
                    <tr class="hover:bg-gray-50">
                        <td class="px-6 py-4">{{ purchase.wishlist_item.name }}</td>
                        <td class="px-6 py-4">{{ purchase.wishlist_item.user.name }}</td>
                        <td class="px-6 py-4">{{ purchase.purchased_by.name }}</td>
                        <td class="px-6 py-4">{{ purchase.quantity }}</td>
                        <td class="px-6 py-4">{{ purchase.created_at.strftime('%Y-%m-%d') }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
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

print(f"\n✓ Created {len(TEMPLATES)} admin template files")
print("\nRun all three template scripts:")
print("  python create_templates.py")
print("  python create_wishlist_templates.py")
print("  python create_admin_templates.py")
