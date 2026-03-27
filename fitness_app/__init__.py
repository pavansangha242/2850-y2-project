import os
from flask import Flask
from fitness_app.extentions import db
from fitness_app.models import (
    User, TrainingPlan, PlannedWorkout, TrainingClient,
    ExerciseType, Activity, Competition, CompetitionResult
)
from datetime import date, timedelta


def create_app():
    app = Flask(__name__)

    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fitness_app.db')
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

    # ---- Exercise Types ----
    running = ExerciseType(name='Running', description='Outdoor or treadmill running')
    cycling = ExerciseType(name='Cycling', description='Road or stationary cycling')
    swimming = ExerciseType(name='Swimming', description='Pool or open-water swimming')
    walking = ExerciseType(name='Walking', description='Casual or brisk walking')
    strength = ExerciseType(name='Strength Training', description='Weight and resistance training')

    db.session.add_all([running, cycling, swimming, walking, strength])
    db.session.flush()

    # ---- Users ----
    admin = User(first_name='Michael', last_name='Adams', email='michael@fittrack.com',
                 username='michael_admin', role='administrator')
    admin.set_password('admin123')

    trainer1 = User(first_name='Amanda', last_name='Clark', email='amanda@fittrack.com',
                    username='amandaclark', role='pt')
    trainer1.set_password('password123')

    trainer2 = User(first_name='Mark', last_name='Wilson', email='mark@fittrack.com',
                    username='markwilson', role='pt')
    trainer2.set_password('password123')

    user1 = User(first_name='John', last_name='Doe', email='johndoe@gmail.com',
                 username='johndoe', role='customer')
    user1.set_password('password123')

    user2 = User(first_name='Maya', last_name='Ahmed', email='mayaahmad@gmail.com',
                 username='mayaahmed', role='customer')
    user2.set_password('password123')

    current_user = User(first_name='Alex', last_name='Morgan', email='alex@fittrack.com',
                        username='alex', role='customer')
    current_user.set_password('password123')

    db.session.add_all([admin, trainer1, trainer2, user1, user2, current_user])
    db.session.flush()

    # ---- Training Clients (PT ↔ Customer links) ----
    tc1 = TrainingClient(trainer_id=trainer1.user_id, client_id=current_user.user_id, active=True)
    tc2 = TrainingClient(trainer_id=trainer2.user_id, client_id=user1.user_id, active=True)
    db.session.add_all([tc1, tc2])

    # ---- Training Plans ----
    today = date.today()
    plan1 = TrainingPlan(user_id=current_user.user_id, name='Spring Fitness Plan',
                         start_date=today, end_date=today + timedelta(weeks=8))
    db.session.add(plan1)
    db.session.flush()

    # ---- Planned Workouts ----
    pw1 = PlannedWorkout(plan_id=plan1.plan_id, exercise_type_id=running.exercise_type_id,
                         planned_date=today + timedelta(days=1), target_duration=30, target_distance=5.0)
    pw2 = PlannedWorkout(plan_id=plan1.plan_id, exercise_type_id=cycling.exercise_type_id,
                         planned_date=today + timedelta(days=3), target_duration=45, target_distance=15.0)
    pw3 = PlannedWorkout(plan_id=plan1.plan_id, exercise_type_id=strength.exercise_type_id,
                         planned_date=today + timedelta(days=5), target_duration=60, target_distance=0.0)
    db.session.add_all([pw1, pw2, pw3])

    # ---- Activities (logged workouts) ----
    act1 = Activity(user_id=current_user.user_id, exercise_type_id=walking.exercise_type_id,
                    date=today, duration_minutes=60, distance_km=4.5, calories=220,
                    notes='Morning walk in the park')
    act2 = Activity(user_id=current_user.user_id, exercise_type_id=running.exercise_type_id,
                    date=today, duration_minutes=30, distance_km=5.0, calories=350,
                    notes='Interval training')
    db.session.add_all([act1, act2])

    # ---- Competitions ----
    comp1 = Competition(name='City Marathon', location='City Centre',
                        date=date(2026, 4, 10), distance=42.195)
    comp2 = Competition(name='Spring Cycling Race', location='Countryside Road',
                        date=date(2026, 5, 3), distance=80.0)
    comp3 = Competition(name='Open Water Swim', location='Lake Park',
                        date=date(2026, 6, 12), distance=3.0)
    db.session.add_all([comp1, comp2, comp3])
    db.session.flush()

    # ---- Competition Results ----
    res1 = CompetitionResult(user_id=user1.user_id, competition_id=comp1.competition_id,
                             finish_time='3:45:12', position=42, personal_best=True)
    db.session.add(res1)

    db.session.commit()
