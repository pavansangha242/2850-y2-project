"""Gym activity routes for the Motivara application.

Handles logging gym workouts, seeding default exercises,

assigning exercises to clients, and displaying weekly gym stats.
"""

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import (
    GymAssignment,
    GymExercise,
    GymWorkout,
    SessionBooking,
    User,
)

gym_bp = Blueprint("gym", __name__)


def get_logged_in_user():
    """Returns the current logged-in user object, or None if no one is logged in."""
    username = session.get("username")

    if not username:
        return None

    return User.query.filter_by(username=username).first()


def ensure_default_gym_exercises():
    """Seeds the database with a default list of gym exercises."""
    if GymExercise.query.first():
        return

    gym_exercises = [
        GymExercise(
            name="Bench Press",
            muscle_group="Chest",
            description="Flat barbell bench press",
            video_url="https://www.youtube.com/watch?v=sYV-ki-1blM",
        ),
        GymExercise(
            name="Incline Dumbbell Press",
            muscle_group="Chest",
            description="Incline bench with dumbbells",
            video_url="https://www.youtube.com/embed/8iPEnn-ltC8",
        ),
        GymExercise(
            name="Cable Fly",
            muscle_group="Chest",
            description="Cable crossover fly",
            video_url="https://www.youtube.com/embed/WEM9FCIPlxQ",
        ),
        GymExercise(
            name="Lat Pulldown",
            muscle_group="Back",
            description="Wide grip lat pulldown",
            video_url="https://www.youtube.com/embed/CAwf7n6Luuc",
        ),
        GymExercise(
            name="Seated Row",
            muscle_group="Back",
            description="Cable seated row",
            video_url="https://www.youtube.com/embed/GZbfZ033f74",
        ),
        GymExercise(
            name="Deadlift",
            muscle_group="Back",
            description="Conventional barbell deadlift",
            video_url="https://www.youtube.com/embed/op9kVnSso6Q",
        ),
        GymExercise(
            name="Squat",
            muscle_group="Legs",
            description="Barbell back squat",
            video_url="https://www.youtube.com/embed/ultWZbUMPL8",
        ),
        GymExercise(
            name="Leg Press",
            muscle_group="Legs",
            description="Machine leg press",
            video_url="https://www.youtube.com/embed/IZxyjW7MPJQ",
        ),
        GymExercise(
            name="Leg Curl",
            muscle_group="Legs",
            description="Lying leg curl machine",
            video_url="https://www.youtube.com/embed/1Tq3QdYUuHs",
        ),
        GymExercise(
            name="Calf Raise",
            muscle_group="Legs",
            description="Standing calf raises",
            video_url="https://www.youtube.com/embed/-M4-G8p8fmc",
        ),
        GymExercise(
            name="Shoulder Press",
            muscle_group="Shoulders",
            description="Dumbbell overhead press",
            video_url="https://www.youtube.com/embed/qEwKCR5JCog",
        ),
        GymExercise(
            name="Lateral Raise",
            muscle_group="Shoulders",
            description="Dumbbell lateral raises",
            video_url="https://www.youtube.com/embed/3VcKaXpzqRo",
        ),
        GymExercise(
            name="Bicep Curl",
            muscle_group="Arms",
            description="Dumbbell bicep curls",
            video_url="https://www.youtube.com/embed/ykJmrZ5v0Oo",
        ),
        GymExercise(
            name="Tricep Pushdown",
            muscle_group="Arms",
            description="Cable tricep pushdown",
            video_url="https://www.youtube.com/embed/2-LAMcpzODU",
        ),
        GymExercise(
            name="Plank",
            muscle_group="Core",
            description="Front plank hold",
            video_url="https://www.youtube.com/embed/ASdvN_XEl_c",
        ),
        GymExercise(
            name="Cable Crunch",
            muscle_group="Core",
            description="Kneeling cable crunch",
            video_url="https://www.youtube.com/embed/AV5PmSFYMhI",
        ),
    ]

    db.session.add_all(gym_exercises)
    db.session.commit()


#  get the monday of this week
def get_week_start():
    """Returns the date of this week's Monday."""
    today = date.today()
    # monday is 0
    return today - timedelta(days=today.weekday())


