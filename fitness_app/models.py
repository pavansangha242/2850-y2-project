from datetime import datetime
from fitness_app.extensions import db

# Start of Pavan db model
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(25), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=True, nullable=False)

    strava_access_token = db.Column(db.String(200), nullable=True)
    strava_refresh_token = db.Column(db.String(200), nullable=True)
    strava_token_expires_at = db.Column(db.Integer, nullable=True)  # Unix timestamp, expires often on Strava
    strava_athlete_id = db.Column(db.Integer, nullable=True)
    last_strava_sync = db.Column(db.DateTime)
    last_strava_activity_time = db.Column(db.DateTime)

    goals = db.relationship('UserGoal', backref='user', uselist=False, cascade="all, delete-orphan")
    privacy = db.relationship('PrivacySettings', backref='user', uselist=False, cascade="all, delete-orphan")
    survey = db.relationship('HealthSurvey', backref='user', uselist=False, cascade="all, delete-orphan") # link Survey to each user

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

class StravaActivity(db.Model):
    __tablename__ = 'strava_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey('users.id', ondelete="CASCADE"),nullable=False)
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)  # Strava's own ID
    name = db.Column(db.String(200))
    activity_type = db.Column(db.String(50))   # Run, Ride, Swim etc
    start_date = db.Column(db.DateTime)
    distance_m = db.Column(db.Float)           # metres
    moving_time_s = db.Column(db.Integer)      # seconds
    calories = db.Column(db.Float, nullable=True)
    avg_heart_rate = db.Column(db.Float, nullable=True)
    max_heart_rate = db.Column(db.Float, nullable=True)
    elevation_gain = db.Column(db.Float, nullable=True)
    avg_speed = db.Column(db.Float, nullable=True)   # metres per second, can change depending on what we need once implemented
    polyline = db.Column(db.Text, nullable=True)     # encoded GPS route, see if can add route/map to dashboard
    is_manual = db.Column(db.Boolean, default=False) # manually recorded workouts

    user = db.relationship('User',backref=db.backref('strava_activities',lazy=True,cascade="all, delete-orphan")
)


# PTs can view surveys of customers who have share_with_pt enabled.
class HealthSurvey(db.Model):
    __tablename__ = 'health_surveys'
 
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    # --- Activity ---
    workout_hours_per_day = db.Column(db.Float, nullable=True)       
    workout_days_per_week = db.Column(db.Integer, nullable=True)       
    preferred_workout_type = db.Column(db.String(50), nullable=True)   
    fitness_level = db.Column(db.String(20), nullable=True)            
 
    # --- Habits ---
    sleep_hours = db.Column(db.Float, nullable=True)                   
    water_litres = db.Column(db.Float, nullable=True)                 
    smokes = db.Column(db.Boolean, nullable=True)                      
    alcohol_frequency = db.Column(db.String(30), nullable=True)        
 
    # --- Diet ---
    diet_type = db.Column(db.String(50), nullable=True)                
    meals_per_day = db.Column(db.Integer, nullable=True)               
 
    # --- Health ---
    has_injuries = db.Column(db.Boolean, nullable=True)                
    injury_details = db.Column(db.Text, nullable=True)                
    medical_conditions = db.Column(db.Text, nullable=True)            
 
    # --- Goals ---
    fitness_goal = db.Column(db.String(50), nullable=True)             
    motivation_level = db.Column(db.Integer, nullable=True)           
    additional_notes = db.Column(db.Text, nullable=True) 

# End of Pavan db model   


###asma  part
