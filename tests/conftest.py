"""Pytest fixtures and shared test configuration."""

import os
import sys
from datetime import date

import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from fitness_app.extensions import db  # noqa: E402
from fitness_app.models import (  # noqa: E402
    ChatMessage,
    Competition,
    CompetitionResult,
    ExerciseType,
    GymExercise,
    TrainerProfile,
    User,
)
from run import app as flask_app  # noqa: E402


@pytest.fixture
def app():
    """Create and configure a Flask test application."""
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

        db.session.add_all(
            [
                ExerciseType(name="Swimming", description="Swimming workouts"),
                ExerciseType(name="Running", description="Running workouts"),
                ExerciseType(name="Cycling", description="Cycling workouts"),
                ExerciseType(name="Walking", description="Walking workouts"),
                ExerciseType(name="Gym", description="Gym workouts"),
            ]
        )
        db.session.commit()

        db.session.add_all(
            [
                GymExercise(
                    name="Squat",
                    muscle_group="Legs",
                    description="Lower body exercise",
                    video_url="",
                ),
                GymExercise(
                    name="Bench Press",
                    muscle_group="Chest",
                    description="Upper body exercise",
                    video_url="",
                ),
            ]
        )
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
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture
def login_customer(client):
    """Log in a test customer user."""
    with client.session_transaction() as sess:
        sess["username"] = "test_customer"


@pytest.fixture
def login_trainer(client):
    """Log in a test trainer user."""
    with client.session_transaction() as sess:
        sess["username"] = "test_trainer"


@pytest.fixture
def login_admin(client):
    """Log in a test administrator user."""
    with client.session_transaction() as sess:
        sess["username"] = "test_admin"


# Tests for Mohammed's code
@pytest.fixture
def sample_event(app):
    """Create a sample competition event."""
    with app.app_context():
        event = Competition(
            name="Test Marathon", location="London", distance=10, date=date(2030, 1, 1)
        )
        db.session.add(event)
        db.session.commit()
        # Return the integer ID, not object
        return event.competition_id


@pytest.fixture
def registered_event(app):
    """Create an event and register test_customer."""
    with app.app_context():
        user = User.query.filter_by(username="test_customer").first()

        event = Competition(
            name="Registered Event", location="Test", distance=5, date=date(2030, 1, 1)
        )
        db.session.add(event)
        db.session.commit()

        result = CompetitionResult(
            user_id=user.user_id, competition_id=event.competition_id
        )
        db.session.add(result)
        db.session.commit()

    return event.competition_id


@pytest.fixture
def sample_chat_message(app):
    """Create a chat message for testing."""
    with app.app_context():
        user = User.query.filter_by(username="test_customer").first()

        event = Competition.query.first()
        if not event:
            event = Competition(
                name="Chat Event", location="Test", distance=5, date=date(2030, 1, 1)
            )
            db.session.add(event)
            db.session.commit()

        msg = ChatMessage(
            user_id=user.user_id,
            competition_id=event.competition_id,
            content="Test message",
        )
        db.session.add(msg)
        db.session.commit()

    return msg
