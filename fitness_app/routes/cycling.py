from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import (
    Activity,
    TrainingPlan,
    UserGoal,
    get_current_user_id,
    get_exercise_type_id,
    get_user_weight,
)

cycling_bp = Blueprint("cycling", __name__)


def get_cycling_type_id():
    """Returns the database ID for the cycling exercise type."""
    return get_exercise_type_id("Cycling")


# monday of this week
def get_week_start():
    """Returns the date of this week's Monday."""
    today = date.today()
    return today - timedelta(days=today.weekday())


# work out met from speed
def get_cycling_met(speed_kmh):
    """Picks the right MET value based on how fast the user cycling.
    So MET is a measure of effort — faster riding means a higher MET and more which mean calories burned.
    Returns a number between 4.0 if easy and 12.0 for very fast."""    
    if speed_kmh and speed_kmh > 0:
        # faster = more cals
        if speed_kmh >= 30:
            return 12.0
        elif speed_kmh >= 25:
            return 10.0
        elif speed_kmh >= 19:
            return 8.0
        elif speed_kmh >= 15:
            return 6.0
        else:
            return 4.0
    # default if no speed
    return 6.0


# cals = met x weight x hrs
def calculate_calories(met, weight_kg, duration_mins):
    """Estimates calories burned using MET x weight x time in hours.
    Returns None if any of the inputs are missing or zero, otherwise returns a rounded whole number."""
    if weight_kg and duration_mins and weight_kg > 0 and duration_mins > 0:
        hrs = duration_mins / 60
        return round(met * weight_kg * hrs)
    return None


@cycling_bp.route("/cycling")
def cycling_page():
    """Loads everything needed for the main cycling dashboard.
    Pulls together ride history, weekly stats, streak, speed progress, training plan and goal.
    Redirects to login if the user isn't logged in, or shows an empty dashboard if cycling isn't in the database."""
    # user id / cyc type / monday
    if not session.get("username"):
        return redirect(url_for("auth.login"))

    uid = get_current_user_id()
    c_type = get_cycling_type_id()
    monday = get_week_start()

    # error if cycling not in in db
    if not c_type:
        flash("Cycling exercise type was not found.", "error")
        return render_template(
            "cycling.html",
            activities=[],
            rides_this_week=0,
            total_km_week=0,
            rides_10km=0,
            rides_25km=0,
            rides_50km=0,
            rides_100km=0,
            training_plan=None,
            cycling_goal=None,
            streak=0,
            speed_progress=0,
            workouts_target=5,
        )

    # all rides newest first
    all_rides = (
        Activity.query.filter_by(user_id=uid, exercise_type_id=c_type)
        .order_by(Activity.date.desc(), Activity.activity_id.desc())
        .all()
    )

    # rides this week
    rides_week = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.date >= monday,
        )
        .scalar()
        or 0
    )

    # total km this week
    km_week = (
        db.session.query(func.coalesce(func.sum(Activity.distance_km), 0))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.date >= monday,
        )
        .scalar()
        or 0
    )

    # short ride up to 10k
    short_rides = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.distance_km > 0,
            Activity.distance_km <= 10,
        )
        .scalar()
        or 0
    )

    # med ride 10-25
    med_rides = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.distance_km > 10,
            Activity.distance_km <= 25,
        )
        .scalar()
        or 0
    )

    # long ride 25-50km
    long_rides = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.distance_km > 25,
            Activity.distance_km <= 50,
        )
        .scalar()
        or 0
    )

    # really long one over 50
    xl_rides = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.distance_km > 50,
        )
        .scalar()
        or 0
    )

    # newest cyc plan for user
    plan = (
        TrainingPlan.query.filter(
            TrainingPlan.user_id == uid, TrainingPlan.name.like("%Cycling%")
        )
        .order_by(TrainingPlan.plan_id.desc())
        .first()
    )

    # newest cyc goal
    goal = (
        UserGoal.query.filter(
            UserGoal.user_id == uid, UserGoal.goal_type.like("%cycle%")
        )
        .order_by(UserGoal.id.desc())
        .first()
    )

    # streak
    s = 0
    all_dates = (
        db.session.query(Activity.date)
        .filter(Activity.user_id == uid, Activity.exercise_type_id == c_type)
        .distinct()
        .order_by(Activity.date.desc())
        .all()
    )

    # loop dates count in row
    if all_dates:
        checking = date.today()
        for row in all_dates:
            ride_day = row[0]

            # rode today = start streak
            if ride_day == checking:
                s += 1
                checking = checking - timedelta(days=1)
            # rode yestday streak continues
            elif ride_day == checking - timedelta(days=1):
                s += 1
                checking = ride_day - timedelta(days=1)
            else:
                # streak broke stop
                break

    # avg speed this week
    speed_now = (
        db.session.query(func.avg(Activity.average_speed_kmh))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.date >= monday,
            Activity.average_speed_kmh > 0,
        )
        .scalar()
    )

    # avg speed last week to cmpare
    last_monday = monday - timedelta(days=7)
    speed_before = (
        db.session.query(func.avg(Activity.average_speed_kmh))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == c_type,
            Activity.date >= last_monday,
            Activity.date < monday,
            Activity.average_speed_kmh > 0,
        )
        .scalar()
    )

    # % change from last week
    progress = 0
    if speed_now and speed_before and speed_before > 0:
        progress = round(((speed_now - speed_before) / speed_before) * 100)

    # default if no goal
    target = 5
    if goal and goal.workouts_per_week_target:
        target = goal.workouts_per_week_target

    return render_template(
        "cycling.html",
        activities=all_rides,
        rides_this_week=rides_week,
        total_km_week=km_week,
        rides_10km=short_rides,
        rides_25km=med_rides,
        rides_50km=long_rides,
        rides_100km=xl_rides,
        training_plan=plan,
        cycling_goal=goal,
        streak=s,
        speed_progress=progress,
        workouts_target=target,
    )


