from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from fitness_app.extentions import db


class User(db.Model):
    """User model — supports customers, PTs, and administrators."""
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # customer / pt / administrator
    join_date = db.Column(db.Date, default=date.today)

    # Relationships
    training_plan = db.relationship('TrainingPlan', backref='user', uselist=False, lazy=True)
    activities = db.relationship('Activity', backref='user', lazy=True)
    competition_results = db.relationship('CompetitionResult', backref='user', lazy=True)

    # Training Client relationships (as trainer and as client)
    clients = db.relationship('TrainingClient', foreign_keys='TrainingClient.trainer_id', backref='trainer', lazy=True)
    trainers = db.relationship('TrainingClient', foreign_keys='TrainingClient.client_id', backref='client', lazy=True)

    def set_password(self, pw):
        self.password = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password, pw)

    def __repr__(self):
        return f'<User {self.username}>'


class TrainingPlan(db.Model):
    """Training plan — one per user (1-to-1 with User)."""
    __tablename__ = 'training_plans'

    plan_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Relationships
    planned_workouts = db.relationship('PlannedWorkout', backref='training_plan', lazy=True)

    def __repr__(self):
        return f'<TrainingPlan {self.name}>'


class PlannedWorkout(db.Model):
    """Planned workouts inside a training plan (1-to-many from TrainingPlan)."""
    __tablename__ = 'planned_workouts'

    planned_workout_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('training_plans.plan_id'), nullable=False)
    exercise_type_id = db.Column(db.Integer, db.ForeignKey('exercise_types.exercise_type_id'), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    target_duration = db.Column(db.Integer, default=0)       # minutes
    target_distance = db.Column(db.Float, default=0.0)       # km

    def __repr__(self):
        return f'<PlannedWorkout {self.planned_workout_id}>'


class TrainingClient(db.Model):
    """Links a trainer (PT) to a client (1-to-1 with User on each side)."""
    __tablename__ = 'training_clients'

    trainer_client_id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    start_date = db.Column(db.Date, default=date.today)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<TrainingClient trainer={self.trainer_id} client={self.client_id}>'


class ExerciseType(db.Model):
    """Catalogue of exercise types (running, cycling, etc.)."""
    __tablename__ = 'exercise_types'

    exercise_type_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250), default='')

    # Relationships
    activities = db.relationship('Activity', backref='exercise_type', lazy=True)
    planned_workouts = db.relationship('PlannedWorkout', backref='exercise_type', lazy=True)

    def __repr__(self):
        return f'<ExerciseType {self.name}>'


class Activity(db.Model):
    """Logged workouts / activities (1-to-many from User and ExerciseType)."""
    __tablename__ = 'activities'

    activity_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    exercise_type_id = db.Column(db.Integer, db.ForeignKey('exercise_types.exercise_type_id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    duration_minutes = db.Column(db.Integer, default=0)
    distance_km = db.Column(db.Float, default=0.0)
    calories = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default='')

    def __repr__(self):
        return f'<Activity {self.activity_id} by User {self.user_id}>'


class Competition(db.Model):
    """Competitions / events users can participate in."""
    __tablename__ = 'competitions'

    competition_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), default='')
    date = db.Column(db.Date, nullable=False)
    distance = db.Column(db.Float, default=0.0)  # km

    # Relationships
    results = db.relationship('CompetitionResult', backref='competition', lazy=True)

    @property
    def days_remaining(self):
        delta = self.date - date.today()
        return max(delta.days, 0)

    def __repr__(self):
        return f'<Competition {self.name}>'


class CompetitionResult(db.Model):
    """Results for a user in a competition (1-to-many from Competition and User)."""
    __tablename__ = 'competition_results'

    result_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.competition_id'), nullable=False)
    finish_time = db.Column(db.String(50), default='')
    position = db.Column(db.Integer, default=0)
    personal_best = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<CompetitionResult user={self.user_id} comp={self.competition_id}>'
