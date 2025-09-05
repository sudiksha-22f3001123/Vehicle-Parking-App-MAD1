# Vehicle Parking App - V1

## Overview
This is a multi-user web application for managing 4-wheeler parking lots, parking spots, and parked vehicles. It supports two roles: **Admin** (superuser) and **User**. The app is built for the Modern Application Development I course.

## Frameworks Used
- **Flask**: Application back-end
- **Jinja2, HTML, CSS, Bootstrap**: Front-end templating and design
- **SQLite**: Database (created programmatically, not manually)

## Features
### Admin
- No registration required; admin is created automatically when the database is initialized
- Create, edit, and delete parking lots
- Set different prices for each parking lot
- Specify the number of parking spots per lot (spots are created automatically)
- View status of all parking spots and parked vehicles
- View all registered users
- View summary charts (lot-wise bookings, monthly revenue, peak hours)
- Delete lots only if all spots are empty

### User
- Register and login
- View available parking lots
- Book a parking spot (automatically allotted)
- Release/vacate a spot
- View parking history and summary charts (total bookings, time, cost, locations visited, monthly stats)
- Edit profile

## Database Structure
- **User**: id, username, email, password, role, vehicle_number, pin_code, etc.
- **ParkingLot**: id, prime_location_name, price_per_hour, address, pin_code, max_spots, etc.
- **ParkingSpot**: id, lot_id (FK), spot_label, status (O/A), etc.
- **Reservation**: id, spot_id (FK), user_id (FK), parking_timestamp, leaving_timestamp, parking_cost, etc.

## How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open your browser and go to `http://127.0.0.1:5000/`

## Notes
- All demos run locally; no external database required
- Database and admin user are created automatically on first run
- No manual database creation (do not use DB Browser for SQLite)
- Front-end design is flexible; you may customize views

---
**Modern Application Development I**

