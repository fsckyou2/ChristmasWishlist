"""
Script to generate all HTML templates for the Christmas Wishlist application
Run this once to create all necessary template files
"""

import os

# Base directory for templates
TEMPLATES_DIR = 'app/templates'

# Template definitions
TEMPLATES = {
    # Auth templates
    'auth/login.html': '''{% extends "base.html" %}

{% block title %}Login - Christmas Wishlist{% endblock %}

{% block content %}
<div class="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
    <h1 class="text-3xl font-bold mb-6 text-center">Login</h1>

    <form method="POST" class="space-y-4">
        {{ form.hidden_tag() }}

        <div>
            {{ form.email.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.email(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", placeholder="your@email.com") }}
            {% if form.email.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.email.errors[0] }}</p>
            {% endif %}
        </div>

        <div>
            {{ form.password.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.password(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
            {% if form.password.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.password.errors[0] }}</p>
            {% endif %}
        </div>

        {{ form.submit(class="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 cursor-pointer") }}
    </form>

    <div class="mt-6 text-center space-y-2">
        <p><a href="{{ url_for('auth.reset_password_request') }}" class="text-red-600 hover:underline">Forgot Password?</a></p>
        <p><a href="{{ url_for('auth.magic_link') }}" class="text-red-600 hover:underline">Send me a login link</a></p>
        <p class="text-gray-600">Don't have an account? <a href="{{ url_for('auth.register') }}" class="text-red-600 hover:underline">Register</a></p>
    </div>
</div>
{% endblock %}
''',

    'auth/register.html': '''{% extends "base.html" %}

{% block title %}Register - Christmas Wishlist{% endblock %}

{% block content %}
<div class="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
    <h1 class="text-3xl font-bold mb-6 text-center">Create Account</h1>

    <form method="POST" class="space-y-4">
        {{ form.hidden_tag() }}

        <div>
            {{ form.name.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.name(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", placeholder="Your Name") }}
            {% if form.name.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.name.errors[0] }}</p>
            {% endif %}
        </div>

        <div>
            {{ form.email.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.email(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", placeholder="your@email.com") }}
            {% if form.email.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.email.errors[0] }}</p>
            {% endif %}
        </div>

        <div>
            {{ form.password.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.password(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
            {% if form.password.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.password.errors[0] }}</p>
            {% endif %}
        </div>

        <div>
            {{ form.password_confirm.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.password_confirm(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
            {% if form.password_confirm.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.password_confirm.errors[0] }}</p>
            {% endif %}
        </div>

        {{ form.submit(class="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 cursor-pointer") }}
    </form>

    <div class="mt-6 text-center">
        <p class="text-gray-600">Already have an account? <a href="{{ url_for('auth.login') }}" class="text-red-600 hover:underline">Login</a></p>
    </div>
</div>
{% endblock %}
''',

    'auth/magic_link.html': '''{% extends "base.html" %}

{% block title %}Magic Link Login - Christmas Wishlist{% endblock %}

{% block content %}
<div class="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
    <h1 class="text-3xl font-bold mb-6 text-center">Magic Link Login</h1>
    <p class="text-gray-600 mb-6 text-center">Enter your email and we'll send you a secure login link.</p>

    <form method="POST" class="space-y-4">
        {{ form.hidden_tag() }}

        <div>
            {{ form.email.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.email(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", placeholder="your@email.com") }}
            {% if form.email.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.email.errors[0] }}</p>
            {% endif %}
        </div>

        {{ form.submit(class="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 cursor-pointer") }}
    </form>

    <div class="mt-6 text-center">
        <p><a href="{{ url_for('auth.login') }}" class="text-red-600 hover:underline">Back to Login</a></p>
    </div>
</div>
{% endblock %}
''',

    'auth/reset_password_request.html': '''{% extends "base.html" %}

{% block title %}Reset Password - Christmas Wishlist{% endblock %}

{% block content %}
<div class="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
    <h1 class="text-3xl font-bold mb-6 text-center">Reset Password</h1>
    <p class="text-gray-600 mb-6 text-center">Enter your email and we'll send you a password reset link.</p>

    <form method="POST" class="space-y-4">
        {{ form.hidden_tag() }}

        <div>
            {{ form.email.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.email(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600", placeholder="your@email.com") }}
            {% if form.email.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.email.errors[0] }}</p>
            {% endif %}
        </div>

        {{ form.submit(class="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 cursor-pointer") }}
    </form>

    <div class="mt-6 text-center">
        <p><a href="{{ url_for('auth.login') }}" class="text-red-600 hover:underline">Back to Login</a></p>
    </div>
</div>
{% endblock %}
''',

    'auth/reset_password.html': '''{% extends "base.html" %}

{% block title %}Set New Password - Christmas Wishlist{% endblock %}

{% block content %}
<div class="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
    <h1 class="text-3xl font-bold mb-6 text-center">Set New Password</h1>

    <form method="POST" class="space-y-4">
        {{ form.hidden_tag() }}

        <div>
            {{ form.password.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.password(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
            {% if form.password.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.password.errors[0] }}</p>
            {% endif %}
        </div>

        <div>
            {{ form.password_confirm.label(class="block text-gray-700 font-semibold mb-2") }}
            {{ form.password_confirm(class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-600") }}
            {% if form.password_confirm.errors %}
                <p class="text-red-600 text-sm mt-1">{{ form.password_confirm.errors[0] }}</p>
            {% endif %}
        </div>

        {{ form.submit(class="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 cursor-pointer") }}
    </form>
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

print(f"\n✓ Created {len(TEMPLATES)} template files")
print("\nNote: Additional templates for wishlist and admin sections need to be created separately.")
