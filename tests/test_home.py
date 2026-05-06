import pytest
from fitness_app.models import Activity, User
from fitness_app.extensions import db


class TestHomePage:

    def test_home_page_loads(self, client, login_customer):
        login_customer
        response = client.get("/home")
        assert response.status_code == 200

    def test_home_shows_summary(self, client, login_customer, app):
        login_customer

        with app.app_context():
            user = User.query.filter_by(username="test_customer").first()

            activity = Activity(
                user_id=user.user_id,
                calories=200,
                distance_km=5,
                exercise_type_id=1,  
            )
            db.session.add(activity)
            db.session.commit()

        response = client.get("/home")
        assert response.status_code == 200
        assert b"Calories" in response.data
