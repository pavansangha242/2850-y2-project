"""
Automated tests for the FitTrack fitness application.
Tests cover all three main pages (Home, Events, Admin)
and their key features including page loading, event
registration, calendar download, user deletion, and
PT approval/rejection.
"""
import pytest
from fitness_app import create_app
from fitness_app.extentions import db
from fitness_app.models import User, Competition, CompetitionResult


@pytest.fixture
def app():
    """Create a test application with a fresh in-memory database."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed test data
        from fitness_app import seed_database
        seed_database()

    yield app


@pytest.fixture
def client(app):
    """Create a test client for making HTTP requests."""
    return app.test_client()


# ============================================================
# HOME PAGE TESTS
# ============================================================

class TestHomePage:
    """Tests for the home page dashboard."""

    def test_home_page_loads(self, client):
        """Home page should return status 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_page_shows_user_name(self, client):
        """Home page should display the current user's name (Ahmed)."""
        response = client.get('/')
        assert b'Ahmed' in response.data

    def test_home_page_shows_summary(self, client):
        """Home page should display today's summary section."""
        response = client.get('/')
        assert b"Today\\'s Summary" in response.data or b"Today" in response.data

    def test_home_page_shows_quick_actions(self, client):
        """Home page should display quick action buttons."""
        response = client.get('/')
        assert b'Quick Actions' in response.data

    def test_home_page_shows_recommended_activities(self, client):
        """Home page should display recommended activities."""
        response = client.get('/')
        assert b'Running' in response.data
        assert b'Cycling' in response.data
        assert b'Swimming' in response.data
        assert b'Walking' in response.data


# ============================================================
# EVENTS PAGE TESTS
# ============================================================

class TestEventsPage:
    """Tests for the events page and competition features."""

    def test_events_page_loads(self, client):
        """Events page should return status 200."""
        response = client.get('/events')
        assert response.status_code == 200

    def test_events_page_shows_competitions(self, client):
        """Events page should display upcoming competitions."""
        response = client.get('/events')
        assert b'Spring Cycling Race' in response.data

    def test_event_details_page_loads(self, client):
        """Event details page should return status 200."""
        response = client.get('/events/1')
        assert response.status_code == 200

    def test_event_details_shows_info(self, client):
        """Event details page should show competition information."""
        response = client.get('/events/1')
        assert b'City Marathon' in response.data
        assert b'City Centre' in response.data

    def test_event_details_404_for_invalid_id(self, client):
        """Event details should return 404 for non-existent competition."""
        response = client.get('/events/999')
        assert response.status_code == 404

    def test_calendar_download(self, client):
        """Calendar download should return an .ics file."""
        response = client.get('/events/1/calendar')
        assert response.status_code == 200
        assert b'BEGIN:VCALENDAR' in response.data
        assert b'City Marathon' in response.data

    def test_event_registration(self, client, app):
        """Registering for an event should create a competition result."""
        response = client.post('/events/register/1', follow_redirects=True)
        assert response.status_code == 200

        # Check that a result was created in the database
        with app.app_context():
            ahmed = User.query.filter_by(username='ahmed').first()
            result = CompetitionResult.query.filter_by(
                user_id=ahmed.user_id, competition_id=1
            ).first()
            assert result is not None

    def test_duplicate_registration_prevented(self, client, app):
        """Registering twice for the same event should not create duplicates."""
        client.post('/events/register/1')
        client.post('/events/register/1')

        with app.app_context():
            ahmed = User.query.filter_by(username='ahmed').first()
            results = CompetitionResult.query.filter_by(
                user_id=ahmed.user_id, competition_id=1
            ).all()
            assert len(results) == 1


# ============================================================
# ADMIN PAGE TESTS
# ============================================================

