from datetime import date

from fitness_app.extensions import db
from fitness_app.models import Activity, ExerciseType, User


def test_swimming_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/swimming")
    assert response.status_code in [302, 401]


def test_running_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/running")
    assert response.status_code in [302, 401]


def test_cycling_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/cycling")
    assert response.status_code in [302, 401]


def test_walking_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/walking")
    assert response.status_code in [302, 401]


def test_progress_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/progress")
    assert response.status_code in [302, 401]

def test_gym_page_requires_login(client):
    """Redirects if not logged in."""
    response = client.get("/gym")
    assert response.status_code in [302, 401]

def test_swimming_page_loads_for_logged_in_user(client, login_customer):
    """Logged in user sees swimming page."""
    response = client.get("/swimming")
    assert response.status_code == 200
    assert b"Swimming" in response.data


def test_running_page_loads_for_logged_in_user(client, login_customer):
    """Logged in user sees running page."""
    response = client.get("/running")
    assert response.status_code == 200
    assert b"Running" in response.data


def test_cycling_page_loads_for_logged_in_user(client, login_customer):
    """Logged in user sees cycling page."""
    response = client.get("/cycling")
    assert response.status_code == 200
    assert b"Cycling" in response.data


def test_walking_page_loads_for_logged_in_user(client, login_customer):
    """Logged in user sees walking page."""
    response = client.get("/walking")
    assert response.status_code == 200
    assert b"Walking" in response.data

def test_gym_page_loads_for_logged_in_user(client, login_customer):
    """Logged in user sees gym page."""
    response = client.get("/gym")
    assert response.status_code == 200
    assert b"Gym" in response.data or b"gym" in response.data

def test_progress_page_empty_state_for_logged_in_user(client, login_customer):
    """Empty progress page loads without crashing."""
    response = client.get("/progress")
    assert response.status_code == 200
    assert b"No" in response.data or b"data" in response.data


def test_progress_page_shows_logged_activity(client, login_customer, app):
    """Progress page shows a logged activity."""
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
            calories=343,
            notes="Test run",
        )

        db.session.add(activity)
        db.session.commit()

    response = client.get("/progress?sport=Running")
    assert response.status_code == 200
    assert b"Running" in response.data
