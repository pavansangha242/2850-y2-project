"""Database models and helper functions for the fitness application."""
from datetime import date, datetime

from flask import session

from fitness_app.extensions import db


# Start of Pavan db model
class User(db.Model):
    """Application user account model."""
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(25), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=True, nullable=False)

    # relationship--Asma
    training_plan = db.relationship(
        "TrainingPlan",
        backref="user",
        uselist=False,
        lazy=True,
        cascade="all, delete-orphan",
    )
    activities = db.relationship(
        "Activity", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    gym_workouts = db.relationship(
        "GymWorkout", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    trainer_profile = db.relationship(
        "TrainerProfile",
        backref="user",
        uselist=False,
        lazy=True,
        cascade="all, delete-orphan",
    )

    ##asma
    clients = db.relationship(
        "TrainingClient",
        foreign_keys="TrainingClient.trainer_id",
        backref="trainer",
        lazy=True,
        cascade="all, delete-orphan",
    )
    trainers = db.relationship(
        "TrainingClient",
        foreign_keys="TrainingClient.client_id",
        backref="client",
        lazy=True,
        cascade="all, delete-orphan",
    )

    strava_access_token = db.Column(db.String(200), nullable=True)
    strava_refresh_token = db.Column(db.String(200), nullable=True)
    strava_token_expires_at = db.Column(
        db.Integer, nullable=True
    )  # Unix timestamp, expires often on Strava
    strava_athlete_id = db.Column(db.Integer, nullable=True)
    last_strava_sync = db.Column(db.DateTime)
    last_strava_activity_time = db.Column(db.DateTime)

    goals = db.relationship(
        "UserGoal", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    privacy = db.relationship(
        "PrivacySettings", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    survey = db.relationship(
        "HealthSurvey", backref="user", uselist=False, cascade="all, delete-orphan"
    )  # link Survey to each user

    def set_password(self, password):
        """Hash and store the user's password."""
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)


class UserGoal(db.Model):
    """Fitness goals and target metrics for a user."""
    __tablename__ = "user_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    step_target = db.Column(db.Integer, default=10000)
    # asma
    time_exercised_target = db.Column(db.Integer, default=0)
    goal_type = db.Column(db.String(50), default="")
    target_date = db.Column(db.Date, nullable=True)
    weekly_exercise_hours = db.Column(db.Integer, default=0)
    workouts_per_week = db.Column(db.Integer, default=0)
    # new fields for Asma's calorie calculations
    age = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    sex = db.Column(db.String(20), nullable=True)


class PrivacySettings(db.Model):
    """User privacy and data sharing preferences."""
    __tablename__ = "privacy_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    share_with_pt = db.Column(db.Boolean, default=False)
    allow_meetings = db.Column(db.Boolean, default=False)


# experimenting with syncing watch for fitness data


class StravaActivity(db.Model):
    """Fitness activity synced from Strava."""
    __tablename__ = "strava_activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)  # Strava's own ID
    name = db.Column(db.String(200))
    activity_type = db.Column(db.String(50))  # Run, Ride, Swim etc
    start_date = db.Column(db.DateTime)
    distance_m = db.Column(db.Float)  # metres
    moving_time_s = db.Column(db.Integer)  # seconds
    calories = db.Column(db.Float, nullable=True)
    avg_heart_rate = db.Column(db.Float, nullable=True)
    max_heart_rate = db.Column(db.Float, nullable=True)
    elevation_gain = db.Column(db.Float, nullable=True)
    avg_speed = db.Column(
        db.Float, nullable=True
    )  # metres per second, can change depending on what we need once implemented
    polyline = db.Column(
        db.Text, nullable=True
    )  # encoded GPS route, see if can add route/map to dashboard
    is_manual = db.Column(db.Boolean, default=False)  # manually recorded workouts

    user = db.relationship(
        "User",
        backref=db.backref(
            "strava_activities", lazy=True, cascade="all, delete-orphan"
        ),
    )


# PTs can view surveys of customers who have share_with_pt enabled.
class HealthSurvey(db.Model):
    """Health and lifestyle survey completed by a user."""
    __tablename__ = "health_surveys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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


class TrainingPlan(db.Model):
    __tablename__ = "training_plans"

    plan_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    swims_per_week = db.Column(db.Integer, default=0)
    weekly_distance = db.Column(db.Float, default=0.0)
    target_pace = db.Column(db.String(50), default="")

    # relationships
    planned_workouts = db.relationship(
        "PlannedWorkout", backref="training_plan", lazy=True
    )

    def __repr__(self):
        return f"<TrainingPlan {self.name}>"


# planed workouts inside a plan
class PlannedWorkout(db.Model):
    __tablename__ = "planned_workouts"

    planned_workout_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("training_plans.plan_id"), nullable=False
    )
    exercise_type_id = db.Column(
        db.Integer, db.ForeignKey("exercise_types.exercise_type_id"), nullable=False
    )
    planned_date = db.Column(db.Date, nullable=False)
    target_duration = db.Column(db.Integer, default=0)  # mins
    target_distance = db.Column(db.Float, default=0.0)  # km

    def __repr__(self):
        return f"<PlannedWorkout {self.planned_workout_id}>"


# list of exer types
class ExerciseType(db.Model):
    __tablename__ = "exercise_types"

    exercise_type_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250), default="")

    # relationships
    activities = db.relationship("Activity", backref="exercise_type", lazy=True)
    planned_workouts = db.relationship(
        "PlannedWorkout", backref="exercise_type", lazy=True
    )

    def __repr__(self):
        return f"<ExerciseType {self.name}>"


