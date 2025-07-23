from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from flask import jsonify
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
import json
from datetime import datetime, timedelta

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'beautysalon-secretkey-2025'  # Make sure this is set
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///salon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'customer' or 'salon_owner'
    profile_picture = db.Column(db.String(200), default='default_profile.jpg')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class Salon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    opening_time = db.Column(db.String(50))
    closing_time = db.Column(db.String(50))
    weekly_closing = db.Column(db.String(50))  # Day of week when salon is closed
    images = db.relationship('SalonImage', backref='salon', lazy=True, cascade="all, delete-orphan")
    services = db.relationship('Service', backref='salon', lazy=True, cascade="all, delete-orphan")
    employees = db.relationship('Employee', backref='salon', lazy=True, cascade="all, delete-orphan")
    
class SalonImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    image_path = db.Column(db.String(200), nullable=False)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # duration in minutes

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    image = db.Column(db.String(200), default='default_employee.jpg')

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New fields for payment feature
    has_paid_deposit = db.Column(db.Boolean, default=False)
    deposit_amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), nullable=True)
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, pending, completed
    discounted_price = db.Column(db.Float, default=0.0)
    transaction_id = db.Column(db.String(100), nullable=True)

    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id])
    salon = db.relationship('Salon', foreign_keys=[salon_id])
    service = db.relationship('Service', foreign_keys=[service_id])

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    salon_id = db.Column(db.Integer, db.ForeignKey('salon.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id])
    salon = db.relationship('Salon', foreign_keys=[salon_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    appointment = db.relationship('Appointment', foreign_keys=[appointment_id])

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50))  # appointment, message, system
    related_id = db.Column(db.Integer)  # ID of related entity (appointment, message)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def escapejs_filter(value):
    return Markup(json.dumps(value))

app.jinja_env.filters['escapejs'] = escapejs_filter

def save_image(file):
    if file:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return f"uploads/{unique_filename}"
    return None

def create_notification(user_id, content, notification_type, related_id=None):
    notification = Notification(
        user_id=user_id,
        content=content,
        type=notification_type,
        related_id=related_id
    )
    db.session.add(notification)
    db.session.commit()


def get_date_slots(salon_id):
    slots = TimeSlot.query.filter_by(
        salon_id=salon_id,
        is_available=True
    ).filter(
        TimeSlot.date >= datetime.now().date()
    ).order_by(
        TimeSlot.date,
        TimeSlot.start_time
    ).all()

    date_slots = {}
    for slot in slots:
        date_str = slot.date.strftime('%Y-%m-%d')
        time_entry = {
            'time': slot.start_time.strftime('%H:%M'),
            'end': slot.end_time.strftime('%H:%M')  # Changed from 'end_time' to 'end'
        }
        
        if date_str not in date_slots:
            date_slots[date_str] = {
                'date_str': date_str,
                'day_name': slot.date.strftime('%A'),
                'times': []
            }
        date_slots[date_str]['times'].append(time_entry)
    
    return list(date_slots.values())

# Routes
@app.route('/')
def index():
    # Get random salons (0-3)
    salon_count = Salon.query.count()
    featured_count = min(6, salon_count)
    featured_salons = Salon.query.order_by(db.func.random()).limit(featured_count).all()
    
    return render_template('index.html', featured_salons=featured_salons)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Redirect based on role
            if user.role == 'customer':
                return redirect(url_for('customer_dashboard'))
            else:
                return redirect(url_for('salon_dashboard'))
        else:
            flash('Invalid email or password.')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.')
            return redirect(url_for('login'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password, role=role)
        
        db.session.add(new_user)
        db.session.commit()
        
        # If salon owner, create a salon record
        if role == 'salon_owner':
            new_salon = Salon(
                owner_id=new_user.id,
                name=f"{name}'s Salon",
                location="Please update your location",
                description="Please add a description of your salon"
            )
            db.session.add(new_salon)
            db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Get all appointments ordered by date (newest first) and time (newest first)
    all_appointments = Appointment.query.filter_by(
        customer_id=current_user.id
    ).order_by(
        Appointment.date.desc(),
        Appointment.time.desc()
    ).all()
    
    # Split into past and upcoming
    past_appointments = [a for a in all_appointments if a.date < datetime.now().date()]
    upcoming_appointments = [a for a in all_appointments if a.date >= datetime.now().date()]
    
    # Get notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(
        Notification.timestamp.desc()
    ).all()
    
    return render_template('customer_dashboard.html', 
                         past_appointments=past_appointments, 
                         upcoming_appointments=upcoming_appointments,
                         notifications=notifications)

@app.route('/salon/dashboard')
@login_required
def salon_dashboard():
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Get salon info
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    if not salon:
        flash('Salon information not found.')
        return redirect(url_for('index'))
    
    # Get appointments for the salon
    pending_appointments = Appointment.query.filter_by(salon_id=salon.id, status='pending').all()
    confirmed_appointments = Appointment.query.filter_by(salon_id=salon.id, status='confirmed').all()
    
    # Get salon notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.timestamp.desc()).all()
    
    # Calculate earnings
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    completed_appointments = Appointment.query.filter_by(
        salon_id=salon.id, 
        status='completed'
    ).all()
    
    current_month_earnings = sum([
        appt.service.price for appt in completed_appointments 
        if appt.date.month == current_month and appt.date.year == current_year
    ])
    
    # Group by month for history
    earnings_history = {}
    for appt in completed_appointments:
        month_key = f"{appt.date.year}-{appt.date.month}"
        if month_key not in earnings_history:
            earnings_history[month_key] = 0
        earnings_history[month_key] += appt.service.price
    
    return render_template('salon_dashboard.html',
                          salon=salon,
                          pending_appointments=pending_appointments,
                          confirmed_appointments=confirmed_appointments,
                          notifications=notifications,
                          current_month_earnings=current_month_earnings,
                          earnings_history=earnings_history)

@app.route('/salon/profile', methods=['GET', 'POST'])
@login_required
def salon_profile():
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    if request.method == 'POST':
        salon.name = request.form.get('salon_name')
        salon.description = request.form.get('description')
        salon.location = request.form.get('location')
        salon.phone = request.form.get('phone')
        salon.opening_time = request.form.get('opening_time')
        salon.closing_time = request.form.get('closing_time')
        salon.weekly_closing = request.form.get('weekly_closing')
        
        # Handle salon images
        if 'salon_images' in request.files:
            files = request.files.getlist('salon_images')
            for file in files:
                if file and file.filename != '':
                    image_path = save_image(file)
                    if image_path:
                        new_image = SalonImage(salon_id=salon.id, image_path=image_path)
                        db.session.add(new_image)
        
        db.session.commit()
        flash('Salon information updated successfully!')
        return redirect(url_for('salon_dashboard'))
    
    return render_template('salon_profile.html', salon=salon)

@app.route('/salon/services', methods=['GET', 'POST'])
@login_required
def salon_services():
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        duration = int(request.form.get('duration'))
        
        new_service = Service(
            salon_id=salon.id,
            name=name,
            description=description,
            price=price,
            duration=duration
        )
        
        db.session.add(new_service)
        db.session.commit()
        flash('Service added successfully!')
        return redirect(url_for('salon_services'))
    
    services = Service.query.filter_by(salon_id=salon.id).all()
    return render_template('salon_services.html', salon=salon, services=services)

@app.route('/salon/employees', methods=['GET', 'POST'])
@login_required
def salon_employees():
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        
        new_employee = Employee(
            salon_id=salon.id,
            name=name,
            role=role
        )
        
        if 'image' in request.files and request.files['image']:
            image_path = save_image(request.files['image'])
            if image_path:
                new_employee.image = image_path
        
        db.session.add(new_employee)
        db.session.commit()
        flash('Employee added successfully!')
        return redirect(url_for('salon_employees'))
    
    employees = Employee.query.filter_by(salon_id=salon.id).all()
    return render_template('salon_employees.html', salon=salon, employees=employees)

from datetime import datetime, timedelta  # Add this import at the top of your app.py

@app.route('/salon/timeslots', methods=['GET', 'POST'])
@login_required
def salon_timeslots():
    if current_user.role != 'salon_owner':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    if not salon:
        flash('Salon not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Validate form data
            date_str = request.form.get('date')
            start_str = request.form.get('start_time')
            end_str = request.form.get('end_time')
            
            if not all([date_str, start_str, end_str]):
                flash('All fields are required.', 'error')
                return redirect(url_for('salon_timeslots'))
            
            # Parse and validate datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            
            if date < datetime.now().date():
                flash("Can't add slots for past dates.", 'error')
                return redirect(url_for('salon_timeslots'))
                
            if start_time >= end_time:
                flash('End time must be after start time.', 'error')
                return redirect(url_for('salon_timeslots'))
                
            # Check for overlapping slots
            overlapping = TimeSlot.query.filter_by(
                salon_id=salon.id,
                date=date
            ).filter(
                TimeSlot.start_time < end_time,
                TimeSlot.end_time > start_time
            ).first()
            
            if overlapping:
                flash('This time slot overlaps with an existing one.', 'error')
                return redirect(url_for('salon_timeslots'))
            
            # Create new slot
            new_slot = TimeSlot(
                salon_id=salon.id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                is_available=True
            )
            
            db.session.add(new_slot)
            db.session.commit()
            flash('Time slot added successfully!', 'success')
            
        except ValueError as e:
            db.session.rollback()
            flash('Invalid date or time format.', 'error')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the time slot.', 'error')
            app.logger.error(f"Error in salon_timeslots: {str(e)}")
        
        return redirect(url_for('salon_timeslots'))
    
    # GET request handling
    try:
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)  # Now using the imported timedelta
        
        timeslots = TimeSlot.query.filter_by(
            salon_id=salon.id
        ).filter(
            TimeSlot.date >= start_date,
            TimeSlot.date <= end_date
        ).order_by(
            TimeSlot.date,
            TimeSlot.start_time
        ).all()
        
        return render_template(
            'salon_timeslots.html',
            salon=salon,
            timeslots=timeslots,
            now=datetime.now()  # Pass current time for template
        )
        
    except Exception as e:
        flash('Error loading time slots.', 'error')
        app.logger.error(f"Error loading timeslots: {str(e)}")
        return redirect(url_for('salon_dashboard'))

@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        
        if 'profile_picture' in request.files and request.files['profile_picture']:
            image_path = save_image(request.files['profile_picture'])
            if image_path:
                current_user.profile_picture = image_path
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('customer_dashboard'))
    
    return render_template('customer_profile.html')

@app.route('/find-salons')
def find_salons():
    search_query = request.args.get('search', '').strip()
    service_type = request.args.get('service_type', '').strip()
    
    query = Salon.query
    
    # Apply search filter if search query exists
    if search_query:
        query = query.filter(
            db.or_(
                Salon.name.ilike(f'%{search_query}%'),
                Salon.location.ilike(f'%{search_query}%')
            )
        )
    
    # Apply service type filter if selected
    if service_type:
        query = query.join(Service).filter(Service.name.ilike(f'%{service_type}%'))
    
    salons = query.all()
    
    # Get unique service types for dropdown
    service_types = [s.name for s in Service.query.distinct(Service.name).all()]
    
    # Get minimum price for each salon
    for salon in salons:
        min_price_service = Service.query.filter_by(salon_id=salon.id).order_by(Service.price).first()
        salon.min_price = min_price_service.price if min_price_service else 0
    
    return render_template('find_salons.html', 
                         salons=salons,
                         service_types=service_types)

@app.route('/salon/<int:salon_id>')
def salon_detail(salon_id):
    salon = Salon.query.get_or_404(salon_id)
    services = Service.query.filter_by(salon_id=salon_id).all()
    reviews = Review.query.filter_by(salon_id=salon_id).order_by(Review.date_posted.desc()).all()
    
    # Calculate average rating
    if reviews:
        avg_rating = sum([review.rating for review in reviews]) / len(reviews)
    else:
        avg_rating = 0
    
    return render_template('salon_detail.html', 
                          salon=salon, 
                          services=services, 
                          reviews=reviews, 
                          avg_rating=avg_rating)


@app.route('/salon/<int:salon_id>/book', methods=['GET', 'POST'])
@login_required
def book_appointment(salon_id):
    if current_user.role != 'customer':
        flash('Only customers can book appointments.')
        return redirect(url_for('salon_detail', salon_id=salon_id))
    
    salon = Salon.query.get_or_404(salon_id)
    
    try:
        # Get services with proper error handling
        services = Service.query.filter_by(salon_id=salon_id).all()
        if not services:
            flash('This salon currently has no services available.')
            return redirect(url_for('salon_detail', salon_id=salon_id))
        
        if request.method == 'POST':
            # Validate form data
            service_id = request.form.get('service_id')
            date_str = request.form.get('date')
            time_str = request.form.get('time')
            pay_deposit = request.form.get('pay_deposit') == '1'  # New field
            
            if not all([service_id, date_str, time_str]):
                flash('Please fill all required fields.')
                return redirect(url_for('book_appointment', salon_id=salon_id))
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid date or time format.')
                return redirect(url_for('book_appointment', salon_id=salon_id))
            
            # Check if service exists
            service = Service.query.get(service_id)
            if not service or service.salon_id != salon_id:
                flash('Invalid service selection.')
                return redirect(url_for('book_appointment', salon_id=salon_id))
            
            # Check time slot availability
            timeslot = TimeSlot.query.filter_by(
                salon_id=salon_id,
                date=date,
                is_available=True
            ).filter(
                TimeSlot.start_time <= time,
                TimeSlot.end_time >= time
            ).first()

            if not timeslot:
                flash('Selected time slot is not available.')
                return redirect(url_for('book_appointment', salon_id=salon_id))
            
            # Mark timeslot as booked
            timeslot.is_available = False
            
            # Calculate discounted price if deposit payment is selected
            discounted_price = service.price * 0.95 if pay_deposit else 0
            
            # Create appointment
            new_appointment = Appointment(
                customer_id=current_user.id,
                salon_id=salon_id,
                service_id=service_id,
                date=date,
                time=time,
                status='pending',
                # New fields for payment
                has_paid_deposit=False,  # Will be set to True after payment
                deposit_amount=service.price * 0.03 if pay_deposit else 0,
                discounted_price=discounted_price
            )
            
            db.session.add(new_appointment)
            db.session.commit()  # Need to commit to get appointment ID
            
            # Create notification for salon owner
            create_notification(
                user_id=salon.owner_id,
                content=f"New appointment booking from {current_user.name}",
                notification_type='appointment',
                related_id=new_appointment.id
            )
            
            # Redirect to payment gateway if deposit payment is selected
            if pay_deposit:
                return redirect(url_for('payment_gateway', appointment_id=new_appointment.id))
            else:
                flash('Appointment booked successfully! Waiting for salon confirmation.')
                return redirect(url_for('customer_dashboard'))
        
        # Prepare available time slots in JSON-serializable format
        date_slots = get_date_slots(salon_id)
        if not date_slots:
            flash('No available time slots found for this salon.')
        
        # Prepare services data for template
        services_data = [{
            'id': s.id,
            'name': s.name,
            'price': float(s.price),
            'duration': int(s.duration),
            'description': s.description
        } for s in services]
        
        return render_template(
            "book_appointment.html",
            salon=salon,
            services=services_data,
            date_slots=date_slots,
            now=datetime.now().date()  # Pass current date for form validation
        )
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while processing your request.')
        app.logger.error(f"Error in book_appointment: {str(e)}")
        return redirect(url_for('salon_detail', salon_id=salon_id))


@app.route('/appointment/<int:appointment_id>/confirm', methods=['POST'])
@login_required
def confirm_appointment(appointment_id):
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    salon = Salon.query.get(appointment.salon_id)
    
    if salon.owner_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('salon_dashboard'))
    
    appointment.status = 'confirmed'
    db.session.commit()
    
    # Create notification for customer
    create_notification(
        user_id=appointment.customer_id,
        content=f"Your appointment at {salon.name} has been confirmed!",
        notification_type='appointment',
        related_id=appointment_id
    )
    
    flash('Appointment confirmed successfully!')
    return redirect(url_for('salon_dashboard'))

