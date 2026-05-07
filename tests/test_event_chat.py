"""
Community chat.
The chat tests ensure only logged in users can participate in the feed.
"""

from fitness_app.models import ChatMessage


class TestEventChat:

    def test_chat_requires_login(self, client, sample_event):
        # sample_event is the integer ID from conftest.py
        response = client.get(f"/events/{sample_event}/chat")
        assert response.status_code in (302, 401)

    def test_send_message(self, client, login_customer, sample_event, app):
        # login_customer is already active
        response = client.post(
            f"/events/{sample_event}/chat/send", data={"message": "Hello"}
        )
        assert response.status_code in (200, 302)

        with app.app_context():
            # Checking database to ensure message was saved
            msg = ChatMessage.query.filter_by(content="Hello").first()
            assert msg is not None

    def test_empty_message_handled(self, client, login_customer, sample_event):
        # Using the ID directly
        response = client.post(
            f"/events/{sample_event}/chat/send", data={"message": ""}
        )
        assert response.status_code in (200, 302, 400)