class TestAdminPage:
    """Tests for the admin dashboard features."""

    def test_admin_page_loads(self, client):
        """Admin page should return status 200."""
        response = client.get('/admin')
        assert response.status_code == 200

    def test_admin_shows_statistics(self, client):
        """Admin page should display platform statistics."""
        response = client.get('/admin')
        assert b'Platform Statistics' in response.data
        assert b'Total Users' in response.data

    def test_admin_shows_pending_pts(self, client):
        """Admin page should show pending PT applications."""
        response = client.get('/admin')
        assert b'Sarah' in response.data
        assert b'David' in response.data

    def test_admin_shows_approved_pts(self, client):
        """Admin page should show approved trainers."""
        response = client.get('/admin')
        assert b'Daniel' in response.data

    def test_admin_search_users(self, client):
        """Admin search should filter users by name."""
        response = client.get('/admin?q=Noor')
        assert response.status_code == 200
        assert b'Noor' in response.data

    def test_admin_search_no_results(self, client):
        """Admin search should handle queries with no matches."""
        response = client.get('/admin?q=zzzzzzz')
        assert response.status_code == 200
        assert b'No users found' in response.data

    def test_delete_user(self, client, app):
        """Deleting a user should remove them from the database."""
        with app.app_context():
            james = User.query.filter_by(username='jamesmitchell').first()
            james_id = james.user_id

        response = client.post(f'/admin/delete-user/{james_id}', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            deleted_user = User.query.filter_by(username='jamesmitchell').first()
            assert deleted_user is None

    def test_cannot_delete_admin(self, client, app):
        """Admin users should not be deletable."""
        with app.app_context():
            admin = User.query.filter_by(role='administrator').first()
            admin_id = admin.user_id

        client.post(f'/admin/delete-user/{admin_id}')

        with app.app_context():
            admin = User.query.filter_by(role='administrator').first()
            assert admin is not None

    def test_approve_pt(self, client, app):
        """Approving a PT should set their approved status to True."""
        with app.app_context():
            sarah = User.query.filter_by(username='sarahjohnson').first()
            sarah_id = sarah.user_id
            assert sarah.approved is False

        response = client.post(f'/admin/approve-pt/{sarah_id}', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            sarah = User.query.filter_by(username='sarahjohnson').first()
            assert sarah.approved is True

    def test_reject_pt(self, client, app):
        """Rejecting a PT should remove them from the database."""
        with app.app_context():
            david = User.query.filter_by(username='davidlee').first()
            david_id = david.user_id

        response = client.post(f'/admin/reject-pt/{david_id}', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            david = User.query.filter_by(username='davidlee').first()
            assert david is None


# ============================================================
# SECURITY & EDGE CASE TESTS
# ============================================================

class TestSecurityAndEdgeCases:
    """Tests for input validation, error handling, and security risks."""

    def test_search_with_empty_input(self, client):
        """Empty search input should not cause errors."""
        response = client.get('/admin?q=')
        assert response.status_code == 200

    def test_search_with_special_characters(self, client):
        """Special characters in search should be handled safely."""
        response = client.get('/admin?q=%25%27%22%3C%3E')
        assert response.status_code == 200

    def test_search_with_script_tag(self, client):
        """HTML/script tags in search should not be executed (XSS prevention)."""
        response = client.get('/admin?q=<script>alert(1)</script>')
        assert response.status_code == 200
        # The script tag should not appear unescaped in the response
        assert b'<script>alert(1)</script>' not in response.data

    def test_delete_nonexistent_user(self, client):
        """Trying to delete a user that does not exist should return 404."""
        response = client.post('/admin/delete-user/9999')
        assert response.status_code == 404

    def test_register_nonexistent_event(self, client):
        """Registering for a competition that does not exist should return 404."""
        response = client.post('/events/register/9999')
        assert response.status_code == 404

    def test_view_nonexistent_event(self, client):
        """Viewing a competition that does not exist should return 404."""
        response = client.get('/events/9999')
        assert response.status_code == 404

    def test_approve_nonexistent_user(self, client):
        """Approving a user that does not exist should return 404."""
        response = client.post('/admin/approve-pt/9999')
        assert response.status_code == 404

    def test_reject_nonexistent_user(self, client):
        """Rejecting a user that does not exist should return 404."""
        response = client.post('/admin/reject-pt/9999')
        assert response.status_code == 404

    def test_calendar_nonexistent_event(self, client):
        """Downloading calendar for nonexistent event should return 404."""
        response = client.get('/events/9999/calendar')
        assert response.status_code == 404
