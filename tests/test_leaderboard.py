

class TestLeaderboard:

    def test_leaderboard_loads(self, client, login_customer):
        login_customer
        response = client.get("/leaderboard")
        assert response.status_code == 200

    def test_leaderboard_week(self, client, login_customer):
        login_customer
        response = client.get("/leaderboard?period=week")
        assert response.status_code == 200

    def test_leaderboard_month(self, client, login_customer):
        login_customer
        response = client.get("/leaderboard?period=month")
        assert response.status_code == 200
