# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Form untuk registerasi user
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=80)
    ])
    email = StringField("Email", validators=[
        DataRequired(), Email(), Length(max=255)
    ])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(min=6, max=128)
    ])
    password2 = PasswordField("Masukkan ulang password", validators=[
        DataRequired(), EqualTo("password", message="Password harus sama")
    ])
    submit = SubmitField("Register")

# Form untuk login user
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Log in")

# Form untuk lupa password
class ForgotPasswordForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    new_password = PasswordField("Password baru", validators=[DataRequired(), Length(min=6, max=128)])
    new_password2 = PasswordField("Ulangi password", validators=[
        DataRequired(), EqualTo("new_password", message="Password tidak sama")
    ])
    submit = SubmitField("Reset password")
