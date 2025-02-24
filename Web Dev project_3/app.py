from flask import Flask, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "YourSecretKey"
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class Patient(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="patient")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(9), nullable=False)
    image = db.Column(db.String(300), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    patient = db.relationship('Patient', backref=db.backref('cart', lazy=True))
    book = db.relationship('Book', backref=db.backref('cart', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    patient = db.relationship('Patient', backref=db.backref('orders', lazy=True))
    book = db.relationship('Book', backref=db.backref('orders', lazy=True))

@login_manager.user_loader
def load_patient(user_id):
    return Patient.query.get(int(user_id))

@app.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        patient = Patient.query.filter_by(email=email).first()

        if patient and patient.check_password(password):
            login_user(patient)
            flash("Login successful!", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password!", "danger")
    
    return render_template("login.html")



@app.route('/about_us')
def about_us():
    return render_template('about.html')


@app.route('/bookappointment')
def bookappointment():
    return render_template('bookappointment.html')



@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role != 'doctor':  
        flash("Access denied!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = request.form['price']
        image = request.files['image']

        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        new_book = Book(title=title, author=author, price=price, image=filename, uploaded_by=current_user.id)
        db.session.add(new_book)
        db.session.commit()
        flash("Book added successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_book.html')

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if current_user.role != 'doctor':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))

    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.price = request.form['price']

        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            book.image = filename  # Update book image

        db.session.commit()
        flash("Book updated successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_book.html', book=book)


@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if current_user.role != 'doctor':
        flash("Access denied!", "danger")
        return redirect(url_for('dashboard'))

    book = Book.query.get_or_404(book_id)

    # Delete the book from the database
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully!", "success")
    return redirect(url_for('dashboard'))




@app.route('/update_order/<int:order_id>/<string:status>')
@login_required
def update_order(order_id, status):
    if current_user.role != 'doctor':
        flash("Access denied!", "danger")
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    flash(f"Order {status}!", "success")
    return redirect(url_for('orders'))

@app.route('/track_orders')
@login_required
def track_orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('track_orders.html', orders=orders)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role", "patient")

        if Patient.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for("register"))

        new_patient = Patient(name=name, email=email, role=role)
        new_patient.set_password(password)
        db.session.add(new_patient)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")



@app.route('/add_to_cart/<int:book_id>')
@login_required
def add_to_cart(book_id):
    cart_item = Cart(user_id=current_user.id, book_id=book_id)
    db.session.add(cart_item)
    db.session.commit()
    flash("Book added to cart!", "success")
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:book_id>')
@login_required
def remove_from_cart(book_id):
    cart_item = Cart.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Book removed from cart!", "success")
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.book.price for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/place_order')
@login_required
def place_order():
    if current_user.role == 'doctor':  
        flash("doctors cannot place orders!", "danger")
        return redirect(url_for('index'))

    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('cart'))
    
    for item in cart_items:
        new_order = Order(user_id=current_user.id, book_id=item.book_id, status='Pending')
        db.session.add(new_order)
        db.session.delete(item)  # Remove from cart
    db.session.commit()
    
    flash("Order placed successfully!", "success")
    return redirect(url_for('orders'))


@app.route('/orders')
@login_required
def orders():
    if current_user.role != 'doctor':
        flash("Access denied!", "danger")
        return redirect(url_for('index'))
    orders = Order.query.all()
    return render_template('orders.html', orders=orders)

@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('book_details.html', book=book)

@app.route('/dashboard')
@login_required
def dashboard():
    books = Book.query.all() if current_user.role == 'doctor' else []
    return render_template('dashboard.html', books=books)


@app.route('/get_appointment')
def get_appointment():
    return render_template('doctors.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5600)