@app.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check authorization
    if current_user.role == 'customer' and appointment.customer_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('customer_dashboard'))
    
    if current_user.role == 'salon_owner':
        salon = Salon.query.get(appointment.salon_id)
        if salon.owner_id != current_user.id:
            flash('Access denied.')
            return redirect(url_for('salon_dashboard'))

    # Find and update the timeslot
    timeslot = TimeSlot.query.filter_by(
        salon_id=appointment.salon_id,
        date=appointment.date,
        start_time=appointment.time
    ).first()
    
    if timeslot:
        timeslot.is_available = True
    
    appointment.status = 'cancelled'
    db.session.commit()
    
    # Create notification for the other party
    if current_user.role == 'customer':
        # Notify salon owner
        salon = Salon.query.get(appointment.salon_id)
        create_notification(
            user_id=salon.owner_id,
            content=f"Appointment with {current_user.name} has been cancelled by the customer.",
            notification_type='appointment',
            related_id=appointment_id
        )
        flash('Appointment cancelled successfully!')
        return redirect(url_for('customer_dashboard'))
    else:
        # Notify customer
        salon = Salon.query.get(appointment.salon_id)
        create_notification(
            user_id=appointment.customer_id,
            content=f"Your appointment at {salon.name} has been cancelled by the salon.",
            notification_type='appointment',
            related_id=appointment_id
        )
        flash('Appointment cancelled successfully!')
        return redirect(url_for('salon_dashboard'))