def ensure_default_exercise_types():
    default_types = [
        ("Swimming", "Swimming workouts"),
        ("Cycling", "Cycling workouts"),
        ("Running", "Running workouts"),
        ("Walking", "Walking workouts"),
        ("Gym", "Gym workouts"),
    ]

    for name, description in default_types:
        existing = ExerciseType.query.filter_by(name=name).first()

        if not existing:
            exercise = ExerciseType(name=name, description=description)
            db.session.add(exercise)

    db.session.commit()


# logged workouts
class Activity(db.Model):
    __tablename__ = "activities"

    activity_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    exercise_type_id = db.Column(
        db.Integer, db.ForeignKey("exercise_types.exercise_type_id"), nullable=False
    )
    planned_workout_id = db.Column(
        db.Integer, db.ForeignKey("planned_workouts.planned_workout_id"), default=None
    )
    date = db.Column(db.Date, default=date.today)
    duration_minutes = db.Column(db.Integer, default=0)
    distance_km = db.Column(db.Float, default=0.0)
    steps = db.Column(db.Integer, default=0)
    laps = db.Column(db.Integer, default=0)
    stroke_type = db.Column(db.String(50), default="")
    average_speed_kmh = db.Column(db.Float, default=0.0)
    pace_per_km = db.Column(db.Float, default=0.0)
    pace_per_100m = db.Column(db.Float, default=0.0)
    calories = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default="")

    def __repr__(self):
        return f"<Activity {self.activity_id} by User {self.user_id}>"


# gym exers w descriptions
class GymExercise(db.Model):
    __tablename__ = "gym_exercises"

    gym_exercise_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    muscle_group = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default="")
    video_url = db.Column(db.String(250), default="")

    # relationships
    assignments = db.relationship("GymAssignment", backref="exercise", lazy=True)
    workouts = db.relationship("GymWorkout", backref="exercise", lazy=True)

    def __repr__(self):
        return f"<GymExercise {self.name}>"


# exers the trainer has given to client
class GymAssignment(db.Model):
    __tablename__ = "gym_assignments"

    assignment_id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    gym_exercise_id = db.Column(
        db.Integer, db.ForeignKey("gym_exercises.gym_exercise_id"), nullable=False
    )
    sets = db.Column(db.Integer, default=0)
    reps = db.Column(db.Integer, default=0)
    weight_kg = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, default="")
    date_assigned = db.Column(db.Date, default=date.today)

    def __repr__(self):
        return f"<GymAssignment for client={self.client_id}>"


