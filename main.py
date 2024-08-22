from flask import Flask, abort, flash, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, distinct
from flask_bootstrap import Bootstrap5
from wtforms.validators import DataRequired
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from functools import wraps
from wtforms import StringField, SubmitField, PasswordField
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafe.db'
db = SQLAlchemy(app)


# db.init_app(app)


class Cafe(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    map_url: Mapped[str] = mapped_column(String(500), nullable=False)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    seats: Mapped[str] = mapped_column(String(250), nullable=False)
    has_toilet: Mapped[bool] = mapped_column(String(250), nullable=False)
    has_wifi: Mapped[bool] = mapped_column(String(250), nullable=False)
    has_sockets: Mapped[bool] = mapped_column(String(250), nullable=False)
    rating: Mapped[bool] = mapped_column(String(250), nullable=False)
    coffee_price: Mapped[str] = mapped_column(String(250), nullable=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))


with app.app_context():
    db.create_all()


class CreateCafeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    map_url = StringField("Map", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    has_sockets = StringField("Has Sockets", validators=[DataRequired()])
    has_toilet = StringField("Has Toilet", validators=[DataRequired()])
    has_wifi = StringField("Has WiFi", validators=[DataRequired()])
    rating = StringField("Rating", validators=[DataRequired()])
    seats = StringField("Seats Number", validators=[DataRequired()])
    coffee_price = StringField(" Cafe Price", validators=[DataRequired()])
    submit = SubmitField("Add New Cafe")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if user email is already present in the database.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/delete/<int:cafe_id>")
@admin_only
def delete_cafe(cafe_id):
    cafe_to_delete = db.get_or_404(Cafe, cafe_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/", methods=["GET", "POST"])
def home():
    result = db.session.execute(db.select(Cafe).order_by(Cafe.id))
    all_cafes = result.scalars().all()
    return render_template("index.html", all_cafes=all_cafes)


@app.route("/cafe/<int:cafe_id>")
def cafe(cafe_id):
    requested_cafe = db.get_or_404(Cafe, cafe_id)
    return render_template("cafe-page.html", cafe=requested_cafe, current_user=current_user)


@app.route("/new-cafe", methods=["GET", "POST"])
def add_new_cafe():
    form = CreateCafeForm()
    if form.validate_on_submit():
        new_cafe = Cafe(
            name=form.name.data,
            map_url=form.map_url.data,
            img_url=form.img_url.data,
            location=form.location.data,
            has_sockets=(form.has_sockets.data),
            has_toilet=(form.has_toilet.data),
            has_wifi=(form.has_wifi.data),
            rating=(form.rating.data),
            seats=form.seats.data,
            coffee_price=form.coffee_price.data
        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("new-cafe.html", form=form)


@app.route("/edit-cafe/<int:cafe_id>", methods=["GET", "POST"])
def edit_cafe(cafe_id):
    cafe_ = db.get_or_404(Cafe, cafe_id)
    edit_form = CreateCafeForm(
        name=cafe_.name,
        map_url=cafe_.map_url,
        img_url=cafe_.img_url,
        location=cafe_.location,
        has_sockets=(cafe_.has_sockets),
        has_toilet=(cafe_.has_toilet),
        has_wifi=(cafe_.has_wifi),
        rating=(cafe_.rating),
        seats=cafe_.seats,
        coffee_price=cafe_.coffee_price
    )
    if edit_form.validate_on_submit():
        cafe_.name = edit_form.name.data
        cafe_.map_url = edit_form.map_url.data
        cafe_.img_url = edit_form.img_url.data
        cafe_.location = edit_form.location.data
        cafe_.has_sockets = edit_form.has_sockets.data
        cafe_.has_toilet = edit_form.has_toilet.data
        cafe_.has_wifi = edit_form.has_wifi.data
        cafe_.rating = edit_form.rating.data
        cafe_.seats = edit_form.seats.data
        cafe_.coffee_price = edit_form.coffee_price.data
        db.session.commit()
        return redirect(url_for('cafe', cafe_id=cafe_.id))
    return render_template("new-cafe.html", form=edit_form, is_edit=True)


@app.route('/search', methods=['GET', 'POST'])
def search_page():
    result = db.session.query(distinct(Cafe.location))
    all_cafes = result.all()
    return render_template("search_by_cities.html", all_cafes=all_cafes)


@app.route('/search/<loc>', methods=['GET', 'POST'])
def search(loc):
    location = loc
    cafes_in_location = db.session.query(Cafe).filter_by(location=location)
    all_cafes = cafes_in_location.all()
    return render_template('search_results.html', all_cafes=all_cafes, loc=location)


@app.route('/about_us', methods=['GET', 'POST'])
def about():
    return render_template('about_us.html')

# MAIL_ADDRESS = Your email
# MAIL_APP_PW = Your email pass
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        # send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)



# def send_email(name, email, phone, message):
#     email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
#     with smtplib.SMTP("smtp.gmail.com") as connection:
#         connection.starttls()
#         connection.login(MAIL_ADDRESS, MAIL_APP_PW)
#         connection.sendmail(MAIL_ADDRESS, MAIL_APP_PW, email_message)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
