from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ---------------------- #
#       User Model       #
# ---------------------- #
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)  # Plain text
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), default='user', nullable=False)  # 'admin' or 'user'
    vehicle_number = db.Column(db.String(20), nullable=True)
    pin_code = db.Column(db.String(6), nullable=True)

    reservations = db.relationship('Reservation', backref='user', lazy=True)

# ---------------------------- #
#     Parking Lot Model        #
# ---------------------------- #
class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(6), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Optional

    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade='all, delete-orphan')

# ---------------------------- #
#     Parking Spot Model       #
# ---------------------------- #
class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # A=Available, O=Occupied
    spot_label = db.Column(db.String(20), nullable=True)

    reservation = db.relationship('Reservation', backref='spot', uselist=False, cascade='all, delete-orphan')

# ---------------------------- #
#     Reservation Model        #
# ---------------------------- #
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)
    note = db.Column(db.Text, nullable=True)

# ---------------------------- #
#    Create Fixed Admin        #
# ---------------------------- #
def create_admin(app):
    with app.app_context():
        db.create_all()
        admin_email = 'admin@gmail.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            new_admin = User(
                username='admin',
                email=admin_email,
                password='admin',  # ✅ Plain text password
                role='admin',
                vehicle_number=None
            )
            db.session.add(new_admin)
            db.session.commit()
            print("✅ Admin created: admin@gmail.com / admin")
        else:
            print("ℹ Admin already exists.")