@app.route('/appointment/<int:appointment_id>/complete', methods=['POST'])
@login_required
def complete_appointment(appointment_id):
    if current_user.role != 'salon_owner':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    salon = Salon.query.get(appointment.salon_id)
    
    if salon.owner_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('salon_dashboard'))
    
    appointment.status = 'completed'
    db.session.commit()
    
    # Create notification for customer
    create_notification(
        user_id=appointment.customer_id,
        content=f"Your appointment at {salon.name} has been marked as completed. Please leave a review!",
        notification_type='appointment',
        related_id=appointment_id
    )
    
    flash('Appointment marked as completed!')
    return redirect(url_for('salon_dashboard'))

@app.route('/appointment/<int:appointment_id>/book-again', methods=['POST'])
@login_required
def book_again(appointment_id):
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    old_appointment = Appointment.query.get_or_404(appointment_id)
    if old_appointment.customer_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('customer_dashboard'))
    
    # Redirect to booking page with pre-filled data
    return redirect(url_for('book_appointment', 
                           salon_id=old_appointment.salon_id, 
                           service_id=old_appointment.service_id))

@app.route('/salon/<int:salon_id>/review', methods=['POST'])
@login_required
def post_review(salon_id):
    if current_user.role != 'customer':
        flash('Only customers can post reviews.')
        return redirect(url_for('salon_detail', salon_id=salon_id))
    
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    # Check if user has had an appointment with this salon
    has_appointment = Appointment.query.filter_by(
        customer_id=current_user.id,
        salon_id=salon_id,
        status='completed'
    ).first() is not None
    
    if not has_appointment:
        flash('You can only review salons after a completed appointment.')
        return redirect(url_for('salon_detail', salon_id=salon_id))
    
    # Check if user has already reviewed this salon
    existing_review = Review.query.filter_by(
        customer_id=current_user.id,
        salon_id=salon_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.comment = comment
        existing_review.date_posted = datetime.utcnow()
        flash('Review updated successfully!')
    else:
        # Create new review
        new_review = Review(
            customer_id=current_user.id,
            salon_id=salon_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
        flash('Review posted successfully!')
    
    db.session.commit()
    return redirect(url_for('salon_detail', salon_id=salon_id))

@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    receiver_id = int(request.form.get('receiver_id'))
    appointment_id = int(request.form.get('appointment_id')) if request.form.get('appointment_id') else None
    content = request.form.get('content')
    
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        appointment_id=appointment_id,
        content=content
    )
    
    db.session.add(new_message)
    
    # Create notification for receiver
    create_notification(
        user_id=receiver_id,
        content=f"New message from {current_user.name}",
        notification_type='message',
        related_id=new_message.id
    )
    
    db.session.commit()
    flash('Message sent successfully!')
    
    # Redirect based on user role
    if current_user.role == 'customer':
        return redirect(url_for('customer_dashboard'))
    else:
        return redirect(url_for('salon_dashboard'))

@app.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/services/<int:service_id>/update', methods=['POST'])
@login_required
def update_service(service_id):
    if current_user.role != 'salon_owner':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    service = Service.query.get_or_404(service_id)
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    # Verify service belongs to owner's salon
    if not salon or service.salon_id != salon.id:
        flash('Access denied.', 'error')
        return redirect(url_for('salon_services'))
    
    try:
        service.name = request.form.get('name')
        service.description = request.form.get('description')
        service.price = float(request.form.get('price'))
        service.duration = int(request.form.get('duration'))
        
        db.session.commit()
        flash('Service updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating service.', 'error')
        app.logger.error(f"Error updating service: {str(e)}")
    
    return redirect(url_for('salon_services'))

@app.route('/services/<int:service_id>/delete', methods=['POST'])
@login_required
def delete_service(service_id):
    if current_user.role != 'salon_owner':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    service = Service.query.get_or_404(service_id)
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    # Verify service belongs to owner's salon
    if not salon or service.salon_id != salon.id:
        flash('Access denied.', 'error')
        return redirect(url_for('salon_services'))
    
    try:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting service.', 'error')
        app.logger.error(f"Error deleting service: {str(e)}")
    
    return redirect(url_for('salon_services'))


@app.route('/clear-all-notifications', methods=['POST'])
@login_required
def clear_all_notifications():
    if current_user.role != 'salon_owner':
        return jsonify({'success': False})
    
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/salon/timeslots/<int:timeslot_id>/delete', methods=['POST'])
@login_required
def delete_timeslot(timeslot_id):
    if current_user.role != 'salon_owner':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    timeslot = TimeSlot.query.get_or_404(timeslot_id)
    salon = Salon.query.filter_by(owner_id=current_user.id).first()
    
    if not salon or timeslot.salon_id != salon.id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        db.session.delete(timeslot)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting timeslot: {str(e)}")
        return jsonify({'success': False, 'message': 'Error deleting timeslot'})
    

@app.route('/payment/gateway/<int:appointment_id>', methods=['GET'])
@login_required
def payment_gateway(appointment_id):
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.customer_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('customer_dashboard'))
    
    if appointment.has_paid_deposit:
        flash('Deposit already paid for this appointment.')
        return redirect(url_for('customer_dashboard'))
    
    service = Service.query.get(appointment.service_id)
    salon = Salon.query.get(appointment.salon_id)
    
    # Calculate deposit amount (3% of service price)
    deposit_amount = round(service.price * 0.03, 2)
    
    # Calculate discounted price (5% off)
    discounted_price = round(service.price * 0.95, 2)
    
    return render_template(
        'payment_gateway.html',
        appointment=appointment,
        service=service,
        salon=salon,
        deposit_amount=deposit_amount,
        discounted_price=discounted_price
    )

