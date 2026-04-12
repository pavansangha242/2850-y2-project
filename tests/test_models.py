"""
Unit tests for the FitTrack application models.
Tests individual model methods and properties in isolation
using systematic testing principles:
  - Size: empty, single, and multiple entries
  - Branching: all logical paths through the code
  - Boundary (edge) cases: values at and around boundaries

These tests use Python's assert (via pytest) to validate
expected behaviour at the function level.
"""
import pytest
from datetime import date, timedelta
from fitness_app import create_app
from fitness_app.extentions import db
from fitness_app.models import (
    User, TrainingPlan, PlannedWorkout, TrainingClient,
    ExerciseType, Activity, Competition, CompetitionResult
)


@pytest.fixture
def app():
    """Create a test application with a fresh in-memory database."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture
def sample_user(app):
    """Create and return a single sample user for testing."""
    with app.app_context():
        user = User(
            first_name='Test', last_name='User',
            email='test@test.com', username='testuser', role='customer'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user.user_id


# ============================================================
# USER MODEL — PASSWORD TESTS
# ============================================================

class TestUserPassword:
    """
    Tests for User.set_password() and User.check_password().
    Covers branching: correct password vs wrong password.
    """

    def test_set_password_hashes_value(self, app, sample_user):
        """Password should be stored as a hash, not plain text."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            # The stored password must NOT be the plain-text input
            assert user.password != 'password123'

    def test_check_password_correct(self, app, sample_user):
        """check_password should return True for the correct password."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            assert user.check_password('password123') is True

    def test_check_password_wrong(self, app, sample_user):
        """check_password should return False for an incorrect password."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            assert user.check_password('wrongpassword') is False

    def test_check_password_empty_string(self, app, sample_user):
        """Boundary: check_password with an empty string should return False."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            assert user.check_password('') is False


# ============================================================
# USER MODEL — REPRESENTATION AND ROLES
# ============================================================

class TestUserModel:
    """
    Tests for User model attributes and __repr__.
    Covers branching: different user roles (customer, pt, administrator).
    """

    def test_user_repr(self, app, sample_user):
        """__repr__ should return a readable string with the username."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            assert repr(user) == '<User testuser>'

    def test_user_role_customer(self, app):
        """Branching: a user can have the 'customer' role."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='c@c.com',
                        username='cust', role='customer')
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            assert user.role == 'customer'

    def test_user_role_pt(self, app):
        """Branching: a user can have the 'pt' role."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='pt@pt.com',
                        username='ptuser', role='pt', approved=False)
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            assert user.role == 'pt'
            assert user.approved is False

    def test_user_role_administrator(self, app):
        """Branching: a user can have the 'administrator' role."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='admin@a.com',
                        username='adminuser', role='administrator')
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            assert user.role == 'administrator'

    def test_user_default_approved_is_true(self, app):
        """New users should default to approved=True."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='d@d.com',
                        username='defuser', role='customer')
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            assert user.approved is True

    def test_user_default_join_date(self, app):
        """New users should have today's date as their join_date."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='e@e.com',
                        username='dateuser', role='customer')
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            assert user.join_date == date.today()


# ============================================================
# COMPETITION MODEL — days_remaining PROPERTY
# ============================================================

class TestCompetitionDaysRemaining:
    """
    Tests for Competition.days_remaining property.
    Covers boundary cases: past, today, and future dates.
    """

    def test_days_remaining_future(self, app):
        """A competition 10 days away should return 10."""
        with app.app_context():
            comp = Competition(name='Future Race', date=date.today() + timedelta(days=10), distance=5.0)
            assert comp.days_remaining == 10

    def test_days_remaining_today(self, app):
        """Boundary: a competition today should return 0."""
        with app.app_context():
            comp = Competition(name='Today Race', date=date.today(), distance=5.0)
            assert comp.days_remaining == 0

    def test_days_remaining_past(self, app):
        """Boundary: a past competition should return 0, not a negative number."""
        with app.app_context():
            comp = Competition(name='Past Race', date=date.today() - timedelta(days=5), distance=5.0)
            assert comp.days_remaining == 0

    def test_days_remaining_tomorrow(self, app):
        """Boundary: a competition tomorrow should return exactly 1."""
        with app.app_context():
            comp = Competition(name='Tomorrow Race', date=date.today() + timedelta(days=1), distance=5.0)
            assert comp.days_remaining == 1

    def test_competition_repr(self, app):
        """__repr__ should return a readable string with the name."""
        with app.app_context():
            comp = Competition(name='Test Marathon', date=date.today(), distance=42.195)
            assert repr(comp) == '<Competition Test Marathon>'


# ============================================================
# ACTIVITY MODEL — SIZE TESTS (empty, single, multiple)
# ============================================================

class TestActivitySize:
    """
    Size tests for Activity records on a User.
    Tests the cases when a user has zero, one, or many activities.
    """

    def test_user_no_activities(self, app, sample_user):
        """Size: a new user should have zero activities (empty list)."""
        with app.app_context():
            user = db.session.get(User, sample_user)
            assert len(user.activities) == 0

    def test_user_single_activity(self, app, sample_user):
        """Size: adding one activity should give a list of length 1."""
        with app.app_context():
            exercise = ExerciseType(name='Running', description='Test')
            db.session.add(exercise)
            db.session.flush()

            activity = Activity(
                user_id=sample_user, exercise_type_id=exercise.exercise_type_id,
                duration_minutes=30, distance_km=5.0, calories=300
            )
            db.session.add(activity)
            db.session.commit()

            user = db.session.get(User, sample_user)
            assert len(user.activities) == 1

    def test_user_multiple_activities(self, app, sample_user):
        """Size: adding three activities should give a list of length 3."""
        with app.app_context():
            exercise = ExerciseType(name='Cycling', description='Test')
            db.session.add(exercise)
            db.session.flush()

            for i in range(3):
                act = Activity(
                    user_id=sample_user, exercise_type_id=exercise.exercise_type_id,
                    duration_minutes=20 + i * 10, distance_km=5.0 + i, calories=200 + i * 50
                )
                db.session.add(act)
            db.session.commit()

            user = db.session.get(User, sample_user)
            assert len(user.activities) == 3


# ============================================================
# ACTIVITY MODEL — BOUNDARY / EDGE CASES
# ============================================================

class TestActivityBoundary:
    """
    Boundary tests for Activity fields.
    Tests values at and around zero (the lower boundary).
    """

    def test_activity_zero_duration(self, app, sample_user):
        """Boundary: an activity with 0 minutes should be valid."""
        with app.app_context():
            exercise = ExerciseType(name='Walk', description='Test')
            db.session.add(exercise)
            db.session.flush()

            activity = Activity(
                user_id=sample_user, exercise_type_id=exercise.exercise_type_id,
                duration_minutes=0, distance_km=0.0, calories=0
            )
            db.session.add(activity)
            db.session.commit()

            assert activity.duration_minutes == 0
            assert activity.distance_km == 0.0
            assert activity.calories == 0

    def test_activity_large_values(self, app, sample_user):
        """Boundary: an activity with very large values should be valid."""
        with app.app_context():
            exercise = ExerciseType(name='Ultra', description='Test')
            db.session.add(exercise)
            db.session.flush()

            activity = Activity(
                user_id=sample_user, exercise_type_id=exercise.exercise_type_id,
                duration_minutes=1440, distance_km=100.0, calories=5000
            )
            db.session.add(activity)
            db.session.commit()

            assert activity.duration_minutes == 1440  # 24 hours
            assert activity.distance_km == 100.0
            assert activity.calories == 5000

    def test_activity_default_values(self, app, sample_user):
        """Boundary: when no values are given, defaults should apply."""
        with app.app_context():
            exercise = ExerciseType(name='Rest', description='Test')
            db.session.add(exercise)
            db.session.flush()

            activity = Activity(
                user_id=sample_user, exercise_type_id=exercise.exercise_type_id
            )
            db.session.add(activity)
            db.session.commit()

            assert activity.duration_minutes == 0
            assert activity.distance_km == 0.0
            assert activity.calories == 0
            assert activity.notes == ''
            assert activity.date == date.today()


# ============================================================
# COMPETITION RESULT — BRANCHING TESTS
# ============================================================

class TestCompetitionResultBranching:
    """
    Branching tests for CompetitionResult.
    Tests different paths: with/without personal best, with/without position.
    """

    def test_result_with_personal_best(self, app, sample_user):
        """Branching: a result marked as personal best should store True."""
        with app.app_context():
            comp = Competition(name='PB Race', date=date.today(), distance=10.0)
            db.session.add(comp)
            db.session.flush()

            result = CompetitionResult(
                user_id=sample_user, competition_id=comp.competition_id,
                finish_time='0:45:30', position=1, personal_best=True
            )
            db.session.add(result)
            db.session.commit()

            assert result.personal_best is True
            assert result.position == 1

    def test_result_without_personal_best(self, app, sample_user):
        """Branching: a result NOT marked as personal best should store False."""
        with app.app_context():
            comp = Competition(name='Normal Race', date=date.today(), distance=10.0)
            db.session.add(comp)
            db.session.flush()

            result = CompetitionResult(
                user_id=sample_user, competition_id=comp.competition_id,
                finish_time='1:20:00', position=15, personal_best=False
            )
            db.session.add(result)
            db.session.commit()

            assert result.personal_best is False
            assert result.position == 15

    def test_result_default_values(self, app, sample_user):
        """Boundary: a result with no optional fields should use defaults."""
        with app.app_context():
            comp = Competition(name='Default Race', date=date.today(), distance=5.0)
            db.session.add(comp)
            db.session.flush()

            result = CompetitionResult(
                user_id=sample_user, competition_id=comp.competition_id
            )
            db.session.add(result)
            db.session.commit()

            assert result.finish_time == ''
            assert result.position == 0
            assert result.personal_best is False


# ============================================================
# TRAINING PLAN — SIZE TESTS (planned workouts)
# ============================================================

class TestTrainingPlanSize:
    """
    Size tests for PlannedWorkout records in a TrainingPlan.
    Tests empty, single, and multiple planned workouts.
    """

    def test_plan_no_workouts(self, app, sample_user):
        """Size: a new training plan should have zero planned workouts."""
        with app.app_context():
            plan = TrainingPlan(
                user_id=sample_user, name='Empty Plan',
                start_date=date.today(), end_date=date.today() + timedelta(weeks=4)
            )
            db.session.add(plan)
            db.session.commit()

            assert len(plan.planned_workouts) == 0

    def test_plan_single_workout(self, app, sample_user):
        """Size: a plan with one workout should have a list of length 1."""
        with app.app_context():
            exercise = ExerciseType(name='Run', description='Test')
            db.session.add(exercise)
            db.session.flush()

            plan = TrainingPlan(
                user_id=sample_user, name='One Workout Plan',
                start_date=date.today(), end_date=date.today() + timedelta(weeks=4)
            )
            db.session.add(plan)
            db.session.flush()

            pw = PlannedWorkout(
                plan_id=plan.plan_id, exercise_type_id=exercise.exercise_type_id,
                planned_date=date.today() + timedelta(days=1),
                target_duration=30, target_distance=5.0
            )
            db.session.add(pw)
            db.session.commit()

            assert len(plan.planned_workouts) == 1

    def test_plan_multiple_workouts(self, app, sample_user):
        """Size: a plan with five workouts should have a list of length 5."""
        with app.app_context():
            exercise = ExerciseType(name='Swim', description='Test')
            db.session.add(exercise)
            db.session.flush()

            plan = TrainingPlan(
                user_id=sample_user, name='Full Plan',
                start_date=date.today(), end_date=date.today() + timedelta(weeks=8)
            )
            db.session.add(plan)
            db.session.flush()

            for day in range(5):
                pw = PlannedWorkout(
                    plan_id=plan.plan_id, exercise_type_id=exercise.exercise_type_id,
                    planned_date=date.today() + timedelta(days=day + 1),
                    target_duration=30, target_distance=3.0
                )
                db.session.add(pw)
            db.session.commit()

            assert len(plan.planned_workouts) == 5


# ============================================================
# TRAINING CLIENT — BRANCHING (active vs inactive)
# ============================================================

class TestTrainingClientBranching:
    """
    Branching tests for TrainingClient relationships.
    Tests active and inactive trainer-client links.
    """

    def test_active_training_client(self, app):
        """Branching: an active training client should have active=True."""
        with app.app_context():
            trainer = User(first_name='T', last_name='T', email='t@t.com',
                           username='trainer1', role='pt')
            trainer.set_password('pw')
            client = User(first_name='C', last_name='C', email='cl@c.com',
                          username='client1', role='customer')
            client.set_password('pw')
            db.session.add_all([trainer, client])
            db.session.flush()

            tc = TrainingClient(
                trainer_id=trainer.user_id, client_id=client.user_id, active=True
            )
            db.session.add(tc)
            db.session.commit()

            assert tc.active is True

    def test_inactive_training_client(self, app):
        """Branching: a deactivated training client should have active=False."""
        with app.app_context():
            trainer = User(first_name='T2', last_name='T2', email='t2@t.com',
                           username='trainer2', role='pt')
            trainer.set_password('pw')
            client = User(first_name='C2', last_name='C2', email='c2@c.com',
                          username='client2', role='customer')
            client.set_password('pw')
            db.session.add_all([trainer, client])
            db.session.flush()

            tc = TrainingClient(
                trainer_id=trainer.user_id, client_id=client.user_id, active=False
            )
            db.session.add(tc)
            db.session.commit()

            assert tc.active is False
