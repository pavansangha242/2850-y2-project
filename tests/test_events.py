"""
Event system 
Tests the logic for discovering competitions and making sure the
registration process actually links the user to the event in the DB.
"""
from fitness_app.models import CompetitionResult, User


class TestEvents:

    def test_events_page_loads(self, client):
        response = client.get("/events")
        assert response.status_code == 200

    def test_event_details(self, client, sample_event):
        # sample_event is the integer ID
        response = client.get(f"/events/{sample_event}")
        assert response.status_code == 200

    def test_event_registration(self, client, login_customer, sample_event, app):
        response = client.post(f"/events/register/{sample_event}")
        assert response.status_code in (200, 302)

        with app.app_context():
            user = User.query.filter_by(username="test_customer").first()
            result = CompetitionResult.query.filter_by(
                user_id=user.user_id, competition_id=sample_event
            ).first()
            assert result is not None
