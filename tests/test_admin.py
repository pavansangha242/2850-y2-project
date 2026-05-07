"""
Admin-only functionality.
Covers deleting users and the PT approval workflow.
These tests ensure the administrator role
privileges are being enforced correctly.
"""

from fitness_app.extensions import db
from fitness_app.models import User


class TestAdmin:

    def test_admin_requires_login(self, client):
        # Checks if unauthorised users are redirected to login
        assert client.get("/admin").status_code == 302

    def test_admin_access(self, client, login_admin):
        # Uses existing login_admin
        assert client.get("/admin").status_code == 200

    def test_delete_user(self, client, login_admin, app):
        with app.app_context():
            # Better to use the 'test_customer' created in conftest.py
            user = User.query.filter_by(username="test_customer").first()
            user_id = user.user_id

        # Perform delete
        response = client.post(f"/admin/delete-user/{user_id}", follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            # Verify user is gone
            assert User.query.get(user_id) is None

    def test_approve_pt(self, client, login_admin, app):
        with app.app_context():
            # Use the 'test_trainer' from conftest.py
            pt = User.query.filter_by(username="test_trainer").first()
            # Ensure it's False initially for a valid test
            pt.approved = False
            db.session.commit()
            pt_id = pt.user_id

        client.post(f"/admin/approve-pt/{pt_id}", follow_redirects=True)

        with app.app_context():
            updated_pt = User.query.get(pt_id)
            assert updated_pt.approved is True
