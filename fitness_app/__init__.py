from flask import Flask
from fitness_app.extensions import db
from fitness_app.models import (
    User,
    TrainingPlan,
    PlannedWorkout,
    TrainingClient,
    ExerciseType,
    Activity,
    Competition,
    CompetitionResult,
    ChatMessage,
    TrainerProfile,
)
from datetime import date, datetime, timedelta


# set up the flask app
def create_app():
    app = Flask(__name__)

    # config stuff
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        basedir, "..", "fitness_app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # start extensions
    db.init_app(app)

    # bring in all the blueprints
    from fitness_app.routes.home import home_bp
    from fitness_app.routes.events import events_bp
    from fitness_app.routes.leaderboard import leaderboard_bp
    from fitness_app.routes.admin import admin_bp
    from fitness_app.routes.swimming import swimming_bp
    from fitness_app.routes.cycling import cycling_bp
    from fitness_app.routes.running import running_bp
    from fitness_app.routes.walking import walking_bp
    from fitness_app.routes.gym import gym_bp

    # register all the blueprints
    from fitness_app.routes.auth import auth
    from fitness_app.routes.progress import progress
    from fitness_app.routes.history import history
    from fitness_app.routes.sport_stats import sport_stats
    from fitness_app.routes.trainers import trainers
    from fitness_app.routes.messages import messages_bp
    from fitness_app.routes.strava import strava_bp

    # register all
    app.register_blueprint(home_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(swimming_bp)
    app.register_blueprint(cycling_bp)
    app.register_blueprint(running_bp)
    app.register_blueprint(walking_bp)
    app.register_blueprint(gym_bp)

    app.register_blueprint(auth)
    app.register_blueprint(progress)
    app.register_blueprint(history)
    app.register_blueprint(sport_stats)
    app.register_blueprint(trainers)
    app.register_blueprint(messages_bp)
    app.register_blueprint(strava_bp)

    # create tables and add sample data
    with app.app_context():
        db.create_all()
        seed_database()

        approved_trainers = User.query.filter_by(role="pt", approved=True).all()

        for trainer in approved_trainers:
            profile = TrainerProfile.query.filter_by(user_id=trainer.user_id).first()

            if not profile:
                profile = TrainerProfile(
                    user_id=trainer.user_id,
                    specialty="Personal Trainer",
                    bio="Certified personal trainer.|||Gym training|||Fitness coaching|||Workout plans",
                    average_rating=0,
                    total_reviews=0,
                )
                db.session.add(profile)

        db.session.commit()

    return app


def seed_database():
    """Insert sample data if the database is empty."""
    if User.query.first():
        return

    # ---- Exercise Types ----
    swimming = ExerciseType(name="Swimming", description="Pool or open water swimming")
    cycling = ExerciseType(name="Cycling", description="Road or stationary cycling")
    running = ExerciseType(name="Running", description="Outdoor or treadmill running")
    walking = ExerciseType(name="Walking", description="Casual or brisk walking")
    strength = ExerciseType(
        name="Strength Training", description="Gym and weight training"
    )
    db.session.add_all([swimming, cycling, running, walking, strength])
    db.session.flush()

    # ---- Users ----
    admin = User(
        first_name="Michael",
        last_name="Brown",
        email="michael@fittrack.com",
        username="michaelbrown",
        role="administrator",
    )
    admin.set_password("password123")

    trainer1 = User(
        first_name="Daniel",
        last_name="Carter",
        email="daniel@fittrack.com",
        username="danielcarter",
        role="pt",
        approved=True,
    )
    trainer1.set_password("password123")

    trainer2 = User(
        first_name="Amanda",
        last_name="Clark",
        email="amanda@fittrack.com",
        username="amandaclark",
        role="pt",
        approved=True,
    )
    trainer2.set_password("password123")

    trainer3 = User(
        first_name="Sarah",
        last_name="Johnson",
        email="sarah@fittrack.com",
        username="sarahjohnson",
        role="pt",
        approved=False,
    )
    trainer3.set_password("password123")

    trainer4 = User(
        first_name="David",
        last_name="Lee",
        email="david@fittrack.com",
        username="davidlee",
        role="pt",
        approved=False,
    )
    trainer4.set_password("password123")

    user1 = User(
        first_name="Noor",
        last_name="Hassan",
        email="noor@gmail.com",
        username="noorhassan",
        role="customer",
    )
    user1.set_password("password123")

    user2 = User(
        first_name="James",
        last_name="Mitchell",
        email="james@gmail.com",
        username="jamesmitchell",
        role="customer",
    )
    user2.set_password("password123")

    current_user = User(
        first_name="Ahmed",
        last_name="Ali",
        email="ahmed@fittrack.com",
        username="ahmed",
        role="customer",
    )
    current_user.set_password("password123")

    db.session.add_all(
        [admin, trainer1, trainer2, trainer3, trainer4, user1, user2, current_user]
    )
    db.session.flush()

    # ---- Training Clients ----
    tc1 = TrainingClient(
        trainer_id=trainer1.user_id, client_id=current_user.user_id, active=True
    )
    tc2 = TrainingClient(
        trainer_id=trainer2.user_id, client_id=user1.user_id, active=True
    )
    db.session.add_all([tc1, tc2])

    # ---- Training Plans ----
    today = date.today()
    plan1 = TrainingPlan(
        user_id=current_user.user_id,
        name="Spring Fitness Plan",
        start_date=today,
        end_date=today + timedelta(weeks=8),
    )
    db.session.add(plan1)
    db.session.flush()

    # ---- Planned Workouts ----
    pw1 = PlannedWorkout(
        plan_id=plan1.plan_id,
        exercise_type_id=running.exercise_type_id,
        planned_date=today + timedelta(days=1),
        target_duration=30,
        target_distance=5.0,
    )
    pw2 = PlannedWorkout(
        plan_id=plan1.plan_id,
        exercise_type_id=cycling.exercise_type_id,
        planned_date=today + timedelta(days=3),
        target_duration=45,
        target_distance=15.0,
    )
    pw3 = PlannedWorkout(
        plan_id=plan1.plan_id,
        exercise_type_id=strength.exercise_type_id,
        planned_date=today + timedelta(days=5),
        target_duration=60,
        target_distance=0.0,
    )
    db.session.add_all([pw1, pw2, pw3])

    # ---- Activities ----
    act1 = Activity(
        user_id=current_user.user_id,
        exercise_type_id=walking.exercise_type_id,
        date=today,
        duration_minutes=60,
        distance_km=4.5,
        calories=220,
        notes="Morning walk in the park",
    )
    act2 = Activity(
        user_id=current_user.user_id,
        exercise_type_id=running.exercise_type_id,
        date=today,
        duration_minutes=30,
        distance_km=5.0,
        calories=350,
        notes="Interval training",
    )
    act3 = Activity(
        user_id=current_user.user_id,
        exercise_type_id=cycling.exercise_type_id,
        date=today - timedelta(days=1),
        duration_minutes=45,
        distance_km=15.0,
        calories=400,
        notes="Evening cycle ride",
    )
    act4 = Activity(
        user_id=current_user.user_id,
        exercise_type_id=strength.exercise_type_id,
        date=today - timedelta(days=2),
        duration_minutes=50,
        distance_km=0.0,
        calories=280,
        notes="Upper body session",
    )

    act5 = Activity(
        user_id=user2.user_id,
        exercise_type_id=running.exercise_type_id,
        date=today,
        duration_minutes=60,
        distance_km=10.0,
        calories=650,
        notes="Long distance run",
    )
    act6 = Activity(
        user_id=user2.user_id,
        exercise_type_id=strength.exercise_type_id,
        date=today,
        duration_minutes=75,
        distance_km=0.0,
        calories=420,
        notes="Full body workout",
    )
    act7 = Activity(
        user_id=user2.user_id,
        exercise_type_id=cycling.exercise_type_id,
        date=today - timedelta(days=1),
        duration_minutes=90,
        distance_km=30.0,
        calories=700,
        notes="Road cycling session",
    )
    act8 = Activity(
        user_id=user2.user_id,
        exercise_type_id=swimming.exercise_type_id,
        date=today - timedelta(days=2),
        duration_minutes=45,
        distance_km=2.0,
        calories=350,
        notes="Laps at the pool",
    )
    act9 = Activity(
        user_id=user2.user_id,
        exercise_type_id=running.exercise_type_id,
        date=today - timedelta(days=3),
        duration_minutes=35,
        distance_km=6.0,
        calories=420,
        notes="Tempo run",
    )

    act10 = Activity(
        user_id=user1.user_id,
        exercise_type_id=walking.exercise_type_id,
        date=today,
        duration_minutes=30,
        distance_km=2.0,
        calories=100,
        notes="Walk around the neighbourhood",
    )
    act11 = Activity(
        user_id=user1.user_id,
        exercise_type_id=walking.exercise_type_id,
        date=today - timedelta(days=2),
        duration_minutes=40,
        distance_km=3.0,
        calories=130,
        notes="Evening walk with family",
    )
    act12 = Activity(
        user_id=user1.user_id,
        exercise_type_id=swimming.exercise_type_id,
        date=today - timedelta(days=4),
        duration_minutes=25,
        distance_km=0.8,
        calories=180,
        notes="Gentle swim session",
    )

    db.session.add_all(
        [act1, act2, act3, act4, act5, act6, act7, act8, act9, act10, act11, act12]
    )

    # ---- Competitions ----
    comp1 = Competition(
        name="City Marathon",
        location="City Centre",
        date=today + timedelta(days=20),
        distance=42.195,
    )
    comp2 = Competition(
        name="Spring Cycling Race",
        location="Countryside Road",
        date=today + timedelta(days=40),
        distance=80.0,
    )
    comp3 = Competition(
        name="Open Water Swim",
        location="Lake Park",
        date=today + timedelta(days=60),
        distance=3.0,
    )
    db.session.add_all([comp1, comp2, comp3])
    db.session.flush()

    # ---- Competition Results ----
    res1 = CompetitionResult(
        user_id=user1.user_id,
        competition_id=comp1.competition_id,
        finish_time="3:45:12",
        position=42,
        personal_best=True,
    )
    db.session.add(res1)

    # ---- Chat Messages ----
    now = datetime.utcnow()
    msg1 = ChatMessage(
        competition_id=comp1.competition_id,
        user_id=current_user.user_id,
        content="Hey everyone! Who else is training for the marathon?",
        timestamp=now - timedelta(hours=5),
    )
    msg2 = ChatMessage(
        competition_id=comp1.competition_id,
        user_id=user2.user_id,
        content="I am! Just finished a 20k long run today",
        timestamp=now - timedelta(hours=4, minutes=45),
    )
    msg3 = ChatMessage(
        competition_id=comp1.competition_id,
        user_id=user1.user_id,
        content="Good luck to everyone! I will be cheering from the sidelines",
        timestamp=now - timedelta(hours=3),
    )
    msg4 = ChatMessage(
        competition_id=comp1.competition_id,
        user_id=current_user.user_id,
        content="Thanks Noor! James what pace are you aiming for?",
        timestamp=now - timedelta(hours=2, minutes=30),
    )
    msg5 = ChatMessage(
        competition_id=comp1.competition_id,
        user_id=user2.user_id,
        content="Hoping for under 3:30, been pushing hard in training",
        timestamp=now - timedelta(hours=2),
    )
    db.session.add_all([msg1, msg2, msg3, msg4, msg5])

    db.session.commit()
