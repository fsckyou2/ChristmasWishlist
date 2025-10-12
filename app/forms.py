from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, ValidationError, URL, Optional, NumberRange, Length, EqualTo
from app.models import User


def flexible_url_validator(form, field):
    """Validator that allows full URLs or relative paths (for static files)"""
    if not field.data:
        return  # Allow empty

    # Allow relative paths starting with /
    if field.data.startswith("/"):
        return

    # Otherwise, validate as full URL
    try:
        URL()(form, field)
    except ValidationError:
        raise ValidationError("Must be a valid URL or a relative path starting with /")


class RegistrationForm(FlaskForm):
    """Passwordless registration form (email + magic link)"""

    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email already registered.")


class UsernamePasswordRegistrationForm(FlaskForm):
    """Username/password registration form"""

    name = StringField("Name", validators=[DataRequired()])
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=80, message="Username must be 3-80 characters")]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters")]
    )
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")

    def validate_username(self, field):
        """Check if username already exists"""
        if User.query.filter_by(username=field.data.lower()).first():
            raise ValidationError("Username already taken.")


class LoginForm(FlaskForm):
    """Passwordless login form - sends magic link"""

    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Login Link")


class UsernamePasswordLoginForm(FlaskForm):
    """Username/password login form"""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")


class WishlistItemForm(FlaskForm):
    """Wishlist item form"""

    url = StringField("Product URL", validators=[Optional(), URL()])
    name = StringField("Item Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    price = FloatField("Price", validators=[Optional(), NumberRange(min=0)])
    image_url = StringField("Image URL", validators=[Optional(), flexible_url_validator])
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField("Add to Wishlist")


class PurchaseForm(FlaskForm):
    """Purchase form"""

    quantity = IntegerField("Quantity to Purchase", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Mark as Purchased")


class ProxyWishlistForm(FlaskForm):
    """Form for creating a proxy wishlist for someone without an account"""

    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email (Optional)", validators=[Optional(), Email()])
    submit = SubmitField("Create Wishlist")


class AccountSettingsForm(FlaskForm):
    """Form for updating account settings"""

    name = StringField("Display Name", validators=[DataRequired()])
    email = StringField("Email (Optional)", validators=[Optional(), Email()])
    username = StringField("Username (Optional)", validators=[Optional(), Length(min=3, max=80)])
    submit = SubmitField("Update Account")


class ChangePasswordForm(FlaskForm):
    """Form for changing password"""

    current_password = PasswordField("Current Password", validators=[Optional()])
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters")]
    )
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password")])
    submit = SubmitField("Change Password")
