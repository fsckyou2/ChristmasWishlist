from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, URL, Optional, NumberRange
from app.models import User


class RegistrationForm(FlaskForm):
    """User registration form"""
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Register')

    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class MagicLinkForm(FlaskForm):
    """Magic link login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Login Link')


class PasswordResetRequestForm(FlaskForm):
    """Password reset request form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
    """Password reset form"""
    password = PasswordField('New Password', validators=[DataRequired()])
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Set New Password')


class WishlistItemForm(FlaskForm):
    """Wishlist item form"""
    url = StringField('Product URL', validators=[Optional(), URL()])
    name = StringField('Item Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    price = FloatField('Price', validators=[Optional(), NumberRange(min=0)])
    image_url = StringField('Image URL', validators=[Optional(), URL()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Add to Wishlist')


class PurchaseForm(FlaskForm):
    """Purchase form"""
    quantity = IntegerField('Quantity to Purchase', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Mark as Purchased')
