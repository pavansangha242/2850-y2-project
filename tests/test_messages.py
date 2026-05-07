"""
Tests for messaging system (DMs + trainer inbox + security)
Covers:

- Access control
- Sending messages
- Empty input handling
- Role-based behaviour

Checks empty messages aren't saved to the db and PTs get their own
inbox.
"""

from fitness_app.models import TrainerMessage, User


class TestMessagesPage:

    def test_messages_requires_login(self, client):
        """Messages page should redirect if user not logged in."""
        response = client.get("/messages")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_messages_page_loads(self, client, login_customer):
        """Messages page should load for logged-in users."""
        response = client.get("/messages")
        assert response.status_code == 200
        assert b"My Messages" in response.data

    def test_no_conversations_message(self, client, login_customer):
        """Should show message when no conversations exist."""
        response = client.get("/messages")
        assert b"No conversations yet" in response.data


class TestDirectMessages:

    def test_send_message_success(self, client, login_customer, app):
        """User can send a message to a trainer."""
        with app.app_context():
            # Get the trainer ID while inside the context
            trainer = User.query.filter_by(role="pt").first()
            trainer_id = trainer.user_id

        response = client.post(
            "/messages/send",
            data={"trainer_id": trainer_id, "message": "Hello trainer"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            msg = TrainerMessage.query.filter_by(receiver_id=trainer_id).first()
            assert msg is not None
            assert msg.message == "Hello trainer"

    def test_send_empty_message_not_saved(self, client, login_customer, app):
        """Empty messages should not be stored."""
        with app.app_context():
            trainer = User.query.filter_by(role="pt").first()
            trainer_id = trainer.user_id

        client.post(
            "/messages/send", data={"trainer_id": trainer_id, "message": ""}  # empty
        )

        with app.app_context():
            msgs = TrainerMessage.query.filter_by(receiver_id=trainer_id).all()
            assert len(msgs) == 0

    def test_send_requires_login(self, client):
        """Sending message without login should redirect."""
        response = client.post(
            "/messages/send", data={"trainer_id": 1, "message": "Hi"}
        )
        assert response.status_code == 302
        assert "/login" in response.location


class TestTrainerInbox:

    def test_trainer_inbox_requires_login(self, client):
        """Trainer inbox should require login."""
        response = client.get("/trainer/inbox")
        assert response.status_code == 302

    def test_trainer_only_access(self, client, login_customer):
        """Non-trainers should be redirected away."""
        response = client.get("/trainer/inbox")
        assert response.status_code == 302

    def test_trainer_inbox_loads(self, client, login_trainer):
        """Trainer can access inbox."""
        response = client.get("/trainer/inbox")
        assert response.status_code == 200

    def test_trainer_send_message(self, client, login_trainer, app):
        """Trainer can reply to a client."""
        with app.app_context():
            customer = User.query.filter_by(role="customer").first()
            customer_id = customer.user_id

        response = client.post(
            "/trainer/inbox/send",
            data={"client_id": customer_id, "message": "Reply message"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            msg = TrainerMessage.query.filter_by(receiver_id=customer_id).first()
            assert msg is not None
            assert msg.message == "Reply message"


class TestSecurity:

    def test_xss_message_not_executed(self, client, login_customer, app):
        """Script tags should not execute in messages."""
        with app.app_context():
            trainer = User.query.filter_by(role="pt").first()
            trainer_id = trainer.user_id

        payload = "<script>alert(1)</script>"

        client.post(
            "/messages/send", data={"trainer_id": trainer_id, "message": payload}
        )

        response = client.get("/messages")
        # Check that the raw script tag isn't there
        assert payload.encode() not in response.data

    def test_long_message_handled(self, client, login_customer, app):
        """Very long messages should not crash system."""
        with app.app_context():
            trainer = User.query.filter_by(role="pt").first()
            trainer_id = trainer.user_id

        long_msg = "a" * 5000

        response = client.post(
            "/messages/send", data={"trainer_id": trainer_id, "message": long_msg}
        )
        assert response.status_code in (200, 302)
