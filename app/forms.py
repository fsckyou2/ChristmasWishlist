from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, URL, Optional, NumberRange
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
    """Passwordless registration form"""

    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email already registered.")


class LoginForm(FlaskForm):
    """Passwordless login form - sends magic link"""

    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Login Link")


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
