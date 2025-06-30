from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, create_admin, User, ParkingLot, ParkingSpot,  Reservation
from datetime import datetime
import os

from collections import defaultdict
import calendar

import matplotlib.pyplot as plt



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key'

db.init_app(app)



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

    
    user_id = session['user_id']

    lots = ParkingLot.query.all()
    enriched_lots = []
    for lot in lots:
        available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        lot.available_spots = available
        lot.occupied_spots = occupied
        enriched_lots.append(lot)

    
    active_reservations = Reservation.query.filter_by(user_id=user_id, leaving_timestamp=None).all()


    
    data = defaultdict(int)
    reservations = Reservation.query.filter_by(user_id=user_id).all()
    for res in reservations:
        if res.spot and res.spot.lot:
            lot_name = res.spot.lot.prime_location_name
            data[lot_name] += 1

    summary_path = None
    if data:
        lots_list = list(data.keys())
        counts = list(data.values())
        plt.figure(figsize=(6, 4))
        plt.bar(lots_list, counts, color='lightblue')
        plt.title("Your Parking Summary")
        plt.xlabel("Parking Lot")
        plt.ylabel("Number of Parkings")
        plt.tight_layout()

        summary_path = f'user_summary_{user_id}.png'
        chart_path = os.path.join('static', summary_path)
        plt.savefig(chart_path)
        plt.close()

    # return render_template(
    #     'user/user_dashboard.html',
    #     lots=enriched_lots,
    #     summary_path=summary_path,
    #     active_reservation=active_reservation
    # )
    return render_template("user/user_dashboard.html", lots=lots, active_reservations=active_reservations)