@cycling_bp.route("/cycling/log", methods=["POST"])
def log_ride():
    """Saves a new ride when the user submits the log form.
    Auto-calculates speed and calories if the user left those fields blank.
    Redirects back to the dashboard with a success message once saved."""
    uid = get_current_user_id()
    c_type = get_cycling_type_id()

    # stop if cyc not in db
    if not c_type:
        flash("Cycling exercise type was not found.", "error")
        return redirect(url_for("cycling.cycling_page"))

    # form
    d = request.form.get("date")
    dist = request.form.get("distance")
    dur = request.form.get("duration")
    av_speed = request.form.get("average_speed")
    cals = request.form.get("calories")
    note = request.form.get("notes")

    # weight for cals
    kg = get_user_weight(uid)

    # turn dist / dur to nums
    dist_num = None
    dur_num = None

    if dist:
        try:
            dist_num = float(dist)
        except ValueError:
            # not a num set none
            dist_num = None

    if dur:
        try:
            dur_num = int(dur)
        except ValueError:
            dur_num = None

    # if user typed speed use it else wrk out
    final_speed = None
    if av_speed:
        try:
            final_speed = float(av_speed)
        except ValueError:
            final_speed = None
    elif dist_num and dur_num and dur_num > 0:
        # speed = dist/time
        hrs = dur_num / 60
        final_speed = round(dist_num / hrs, 1)

    # same for cals
    final_cals = None
    if cals:
        try:
            final_cals = int(cals)
        except ValueError:
            final_cals = None

    # no cals yet? work out w met
    if final_cals is None and dur_num:
        # Use saved user weight if available, otherwise use a default estimate
        weight = kg if kg and kg > 0 else 70

        met = get_cycling_met(final_speed)
        final_cals = calculate_calories(met, weight, dur_num)

    # new activity save
    new_ride = Activity(
        user_id=uid,
        exercise_type_id=c_type,
        date=date.fromisoformat(d) if d else date.today(),
        duration_minutes=dur_num or 0,
        distance_km=dist_num or 0.0,
        average_speed_kmh=final_speed or 0.0,
        calories=final_cals or 0,
        notes=note or "",
    )

    db.session.add(new_ride)
    db.session.commit()

    flash("Ride logged successfully!", "success")
    return redirect(url_for("cycling.cycling_page"))


@cycling_bp.route("/cycling/plan", methods=["POST"])
def create_cycling_plan():
    """Creates a cycling training plan, or updates the existing one if the user already has one. Redirects back to the dashboard once saved."""
    uid = get_current_user_id()

    # plan from form
    per_week = request.form.get("rides_per_week", type=int)
    weekly_km = request.form.get("weekly_distance", type=float)
    t_speed = request.form.get("target_speed")

    # check if alrdy got a plan
    plan = (
        TrainingPlan.query.filter(
            TrainingPlan.user_id == uid, TrainingPlan.name.like("%Cycling%")
        )
        .order_by(TrainingPlan.plan_id.desc())
        .first()
    )

    # update or make new
    if plan:
        plan.start_date = date.today()
        plan.end_date = date.today() + timedelta(weeks=8)
        plan.swims_per_week = per_week or 0
        plan.weekly_distance = weekly_km or 0.0
        plan.target_pace = t_speed or ""
    else:
        plan = TrainingPlan(
            user_id=uid,
            name="Cycling Plan",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=8),
            swims_per_week=per_week or 0,
            weekly_distance=weekly_km or 0.0,
            target_pace=t_speed or "",
        )
        db.session.add(plan)

    db.session.commit()

    flash("Cycling plan saved!", "success")
    return redirect(url_for("cycling.cycling_page"))


@cycling_bp.route("/cycling/goal", methods=["POST"])
def set_cycling_goal():
    """Saves the user's cycling goal, or updates it if they've set one before.
    Redirects back to the dashboard once done."""
    uid = get_current_user_id()

    # goal stuff from form
    g_type = request.form.get("goal_type")
    t_date = request.form.get("target_date")
    per_week = request.form.get("workouts_per_week", type=int)

    # existing goal
    goal = (
        UserGoal.query.filter(
            UserGoal.user_id == uid, UserGoal.goal_type.like("%cycle%")
        )
        .order_by(UserGoal.id.desc())
        .first()
    )

    #
    full_type = f"{g_type} cycle" if g_type else "general cycle"
    full_date = date.fromisoformat(t_date) if t_date else None

    # update or make new
    if goal:
        goal.goal_type = full_type
        goal.target_date = full_date
        goal.workouts_per_week_target = per_week or 5
    else:
        goal = UserGoal(
            user_id=uid,
            goal_type=full_type,
            target_date=full_date,
            workouts_per_week_target=per_week or 5,
        )
        db.session.add(goal)

    db.session.commit()

    flash("Cycling goal set!", "success")
    return redirect(url_for("cycling.cycling_page"))


@cycling_bp.route("/cycling/delete/<int:activity_id>", methods=["POST"])
def delete_ride(activity_id):
    """Deletes a ride, but only if it actually belongs to the logged-in user.
    Redirects back to the dashboard with a confirmation message once deleted."""
    uid = get_current_user_id()

    # only delete user own rides
    r = Activity.query.filter_by(
        activity_id=activity_id, user_id=uid, exercise_type_id=get_cycling_type_id()
    ).first_or_404()

    db.session.delete(r)
    db.session.commit()

    flash("Ride deleted.", "success")
    return redirect(url_for("cycling.cycling_page"))
