from datetime import date

from fitness_app.extensions import db
from fitness_app.models import Activity, ExerciseType, User


def test_customer_cannot_access_trainer_dashboard(client, login_customer):
    response = client.get("/trainer-dashboard")
    assert response.status_code in [302, 403]


def test_customer_cannot_access_pt_clients(client, login_customer):
    response = client.get("/pt-clients")
    assert response.status_code in [302, 403]


def test_logged_out_user_cannot_access_progress(client):
    response = client.get("/progress")
    assert response.status_code in [302, 401]


def test_delete_requires_post(client, login_customer):
    response = client.get("/running/delete/1")
    assert response.status_code in [302, 404, 405]


def test_invalid_delete_id_does_not_crash(client, login_customer):
    response = client.post("/running/delete/999999")
    assert response.status_code in [302, 404]


def test_user_cannot_delete_other_users_activity(client, login_customer, app):
    with app.app_context():
        other_user = User(
            username="other_user",
            first_name="Other",
            last_name="User",
            email="other@test.com",
            role="customer",
            password_hash="test",
            approved=True,
        )
        db.session.add(other_user)
        db.session.commit()

        running = ExerciseType.query.filter_by(name="Running").first()

        other_activity = Activity(
            user_id=other_user.user_id,
            exercise_type_id=running.exercise_type_id,
            date=date.today(),
            duration_minutes=30,
            distance_km=5,
            pace_per_km=360,
            calories=300,
            notes="Other user's run",
        )

        db.session.add(other_activity)
        db.session.commit()
        activity_id = other_activity.activity_id

    response = client.post(f"/running/delete/{activity_id}")
    assert response.status_code in [302, 404]

    with app.app_context():
        activity = Activity.query.get(activity_id)
        assert activity is not None