@app.route('/user/book/<int:lot_id>', methods=['GET', 'POST'])
def book_spot(lot_id):
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    spot = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').first()

    if not spot:
        flash("No available spots in this lot.", "danger")
        return redirect(url_for('user_dashboard'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number']
        reservation = Reservation(
            spot_id=spot.id,
            user_id=user.id,
            parking_timestamp=datetime.utcnow(),
        )
        spot.status = 'O'
        db.session.add(reservation)
        db.session.commit()
        flash(f"Spot {spot.spot_label} booked successfully!", "success")
        return redirect(url_for('user_dashboard'))

    return render_template('user/book_spot.html', lot=lot, spot=spot, username=user.username)



@app.route('/user/release/<int:reservation_id>', methods=['GET', 'POST'])
def release_spot(reservation_id):
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    reservation = Reservation.query.get_or_404(reservation_id)

    duration_display = None
    leaving_timestamp = None
    parking_cost = None

    if request.method == 'POST' and not reservation.leaving_timestamp:
        # Set leaving time and compute cost
        reservation.leaving_timestamp = datetime.utcnow()
        duration = reservation.leaving_timestamp - reservation.parking_timestamp
        total_hours = duration.total_seconds() / 3600

        spot = ParkingSpot.query.get(reservation.spot_id)
        price = spot.lot.price_per_hour
        reservation.parking_cost = round(total_hours * price, 2)

        # Free the spot
        spot.status = 'A'
        db.session.commit()

        # Calculate display values
        leaving_timestamp = reservation.leaving_timestamp.strftime('%Y-%m-%d %H:%M')
        duration_minutes = int(duration.total_seconds() // 60)
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        duration_display = f"{hours} hr {minutes} min"
        parking_cost = f"{reservation.parking_cost:.2f}"

        flash(f"Spot released successfully! Cost: ₹{reservation.parking_cost:.2f}", "success")

    elif reservation.leaving_timestamp:
        # If already released, show info
        duration = reservation.leaving_timestamp - reservation.parking_timestamp
        leaving_timestamp = reservation.leaving_timestamp.strftime('%Y-%m-%d %H:%M')
        duration_minutes = int(duration.total_seconds() // 60)
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        duration_display = f"{hours} hr {minutes} min"
        parking_cost = f"{reservation.parking_cost:.2f}" if reservation.parking_cost else None

    return render_template(
        'user/release.html',
        reservation=reservation,
        leaving_timestamp=leaving_timestamp,
        duration_display=duration_display,
        parking_cost=parking_cost
    )




@app.route('/user/summary')
def user_summary():
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    reservations = Reservation.query.filter_by(user_id=user_id).all()

    # Total stats
    total_bookings = len(reservations)
    total_cost = sum(r.parking_cost or 0 for r in reservations)
    total_time_minutes = sum(
        int((r.leaving_timestamp - r.parking_timestamp).total_seconds() // 60)
        for r in reservations if r.leaving_timestamp
    )
    hours = total_time_minutes // 60
    minutes = total_time_minutes % 60
    total_time = f"{hours} hr {minutes} min"

    # Bookings per location
    location_data = defaultdict(int)
    for r in reservations:
        if r.spot and r.spot.lot:
            location_data[r.spot.lot.prime_location_name] += 1

    visited_places = list(location_data.keys())   # ← ADD THIS LINE

    # Monthly bookings
    monthly_data = defaultdict(int)
    for r in reservations:
        month = r.parking_timestamp.strftime('%b')
        monthly_data[month] += 1

    pie_labels = list(location_data.keys())
    pie_values = list(location_data.values())

    return render_template(
        'user/user_summary.html',
        total_bookings=total_bookings,
        total_time=total_time,
        total_cost=round(total_cost, 2),
        visited_places=visited_places,   # ← PASS IT TO TEMPLATE
        location_data=location_data,
        monthly_data=monthly_data,
        pie_labels=pie_labels,
        pie_values=pie_values
    )




@app.route('/user/history')
def parking_history():
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.parking_timestamp.desc()).all()
    return render_template('user/parking_history.html', reservations=reservations)


@app.route('/user/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if session.get('role') != 'user':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.vehicle_number = request.form['vehicle_number']
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('user_dashboard'))

    return render_template('user/edit_profile.html', user=user)



@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    lots = ParkingLot.query.all()
    return render_template('admin/admin_dashboard.html', lots=lots)


@app.route('/admin/lots')
def manage_lots():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    lots = ParkingLot.query.all()
    return render_template('admin/manage_lots.html', lots=lots)


@app.route('/admin/lots/add', methods=['GET', 'POST'])
def add_lot():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['prime_location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = float(request.form['price_per_hour'])
        max_spots = int(request.form['max_spots'])

        lot = ParkingLot(prime_location_name=name, address=address, pin_code=pin_code,
                         price_per_hour=price, max_spots=max_spots)
        db.session.add(lot)
        db.session.commit()

        for i in range(1, max_spots + 1):
            spot = ParkingSpot(lot_id=lot.id, status='A', spot_label=f"Spot-{i}")
            db.session.add(spot)
        db.session.commit()

        flash("Parking lot added successfully.", "success")
        return redirect(url_for('manage_lots'))

    return render_template('admin/add_lot.html')


# @app.route('/admin/lots/edit/<int:lot_id>', methods=['GET', 'POST'])
# def edit_lot(lot_id):
#     if session.get('role') != 'admin':
#         flash("Unauthorized access!", "warning")
#         return redirect(url_for('login'))
#     lot = ParkingLot.query.get_or_404(lot_id)
#     if request.method == 'POST':
#         lot.prime_location_name = request.form['prime_location_name']
#         lot.address = request.form['address']
#         lot.pin_code = request.form['pin_code']
#         lot.price_per_hour = float(request.form['price_per_hour'])
#         lot.max_spots = request.form['max_spots']
        
#         db.session.commit()
#         flash("Parking lot updated successfully.", "success")
#         return redirect(url_for('manage_lots'))
#     return render_template('admin/edit_lot.html', lot=lot)


@app.route('/admin/lots/edit/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.prime_location_name = request.form['prime_location_name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price_per_hour = float(request.form['price_per_hour'])

        new_max_spots = int(request.form['max_spots'])
        current_spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        current_count = len(current_spots)

        # Update max_spots field
        lot.max_spots = new_max_spots

        # Case 1: Add spots
        if new_max_spots > current_count:
            for i in range(current_count + 1, new_max_spots + 1):
                new_spot = ParkingSpot(
                    lot_id=lot.id,
                    status='A',
                    spot_label=f"Spot {i}"
                )
                db.session.add(new_spot)

        # Case 2: Remove extra spots (only if they are not occupied)
        elif new_max_spots < current_count:
            spots_to_remove = current_spots[new_max_spots:]
            for spot in spots_to_remove:
                if spot.status == 'A':
                    db.session.delete(spot)
                else:
                    flash(f"Cannot delete spot {spot.spot_label} as it is currently occupied.", "danger")

        db.session.commit()
        flash("Parking lot updated successfully.", "success")
        return redirect(url_for('manage_lots'))

    return render_template('admin/edit_lot.html', lot=lot)





@app.route('/admin/lots/delete/<int:lot_id>')
def delete_lot(lot_id):
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    lot = ParkingLot.query.get_or_404(lot_id)
    occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').first()
    if occupied:
        flash("Cannot delete lot with occupied spots.", "danger")
    else:
        db.session.delete(lot)
        db.session.commit()
        flash("Parking lot deleted successfully.", "success")
    return redirect(url_for('manage_lots'))


@app.route('/admin/spots/<int:lot_id>')
def view_spots(lot_id):
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('admin/view_spots.html', lot=lot, spots=spots)


@app.route('/admin/users')
def view_users():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "warning")
        return redirect(url_for('login'))
    users = User.query.filter_by(role='user').all()
    return render_template('admin/view_users.html', users=users)



@app.route('/admin/summary')
def admin_summary():
    from sqlalchemy import extract, func

    total_users = User.query.count()
    total_reservations = Reservation.query.count()
    total_revenue = db.session.query(func.sum(Reservation.parking_cost)).scalar() or 0
    active_reservations = Reservation.query.filter(Reservation.leaving_timestamp.is_(None)).count()
   
    total_lots = ParkingLot.query.count()

    # Monthly Revenue (Bar Chart)
    revenue_data = db.session.query(
        extract('month', Reservation.parking_timestamp).label('month'),
        func.sum(Reservation.parking_cost)
    ).group_by('month').all()

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    months = []
    revenues = []
    for month, revenue in revenue_data:
        months.append(month_names[int(month) - 1])
        revenues.append(float(revenue or 0))

    # Lot-wise Bookings (Pie Chart)
    lot_data = db.session.query(
        ParkingLot.prime_location_name,
        func.count(Reservation.id)
    ).join(ParkingSpot, ParkingLot.id == ParkingSpot.lot_id)\
     .join(Reservation, ParkingSpot.id == Reservation.spot_id)\
     .group_by(ParkingLot.prime_location_name).all()
    lot_labels = [name for name, _ in lot_data]
    lot_counts = [count for _, count in lot_data]

    # Peak Parking Hours (Bar Chart)
    peak_hours_data = db.session.query(
        extract('hour', Reservation.parking_timestamp).label('hour'),
        func.count(Reservation.id)
    ).group_by('hour').order_by('hour').all()
    peak_hours = [f"{int(hour):02d}:00" for hour, _ in peak_hours_data]
    peak_counts = [count for _, count in peak_hours_data]

    return render_template("admin/summary.html",
                           total_users=total_users,
                           total_reservations=total_reservations,
                           total_revenue=total_revenue,
                           active_reservations=active_reservations,
                           total_lots=total_lots,
                           months=months,
                           revenues=revenues,
                           lot_labels=lot_labels,
                           lot_counts=lot_counts,
                           peak_hours=peak_hours,
                           peak_counts=peak_counts)




# @app.route('/admin/search')
# def admin_search():
#     if session.get('role') != 'admin':
#         flash("Unauthorized access!", "danger")
#         return redirect(url_for('login'))

#     query = request.args.get('q', '').lower()
#     lots = ParkingLot.query.filter(
#         ParkingLot.prime_location_name.ilike(f"%{query}%")
#     ).all()

#     users = User.query.filter(
#         (User.username.ilike(f"%{query}%")) |
#         (User.email.ilike(f"%{query}%"))
#     ).all()

#     return render_template('admin/search_results.html', query=query, lots=lots, users=users)

@app.route('/admin/search')
def admin_search():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()

    print("Search Query:", query)  # 🔍 DEBUG: Check what's captured

    lots = []
    users = []

    if query:
        lots = ParkingLot.query.filter(
            ParkingLot.prime_location_name.ilike(f"%{query}%")
        ).all()

        users = User.query.filter(
            (User.username.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%"))
        ).all()

    return render_template('admin/search_results.html', query=query, lots=lots, users=users)



@app.route('/admin/edit_profile', methods=['GET', 'POST'])
def admin_edit_profile():
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    admin_id = session['user_id']
    admin = User.query.get(admin_id)

    if request.method == 'POST':
        admin.username = request.form['username']
        admin.email = request.form['email']
        admin.vehicle_number = request.form.get('vehicle_number', None)
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin/edit_profile.html", admin=admin)





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
