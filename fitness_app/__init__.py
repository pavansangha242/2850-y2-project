import os
from datetime import date, datetime, timedelta

from flask import Flask

from fitness_app.extensions import db
from fitness_app.models import (
    Activity,
    ChatMessage,
    Competition,
    CompetitionResult,
    ExerciseType,
    PlannedWorkout,
    TrainerProfile,
    TrainingClient,
    TrainingPlan,
    User,
)


# set up the flask app
def create_app():
    app = Flask(__name__)

    # config stuff
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        basedir, "..", "fitness_app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # start extensions
    db.init_app(app)

    # bring in all the blueprints
    from fitness_app.routes.admin import admin_bp

    # register all the blueprints
    from fitness_app.routes.auth import auth
    from fitness_app.routes.cycling import cycling_bp
    from fitness_app.routes.events import events_bp
    from fitness_app.routes.gym import gym_bp
    from fitness_app.routes.history import history
    from fitness_app.routes.home import home_bp
    from fitness_app.routes.leaderboard import leaderboard_bp
    from fitness_app.routes.messages import messages_bp
    from fitness_app.routes.progress import progress
    from fitness_app.routes.running import running_bp
    from fitness_app.routes.sport_stats import sport_stats
    from fitness_app.routes.strava import strava_bp
    from fitness_app.routes.swimming import swimming_bp
    from fitness_app.routes.trainers import trainers
    from fitness_app.routes.walking import walking_bp

    # register all
    app.register_blueprint(home_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(swimming_bp)
    app.register_blueprint(cycling_bp)
    app.register_blueprint(running_bp)
    app.register_blueprint(walking_bp)
    app.register_blueprint(gym_bp)

    app.register_blueprint(auth)
    app.register_blueprint(progress)
    app.register_blueprint(history)
    app.register_blueprint(sport_stats)
    app.register_blueprint(trainers)
    app.register_blueprint(messages_bp)
    app.register_blueprint(strava_bp)

    # create tables and add sample data
    with app.app_context():
        db.create_all()
        seed_database()

        approved_trainers = User.query.filter_by(role="pt", approved=True).all()

        for trainer in approved_trainers:
            profile = TrainerProfile.query.filter_by(user_id=trainer.user_id).first()

            if not profile:
                profile = TrainerProfile(
                    user_id=trainer.user_id,
                    specialty="Personal Trainer",
                    bio="Certified personal trainer.|||Gym training|||Fitness coaching|||Workout plans",
                    average_rating=0,
                    total_reviews=0,
                )
                db.session.add(profile)

        db.session.commit()

    return app


def seed_database():
    """Insert sample data if the database is empty."""
    if User.query.first():
        return

    # ---- Exercise Types ----
    swimming = ExerciseType(name="Swimming", description="Pool or open water swimming")
    cycling = ExerciseType(name="Cycling", description="Road or stationary cycling")
    running = ExerciseType(name="Running", description="Outdoor or treadmill running")
    walking = ExerciseType(name="Walking", description="Casual or brisk walking")
    strength = ExerciseType(
        name="Strength Training", description="Gym and weight training"
    )
    db.session.add_all([swimming, cycling, running, walking, strength])
    db.session.flush()

    # ---- Users ----
    admin = User(
        first_name="Michael",
        last_name="Brown",
        email="michael@Motivara.com",
        username="michaelbrown",
        role="administrator",
    )
    admin.set_password("password123")

    db.session.add(admin)
    db.session.commit()