@app.route('/payment/process/<int:appointment_id>', methods=['POST'])
@login_required
def process_payment(appointment_id):
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.customer_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('customer_dashboard'))
    
    if appointment.has_paid_deposit:
        flash('Deposit already paid for this appointment.')
        return redirect(url_for('customer_dashboard'))
    
    service = Service.query.get(appointment.service_id)
    salon = Salon.query.get(appointment.salon_id)
    
    payment_method = request.form.get('payment_method')
    transaction_id = request.form.get('transaction_id')
    
    if not payment_method or not transaction_id:
        flash('Please fill in all payment details.')
        return redirect(url_for('payment_gateway', appointment_id=appointment_id))
    
    # Calculate deposit amount (3% of service price)
    deposit_amount = round(service.price * 0.03, 2)
    
    # Calculate discounted price (5% off)
    discounted_price = round(service.price * 0.95, 2)
    
    # Update appointment with payment information
    appointment.has_paid_deposit = True
    appointment.deposit_amount = deposit_amount
    appointment.payment_method = payment_method
    appointment.payment_status = 'completed'
    appointment.discounted_price = discounted_price
    appointment.transaction_id = transaction_id
    
    db.session.commit()
    
    # Create notification for salon owner
    create_notification(
        user_id=salon.owner_id,
        content=f"Deposit payment received for appointment with {current_user.name}",
        notification_type='payment',
        related_id=appointment.id
    )
    
    flash('Payment successful! You will get 5% discount on your service.')
    return redirect(url_for('customer_dashboard'))



# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

