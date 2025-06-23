from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, create_admin, User

# -------------------------- #
#       Flask Setup          #
# -------------------------- #
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key'

db.init_app(app)

# -------------------------- #
#         Routes             #
# -------------------------- #

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['mail']
        username = request.form['user_name']
        password = request.form['pwd']  # Plain text
        vehicle_number = request.form.get('vehicle_number') or None
        pin_code = request.form.get('pin_code') or None

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already exists.", "danger")
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            email=email,
            password=password,
            role='user',
            vehicle_number=vehicle_number,
            pin_code=pin_code
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['user_name']  # Can be username or email
        password = request.form['pwd']

        # Allow login by username OR email
        user = User.query.filter((User.username == login_input) | (User.email == login_input)).first()

        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash("Login successful!", "success")

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid credentials. Try again.", "danger")

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')


# -------------------------- #
#   Create Tables + Admin    #
# -------------------------- #
with app.app_context():
    db.create_all()
    create_admin(app)

# -------------------------- #
#         Run App            #
# -------------------------- #
if __name__ == '__main__':
    app.run(debug=True)