@gym_bp.route("/gym")
def gym_page():
    """Loads everything needed for the main gym dashboard.

    Redirects to login if the user isn't logged in.
    """
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    ensure_default_gym_exercises()
    # get the user who is logged in
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))
    monday = get_week_start()

    # all the exer sorted by muscle group then name
    all_exercises = GymExercise.query.order_by(
        GymExercise.muscle_group, GymExercise.name
    ).all()

    # list of different muscle groups
    m_groups = (
        db.session.query(GymExercise.muscle_group)
        .distinct()
        .order_by(GymExercise.muscle_group)
        .all()
    )
    # list
    m_groups = [g[0] for g in m_groups]

    # get all the assignments the useer given by a trainer
    rows1 = (
        db.session.query(GymAssignment, GymExercise, User)
        .join(GymExercise, GymAssignment.gym_exercise_id == GymExercise.gym_exercise_id)
        .join(User, GymAssignment.trainer_id == User.user_id)
        .filter(GymAssignment.client_id == user.user_id)
        .order_by(GymAssignment.date_assigned.desc())
        .all()
    )

    # put extra info onto each assignment so the template can show it
    my_assignments = []
    for a, ex, trainer in rows1:
        a.exercise_name = ex.name
        a.muscle_group = ex.muscle_group
        a.trainer_name = f"{trainer.first_name} {trainer.last_name}"
        my_assignments.append(a)

    # the workouts user done
    rows2 = (
        db.session.query(GymWorkout, GymExercise)
        .join(GymExercise, GymWorkout.gym_exercise_id == GymExercise.gym_exercise_id)
        .filter(GymWorkout.user_id == user.user_id)
        .order_by(GymWorkout.date.desc(), GymWorkout.gym_workout_id.desc())
        .all()
    )

    # add the exers name/ muscle type to each workout
    my_workouts = []
    for w, ex in rows2:
        w.exercise_name = ex.name
        w.muscle_group = ex.muscle_group
        my_workouts.append(w)

    # count how many different days the user went to g
    gym_days = (
        db.session.query(func.count(func.distinct(GymWorkout.date)))
        .filter(GymWorkout.user_id == user.user_id, GymWorkout.date >= monday)
        .scalar()
        or 0
    )

    # add all sets
    sets_week = (
        db.session.query(func.coalesce(func.sum(GymWorkout.sets_completed), 0))
        .filter(GymWorkout.user_id == user.user_id, GymWorkout.date >= monday)
        .scalar()
        or 0
    )

    # muscle type user worked the most this week
    best_muscle = (
        db.session.query(
            GymExercise.muscle_group, func.count(GymWorkout.gym_workout_id)
        )
        .join(GymWorkout, GymWorkout.gym_exercise_id == GymExercise.gym_exercise_id)
        .filter(GymWorkout.user_id == user.user_id, GymWorkout.date >= monday)
        .group_by(GymExercise.muscle_group)
        .order_by(func.count(GymWorkout.gym_workout_id).desc())
        .first()
    )

    # none if nthing
    best_muscle_name = best_muscle[0] if best_muscle else "None yet"
    clients = []

    if user.role == "pt":
        clients = (
            User.query.join(SessionBooking, SessionBooking.client_id == User.user_id)
            .filter(
                SessionBooking.trainer_id == user.user_id,
                SessionBooking.status == "confirmed",
            )
            .distinct()
            .order_by(User.username.asc())
            .all()
        )

    # send everything to the html page
    return render_template(
        "gym.html",
        user=user,
        clients=clients,
        exercises=all_exercises,
        muscle_groups=m_groups,
        assignments=my_assignments,
        workouts=my_workouts,
        sessions_this_week=gym_days,
        total_sets_week=sets_week,
        top_muscle_name=best_muscle_name,
    )


@gym_bp.route("/gym/log", methods=["POST"])
def log_gym_workout():
    """Saves a new gym workout when the user submits the log form.

    Redirects back to the dashboard with a success message once saved.
    """
    # loged in user
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    # form
    w_date = request.form.get("date")
    ex_id = request.form.get("gym_exercise_id", type=int)
    a_id = request.form.get("assignment_id", type=int)
    sets_done = request.form.get("sets_completed", type=int)
    reps_done = request.form.get("reps_completed", type=int)
    kg = request.form.get("weight_kg", type=float)
    mins = request.form.get("duration", type=int)
    note = request.form.get("notes")

    # error if they didnt choose
    if not ex_id:
        flash("Please choose an exercise.", "error")
        return redirect(url_for("gym.gym_page"))

    # new workoutt/ save it
    new_workout = GymWorkout(
        user_id=user.user_id,
        gym_exercise_id=ex_id,
        assignment_id=a_id,
        date=date.fromisoformat(w_date) if w_date else date.today(),
        sets_completed=sets_done or 0,
        reps_completed=reps_done or 0,
        weight_kg=kg or 0.0,
        duration_minutes=mins or 0,
        notes=note or "",
    )

    db.session.add(new_workout)
    db.session.commit()

    flash("Gym workout logged!", "success")
    return redirect(url_for("gym.gym_page"))


@gym_bp.route("/gym/assign", methods=["POST"])
def assign_exercise():
    """Lets a PT assign a specific exercise to one of their clients with sets, reps and weight.

    Redirects back to the gym page once the assignment is saved.
    """
    # the trainer
    trainer = get_logged_in_user()

    if not trainer:
        return redirect(url_for("auth.login"))

    if trainer.role != "pt":
        flash("Only trainers can assign exercises.", "error")
        return redirect(url_for("gym.gym_page"))

    # get the form data
    c_id = request.form.get("client_id", type=int)
    ex_id = request.form.get("gym_exercise_id", type=int)
    client = User.query.filter_by(user_id=c_id, role="customer").first()

    if not client:
        flash("Client was not found.", "error")
        return redirect(url_for("gym.gym_page"))

    num_sets = request.form.get("sets", type=int)
    num_reps = request.form.get("reps", type=int)
    kg = request.form.get("weight_kg", type=float)
    note = request.form.get("notes")

    # they have to choose one clint or error
    if not c_id or not ex_id:
        flash("Client and exercise are required.", "error")
        return redirect(url_for("gym.gym_page"))

    # make assignment
    new_assign = GymAssignment(
        trainer_id=trainer.user_id,
        client_id=c_id,
        gym_exercise_id=ex_id,
        sets=num_sets or 0,
        reps=num_reps or 0,
        weight_kg=kg or 0.0,
        notes=note or "",
        date_assigned=date.today(),
    )

    db.session.add(new_assign)
    db.session.commit()

    flash("Exercise assigned!", "success")
    return redirect(url_for("gym.gym_page"))


@gym_bp.route("/gym/delete/<int:gym_workout_id>", methods=["POST"])
def delete_gym_workout(gym_workout_id):
    """Deletes a workout, but only if it actually belongs to the user.

    Redirects back to the dashboard with a confirmation message once deleted.
    """
    # find the user
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    # find workout only if itss to user
    w = GymWorkout.query.filter_by(
        gym_workout_id=gym_workout_id, user_id=user.user_id
    ).first_or_404()

    # delete it
    db.session.delete(w)
    db.session.commit()

    flash("Workout deleted.", "success")
    return redirect(url_for("gym.gym_page"))
