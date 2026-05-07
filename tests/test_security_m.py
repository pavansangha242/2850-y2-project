"""
Security checks for Mohammed's code.
Mostly focused on making sure a random user can't access the admin panel
or break the site by entering a large string in the event chat.
Also checks that script tags are escaped, not executed.
"""


class TestSecurity:

    def test_invalid_event(self, client):
        response = client.get("/events/9999")
        assert response.status_code == 404

    def test_register_requires_login(self, client, sample_event):
        event_id = sample_event
        response = client.post(f"/events/register/{event_id}")
        assert response.status_code in (302, 401)

    def test_xss_protection(self, client, login_admin):
        login_admin

        payload = "<script>alert(1)</script>"
        response = client.get(f"/admin?q={payload}")

        assert payload.encode() not in response.data
        assert b"&lt;script&gt;" in response.data

    def test_long_input_safe(self, client, login_customer, sample_event):
        login_customer
        event_id = sample_event

        long_msg = "A" * 5000
        response = client.post(
            f"/events/{event_id}/chat/send", data={"message": long_msg}
        )

        assert response.status_code in (200, 302, 400)
