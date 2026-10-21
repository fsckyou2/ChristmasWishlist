from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, ValidationError, Optional, NumberRange, Length, EqualTo

from app.models import User
from app.validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_PRICE,
    MAX_QUANTITY,
    clean_http_url,
    clean_image_url,
    wtf_validator,
)


class RegistrationForm(FlaskForm):
    """Passwordless registration form (email + magic link)"""

    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("Register")

    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email already registered.")


class UsernamePasswordRegistrationForm(FlaskForm):
    """Username/password registration form"""

    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
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
    remember_me = BooleanField("Keep me signed in", default=True)
    submit = SubmitField("Login")


class WishlistItemForm(FlaskForm):
    """Wishlist item form"""

    url = StringField("Product URL", validators=[Optional(), wtf_validator(clean_http_url)])
    name = StringField("Item Name", validators=[DataRequired(), Length(max=MAX_NAME_LENGTH)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=MAX_DESCRIPTION_LENGTH)])
    price = FloatField("Price", validators=[Optional(), NumberRange(min=0, max=MAX_PRICE)])
    image_url = StringField("Image URL", validators=[Optional(), wtf_validator(clean_image_url)])
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1, max=MAX_QUANTITY)], default=1)
    submit = SubmitField("Add to Wishlist")


class ClaimForm(FlaskForm):
    """Claim some quantity of an item to give"""

    quantity = IntegerField("Quantity to Claim", validators=[DataRequired(), NumberRange(min=1, max=MAX_QUANTITY)])
    submit = SubmitField("Claim")


class ProxyWishlistForm(FlaskForm):
    """Form for creating a proxy wishlist for someone without an account"""

    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email (Optional)", validators=[Optional(), Email()])
    submit = SubmitField("Create Wishlist")


class AccountSettingsForm(FlaskForm):
    """Form for updating account settings"""

    name = StringField("Display Name", validators=[DataRequired(), Length(max=100)])
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


class InviteForm(FlaskForm):
    """Admin: create a single-use registration invite"""

    note = StringField("Who is it for? (optional)", validators=[Optional(), Length(max=200)])
    days = IntegerField("Expires after (days)", validators=[DataRequired(), NumberRange(min=1, max=365)], default=30)
    submit = SubmitField("Create Invite")


class NewSeasonForm(FlaskForm):
    """Admin: archive last season's gifts and clear them from everyone's lists"""

    season = StringField("Season being closed", validators=[DataRequired(), Length(max=20)])
    confirm = StringField("Type the season again to confirm", validators=[DataRequired(), Length(max=20)])
    notify = BooleanField("Email everyone that lists are open for the new season", default=True)
    submit = SubmitField("Start the new season")

    def validate_confirm(self, field):
        if (field.data or "").strip() != (self.season.data or "").strip():
            raise ValidationError("Type the season exactly as shown to confirm.")
