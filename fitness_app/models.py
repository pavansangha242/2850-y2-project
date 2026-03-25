from datetime import datetime, date
from fitness_app.extentions import db


class User(db.Model):
    """User model — supports regular users, trainers, and admins."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')  # user / admin / trainer
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    activities = db.relationship('Activity', backref='user', lazy=True)
    trainer_application = db.relationship('TrainerApplication', backref='user', uselist=False, lazy=True)

    def __repr__(self):
        return f'<User {self.name}>'


class Event(db.Model):
    """Fitness events like marathons, cycling races, etc."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, default='')
    location = db.Column(db.String(200), default='')

    # Relationships
    registrations = db.relationship('EventRegistration', backref='event', lazy=True)

    @property
    def days_remaining(self):
        delta = self.date - date.today()
        return max(delta.days, 0)

    def __repr__(self):
        return f'<Event {self.name}>'


class EventRegistration(db.Model):
    """Tracks which users registered for which events."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)


class Activity(db.Model):
    """Daily activity logs for a user (steps, calories, etc.)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # running, cycling, swimming, walking
    date = db.Column(db.Date, default=date.today)
    steps = db.Column(db.Integer, default=0)
    calories = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Activity {self.activity_type} by User {self.user_id}>'


class TrainerApplication(db.Model):
    """Trainer applications pending admin approval."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TrainerApplication {self.specialty} — {self.status}>'
