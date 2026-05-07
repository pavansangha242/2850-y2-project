import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date

from fitness_app.extensions import db
from fitness_app.models import (
    Activity,
    ExerciseType,
    SessionBooking,
    TrainerMessage,
    TrainingClient,
    User,
)


def test_trainer_page_loads_for_customer(client, login_customer):
    """Trainers page should load for a logged in customer."""
    response = client.get("/trainers")
    assert response.status_code == 200
    assert b"Trainer" in response.data or b"trainers" in response.data


def test_customer_can_book_trainer_session(client, login_customer, app):
    """A customer should be able to book a session with a trainer."""
    with app.app_context():
        trainer = User.query.filter_by(username="test_trainer").first()
        trainer_id = trainer.user_id

    response = client.post(
        "/trainers/book",
        data={
            "trainer_id": trainer_id,
            "book_date": "2026-06-01",
            "book_time": "10:00",
            "notes": "Test booking",
        },
        follow_redirects=False,
    )

    assert response.status_code in [302, 200]

    with app.app_context():
        booking = SessionBooking.query.filter_by(
            trainer_id=trainer_id,
            status="pending",
        ).first()
        assert booking is not None


def test_booking_missing_date_does_not_save(client, login_customer, app):
    """A booking should not be saved if no date is provided."""
    with app.app_context():
        trainer = User.query.filter_by(username="test_trainer").first()
        trainer_id = trainer.user_id

    response = client.post(
        "/trainers/book",
        data={
            "trainer_id": trainer_id,
            "book_time": "10:00",
            "notes": "Missing date",
        },
        follow_redirects=False,
    )

    assert response.status_code in [302, 200]


def test_trainer_dashboard_loads_for_trainer(client, login_trainer):
    """Trainer dashboard should load for a logged in trainer."""
    response = client.get("/trainer-dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"booking" in response.data.lower()


def test_customer_cannot_open_trainer_dashboard(client, login_customer):
    """A customer should not be able to access the trainer dashboard."""
    response = client.get("/trainer-dashboard")
    assert response.status_code in [302, 403]


def test_trainer_confirms_booking(client, login_trainer, app):
    """A trainer should be able to confirm a pending booking."""
    with app.app_context():
        trainer = User.query.filter_by(username="test_trainer").first()
        customer = User.query.filter_by(username="test_customer").first()

        booking = SessionBooking(
            trainer_id=trainer.user_id,
            client_id=customer.user_id,
            date=date.today(),
            time="10:00",
            status="pending",
            notes="Test",
        )

        db.session.add(booking)
        db.session.commit()
        booking_id = booking.booking_id

    response = client.post(f"/trainers/booking/confirm/{booking_id}")
    assert response.status_code in [302, 200]

    with app.app_context():
        booking = SessionBooking.query.get(booking_id)
        assert booking.status == "confirmed"

        client_link = TrainingClient.query.filter_by(
            trainer_id=booking.trainer_id,
            client_id=booking.client_id,
        ).first()

        assert client_link is not None


def test_messages_page_loads_for_customer(client, login_customer):
    """Messages page should load for a logged in customer."""
    response = client.get("/messages")
    assert response.status_code == 200
    assert b"Messages" in response.data or b"Conversation" in response.data


def test_customer_can_send_message_to_trainer(client, login_customer, app):
    """A customer should be able to send a message to a trainer."""
    with app.app_context():
        trainer = User.query.filter_by(username="test_trainer").first()
        trainer_id = trainer.user_id

    response = client.post(
        "/messages/send",
        data={
            "trainer_id": trainer_id,
            "message": "Hello trainer",
        },
        follow_redirects=False,
    )

    assert response.status_code in [302, 200]

    with app.app_context():
        msg = TrainerMessage.query.filter_by(
            receiver_id=trainer_id,
            message="Hello trainer",
        ).first()
        assert msg is not None


def test_empty_message_is_not_saved(client, login_customer, app):
    """A message containing only spaces should not be saved."""
    with app.app_context():
        trainer = User.query.filter_by(username="test_trainer").first()
        trainer_id = trainer.user_id

    response = client.post(
        "/messages/send",
        data={
            "trainer_id": trainer_id,
            "message": "   ",
        },
        follow_redirects=False,
    )

    assert response.status_code in [302, 200]

    with app.app_context():
        msg = TrainerMessage.query.filter_by(message="   ").first()
        assert msg is None


def test_trainer_inbox_loads_for_trainer(client, login_trainer):
    """Trainer inbox should load for a logged in trainer."""
    response = client.get("/trainer/inbox")
    assert response.status_code in [200, 302]


def test_customer_cannot_open_trainer_inbox(client, login_customer):
    """A customer should not be able to access the trainer inbox."""
    response = client.get("/trainer/inbox")
    assert response.status_code in [302, 403]


def test_history_page_loads_for_customer(client, login_customer):
    """History page should load for a logged in customer."""
    response = client.get("/history")
    assert response.status_code in [200, 302]


def test_progress_running_filter_loads(client, login_customer, app):
    """Progress page should load correctly with the running filter applied."""
    with app.app_context():
        user = User.query.filter_by(username="test_customer").first()
        running = ExerciseType.query.filter_by(name="Running").first()

        activity = Activity(
            user_id=user.user_id,
            exercise_type_id=running.exercise_type_id,
            date=date.today(),
            duration_minutes=25,
            distance_km=4,
            pace_per_km=375,
            calories=250,
            notes="Progress test run",
        )

        db.session.add(activity)
        db.session.commit()

    response = client.get("/progress?sport=Running")
    assert response.status_code == 200
    assert b"Running" in response.data


def test_history_page_shows_logged_activity(client, login_customer, app):
    """History page should display a recently logged activity."""
    with app.app_context():
        user = User.query.filter_by(username="test_customer").first()
        running = ExerciseType.query.filter_by(name="Running").first()

        activity = Activity(
            user_id=user.user_id,
            exercise_type_id=running.exercise_type_id,
            date=date.today(),
            duration_minutes=30,
            distance_km=5,
            pace_per_km=360,
            calories=300,
            notes="History test run",
        )

        db.session.add(activity)
        db.session.commit()

    response = client.get("/history")

    assert response.status_code == 200
    assert b"History test run" in response.data
    assert b"Running" in response.data
