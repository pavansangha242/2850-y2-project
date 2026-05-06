def test_activities_requires_login(client):
    """Test that you cannot access the activities list without logging in."""
    response = client.get("/activities", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_activity_detail_requires_login(client):
    """Test that you cannot access a specific activity's detail page without logging in."""
    response = client.get("/activities/123", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_connect_strava_requires_login(client):
    """Test that the connect-strava endpoint requires an authenticated user."""
    response = client.get("/connect-strava", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_sync_strava_requires_login(client):
    """Test that you cannot sync Strava activities without logging in."""
    response = client.get("/sync-strava", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