# gym workouts the user has done
class GymWorkout(db.Model):
    __tablename__ = "gym_workouts"

    gym_workout_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    gym_exercise_id = db.Column(
        db.Integer, db.ForeignKey("gym_exercises.gym_exercise_id"), nullable=False
    )
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("gym_assignments.assignment_id"), default=None
    )
    date = db.Column(db.Date, default=date.today)
    sets_completed = db.Column(db.Integer, default=0)
    reps_completed = db.Column(db.Integer, default=0)
    weight_kg = db.Column(db.Float, default=0.0)
    duration_minutes = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default="")

    def __repr__(self):
        return f"<GymWorkout {self.gym_workout_id} by User {self.user_id}>"


# test user id
def get_current_user_id():
    """Return the currently logged-in user's ID."""
    username = session.get("username")

    if not username:
        return None

    user = User.query.filter_by(username=username).first()

    if not user:
        return None

    return user.user_id


def get_user_weight(user_id):
    """Return the stored weight for a user."""
    user = User.query.get(user_id)

    if user and user.goals and user.goals.weight_kg:
        return user.goals.weight_kg

    return None


# find user by id
def get_user_by_id(user_id):
    """Retrieve a user by their ID."""
    return User.query.get(user_id)


# find user by username
def get_user_by_username(username):
    """Retrieve a user by their username."""
    return User.query.filter_by(username=username).first()


def get_exercise_type_id(exercise_name):
    """Return the ID for an exercise type, creating it if needed."""
    exercise = ExerciseType.query.filter_by(name=exercise_name).first()

    if not exercise:
        exercise = ExerciseType(
            name=exercise_name, description=f"{exercise_name} workout"
        )
        db.session.add(exercise)
        db.session.commit()

    return exercise.exercise_type_id


# --------- start if jawaher's part ---------
class TrainerProfile(db.Model):
    __tablename__ = "trainer_profiles"

    trainer_profile_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False
    )
    specialty = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, default="")
    average_rating = db.Column(db.Float, default=0)
    total_reviews = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<TrainerProfile user={self.user_id}>"


class TrainingClient(db.Model):
    __tablename__ = "training_clients"

    trainer_client_id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    start_date = db.Column(db.Date, default=date.today)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<TrainingClient trainer={self.trainer_id} client={self.client_id}>"


class TrainerReview(db.Model):
    __tablename__ = "trainer_reviews"

    review_id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, default="")
    date = db.Column(db.Date, default=date.today)

    def __repr__(self):
        return f"<TrainerReview trainer={self.trainer_id} rating={self.rating}>"


class SessionBooking(db.Model):
    __tablename__ = "session_bookings"

    booking_id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default="pending")
    notes = db.Column(db.Text, default="")

    def __repr__(self):
        return f"<SessionBooking {self.booking_id} status={self.status}>"


class TrainerMessage(db.Model):
    __tablename__ = "trainer_messages"
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


# --------- end of jawaher part ---------

# mohamed db model


class Competition(db.Model):
    """Competitions / events users can participate in."""

    __tablename__ = "competitions"

    competition_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), default="")
    date = db.Column(db.Date, nullable=False)
    distance = db.Column(db.Float, default=0.0)  # km

    # Relationships
    results = db.relationship("CompetitionResult", backref="competition", lazy=True)

    @property
    def days_remaining(self):
        delta = self.date - date.today()
        return max(delta.days, 0)

    def __repr__(self):
        return f"<Competition {self.name}>"


class CompetitionResult(db.Model):
    """Results for a user in a competition (1-to-many from Competition and User)."""

    __tablename__ = "competition_results"

    result_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    competition_id = db.Column(
        db.Integer, db.ForeignKey("competitions.competition_id"), nullable=False
    )
    finish_time = db.Column(db.String(50), default="")
    position = db.Column(db.Integer, default=0)
    personal_best = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<CompetitionResult user={self.user_id} comp={self.competition_id}>"


class ChatMessage(db.Model):
    """Group chat messages linked to a specific competition/event."""

    __tablename__ = "chat_messages"

    message_id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(
        db.Integer, db.ForeignKey("competitions.competition_id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    author = db.relationship(
        "User",
        backref=db.backref("chat_messages", cascade="all, delete-orphan"),
        lazy=True,
    )
    event = db.relationship(
        "Competition",
        backref=db.backref("chat_messages", cascade="all, delete-orphan"),
        lazy=True,
    )

    def __repr__(self):
        return f"<ChatMessage {self.message_id} by User {self.user_id}>"


# end of mohamed db model
