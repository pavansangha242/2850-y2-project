from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(25), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=True, nullable=False)

    goals = db.relationship('UserGoal', backref='user', uselist=False, cascade="all, delete-orphan")
    privacy = db.relationship('PrivacySettings', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class UserGoal(db.Model):
    __tablename__ = 'user_goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    step_target = db.Column(db.Integer, default=10000)
    weekly_exercise_hours = db.Column(db.Integer, default=0)
    workouts_per_week = db.Column(db.Integer, default=0)
    #new fields for Asma's calorie calculations
    age = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    sex = db.Column(db.String(20), nullable=True)


class PrivacySettings(db.Model):
    __tablename__ = 'privacy_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_with_pt = db.Column(db.Boolean, default=False)
    allow_meetings = db.Column(db.Boolean, default=False)

# experimenting with syncing watch for fitness data
