def test_login_page_renders(client):
    """Test that the login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower()


def test_register_page_renders(client):
    """Test that the registration page loads correctly."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"register" in response.data.lower()


def test_logout_redirects_to_login(client, login_customer):
    """Test that logging out redirects the user to the login page."""
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_settings_requires_login(client):
    """Test that you cannot access settings without logging in."""
    response = client.get("/settings", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_survey_requires_login(client):
    """Test that the survey page redirects to login if not authenticated."""
    response = client.get("/survey", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_survey_accessible_by_customer(client, login_customer):
    """Test that a logged-in customer can access the survey page."""
    response = client.get("/survey")
    assert response.status_code == 200


def test_pt_clients_requires_login(client):
    """Test that the PT clients page redirects to login if not authenticated."""
    response = client.get("/clients", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_pt_view_survey_requires_login(client):
    """Test that the PT view survey page redirects to login if not authenticated."""
    response = client.get("/clients/1/survey", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_register_empty_input_handled_gracefully(client):
    """Test that empty user inputs during registration are handled gracefully (Mark scheme requirement)."""
    response = client.post(
        "/register",
        data={
            "first_name": "New",
            "last_name": "User",
            "username": "newuser",
            "password": "password",
            "confirm_password": "password",
            "email": "newuser@test.com",
            "phone": "12345",
            "role": "customer",
            # Intentionally leaving out required health fields like 'age', 'weight'
        },
    )
    # Should stay on register page and show an error, not crash the server
    assert response.status_code == 200
    assert b"Please fill in all health goal fields" in response.data


def test_customer_can_submit_survey_integration(client, login_customer, app):
    """Integration test checking that submitting a survey saves to the database (Mark scheme requirement)."""
    from fitness_app.models import HealthSurvey, User

    response = client.post(
        "/survey",
        data={
            "workout_hours_per_day": "1.5",
            "workout_days_per_week": "5",
            "preferred_workout_type": "Strength",
            "fitness_level": "Beginner",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Check the database to ensure it was saved!
    with app.app_context():
        user = User.query.filter_by(username="test_customer").first()
        survey = HealthSurvey.query.filter_by(user_id=user.user_id).first()
        assert survey is not None
        assert survey.preferred_workout_type == "Strength"
        assert survey.workout_days_per_week == 5
