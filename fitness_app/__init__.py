import os
from flask import Flask
from fitness_app.extentions import db
from fitness_app.models import User, Event, Activity, TrainerApplication, EventRegistration
from datetime import date, datetime


def create_app():
    app = Flask(__name__)

    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fitness.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialise extensions
    db.init_app(app)

    # Register blueprints
    from fitness_app.routes.home import home_bp
    from fitness_app.routes.events import events_bp
    from fitness_app.routes.admin import admin_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(admin_bp)

    # Create database tables and seed data
    with app.app_context():
        db.create_all()
        seed_database()

    return app


def seed_database():
    """Insert sample data if the database is empty."""
    if User.query.first() is not None:
        return  # Already seeded

    # --- Admin user ---
    admin = User(name='Michael Adams', email='michael@fittrack.com', role='admin')

    # --- Regular users ---
    user1 = User(name='John Doe', email='johndoe@gmail.com', role='user')
    user2 = User(name='David Lee', email='davidlee7@gmail.com', role='user')
    user3 = User(name='Maya Ahmed', email='mayaahmad@gmail.com', role='user')
    current_user = User(name='Alex', email='alex@fittrack.com', role='user')

    db.session.add_all([admin, user1, user2, user3, current_user])
    db.session.flush()  # Get IDs

    # --- Events ---
    evt1 = Event(name='City Marathon', date=date(2026, 4, 10),
                 description='Annual city marathon — 42km through the city centre.',
                 location='City Centre')
    evt2 = Event(name='Spring Cycling Race', date=date(2026, 5, 3),
                 description='A scenic cycling race through the countryside.',
                 location='Countryside Road')
    evt3 = Event(name='Open Water Swim', date=date(2026, 6, 12),
                 description='Open water swimming competition at the lake.',
                 location='Lake Park')

    db.session.add_all([evt1, evt2, evt3])

    # --- Activities for the current user ---
    today = date.today()
    act1 = Activity(user_id=current_user.id, activity_type='walking', date=today,
                    steps=8500, calories=220, duration_minutes=60)
    act2 = Activity(user_id=current_user.id, activity_type='running', date=today,
                    steps=0, calories=200, duration_minutes=30)

    db.session.add_all([act1, act2])

    # --- Trainer applications (pending) ---
    trainer1_user = User(name='Amanda Clark', email='amanda@fittrack.com', role='trainer', is_approved=False)
    trainer2_user = User(name='Mark Wilson', email='mark@fittrack.com', role='trainer', is_approved=False)
    trainer3_user = User(name='Laura Green', email='laura@fittrack.com', role='trainer', is_approved=False)

    db.session.add_all([trainer1_user, trainer2_user, trainer3_user])
    db.session.flush()

    app1 = TrainerApplication(user_id=trainer1_user.id, specialty='Running Coach', status='pending')
    app2 = TrainerApplication(user_id=trainer2_user.id, specialty='Strength Trainer', status='pending')
    app3 = TrainerApplication(user_id=trainer3_user.id, specialty='Swimming Instructor', status='pending')

    db.session.add_all([app1, app2, app3])
    db.session.commit()
