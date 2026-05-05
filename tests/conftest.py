import os
import sys
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from run import app as flask_app
from fitness_app.extensions import db
from fitness_app.models import User, ExerciseType, TrainerProfile, GymExercise


@pytest.fixture
def app():
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        customer = User(
            username="test_customer",
            first_name="Test",
            last_name="Customer",
            email="customer@test.com",
            role="customer",
            password_hash="test",
            approved=True,
        )

        trainer = User(
            username="test_trainer",
            first_name="Test",
            last_name="Trainer",
            email="trainer@test.com",
            role="pt",
            password_hash="test",
            approved=True,
        )

        admin = User(
            username="test_admin",
            first_name="Test",
            last_name="Admin",
            email="admin@test.com",
            role="administrator",
            password_hash="test",
            approved=True,
        )

        db.session.add_all([customer, trainer, admin])
        db.session.commit()

        db.session.add_all([
            ExerciseType(name="Swimming", description="Swimming workouts"),
            ExerciseType(name="Running", description="Running workouts"),
            ExerciseType(name="Cycling", description="Cycling workouts"),
            ExerciseType(name="Walking", description="Walking workouts"),
            ExerciseType(name="Gym", description="Gym workouts"),
        ])
        db.session.commit()

        db.session.add_all([
            GymExercise(
                name="Squat",
                muscle_group="Legs",
                description="Lower body exercise",
                video_url=""
            ),
            GymExercise(
                name="Bench Press",
                muscle_group="Chest",
                description="Upper body exercise",
                video_url=""
            ),
        ])
        db.session.commit()

        trainer_profile = TrainerProfile(
            user_id=trainer.user_id,
            specialty="Strength",
            bio="Personal trainer",
            average_rating=5,
            total_reviews=1,
        )
        db.session.add(trainer_profile)
        db.session.commit()

        yield flask_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login_customer(client):
    with client.session_transaction() as sess:
        sess["username"] = "test_customer"


@pytest.fixture
def login_trainer(client):
    with client.session_transaction() as sess:
        sess["username"] = "test_trainer"


@pytest.fixture
def login_admin(client):
    with client.session_transaction() as sess:
        sess["username"] = "test_admin"