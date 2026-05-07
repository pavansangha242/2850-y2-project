"""Walking activity routes for the Motivara application.

Handles logging walks, tracking steps and distance,
calculating calories, and managing walking plans and goals.
"""
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
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

walking_bp = Blueprint("walking", __name__)


# walking type id
def get_walking_type_id():
    """Returns the database ID for the walking exercise type."""
    return get_exercise_type_id("Walking")


# monday this wk
def get_week_start():
    """Returns the date of this week's Monday."""
    today = date.today()
    return today - timedelta(days=today.weekday())


# met from walking speed
def get_walking_met(distance_km, duration_mins):
    """Picks the right MET value based on how fast the user was walking.
    
    Returns a number between 2.5 is slow and 7.0 power walk.
    """
    if distance_km and duration_mins and distance_km > 0 and duration_mins > 0:
        # speed = dist/time
        speed = distance_km / (duration_mins / 60)

        # faster walk = more cals burnt
        if speed >= 7.5:
            return 7.0
        elif speed >= 6.5:
            return 5.0
        elif speed >= 5.5:
            return 4.3
        elif speed >= 4:
            return 3.5
        else:
            return 2.5
    # default
    return 3.5


# cals = met x weight x hrs
def calculate_calories(met, weight_kg, duration_mins):
    """Estimates calories burned using MET x weight x time in hours.
    
    Returns None if any inputs are missing or zero, otherwise returns a rounded whole number.
    """
    if weight_kg and duration_mins and weight_kg > 0 and duration_mins > 0:
        hrs = duration_mins / 60
        return round(met * weight_kg * hrs)
    return None


@walking_bp.route("/walking")
def walking_page():
    """Loads everything needed for the main walking dashboard.

    Redirects to login if its not user.
    """
    if not session.get("username"):
        return redirect(url_for("auth.login"))

    uid = get_current_user_id()
    w_type = get_walking_type_id()
    monday = get_week_start()

    # empty page if walk not in db
    if not w_type:
        flash("Walking exercise type was not found.", "error")
        return render_template(
            "walking.html",
            activities=[],
            walks_this_week=0,
            total_steps_week=0,
            total_km_week=0,
            walks_1km=0,
            walks_3km=0,
            walks_5km=0,
            walks_10km=0,
            training_plan=None,
            walking_goal=None,
            streak=0,
            step_progress=0,
            workouts_target=5,
        )

    # all walks
    all_walks = (
        Activity.query.filter_by(user_id=uid, exercise_type_id=w_type)
        .order_by(Activity.date.desc(), Activity.activity_id.desc())
        .all()
    )

    # walks this wk
    walks_week = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.date >= monday,
        )
        .scalar()
        or 0
    )

    # total steps this wk
    steps_week = (
        db.session.query(func.coalesce(func.sum(Activity.steps), 0))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.date >= monday,
        )
        .scalar()
        or 0
    )

    # total km this wk
    km_week = (
        db.session.query(func.coalesce(func.sum(Activity.distance_km), 0))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.date >= monday,
        )
        .scalar()
        or 0
    )

    # short walk up to 1km
    tiny_walks = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.distance_km > 0,
            Activity.distance_km <= 1,
        )
        .scalar()
        or 0
    )

    # 1-3km walks
    short_walks = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.distance_km > 1,
            Activity.distance_km <= 3,
        )
        .scalar()
        or 0
    )

    # 3-5km walks
    med_walks = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.distance_km > 3,
            Activity.distance_km <= 5,
        )
        .scalar()
        or 0
    )

    # over 5km
    long_walks = (
        db.session.query(func.count(Activity.activity_id))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.distance_km > 5,
        )
        .scalar()
        or 0
    )

    # walk plan
    plan = (
        TrainingPlan.query.filter(
            TrainingPlan.user_id == uid, TrainingPlan.name.like("%Walking%")
        )
        .order_by(TrainingPlan.plan_id.desc())
        .first()
    )

    # walk goal
    goal = (
        UserGoal.query.filter(
            UserGoal.user_id == uid, UserGoal.goal_type.like("%walk%")
        )
        .order_by(UserGoal.id.desc())
        .first()
    )

    # streak
    s = 0
    all_dates = (
        db.session.query(Activity.date)
        .filter(Activity.user_id == uid, Activity.exercise_type_id == w_type)
        .distinct()
        .order_by(Activity.date.desc())
        .all()
    )

    if all_dates:
        checking = date.today()
        for row in all_dates:
            walk_day = row[0]

            # walked today
            if walk_day == checking:
                s += 1
                checking = checking - timedelta(days=1)
            # walked yestday
            elif walk_day == checking - timedelta(days=1):
                s += 1
                checking = walk_day - timedelta(days=1)
            else:
                # streak broke
                break

    # avg steps this wk
    steps_now = (
        db.session.query(func.avg(Activity.steps))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.date >= monday,
            Activity.steps > 0,
        )
        .scalar()
    )

    # avg steps last wk to cmpare
    last_monday = monday - timedelta(days=7)
    steps_before = (
        db.session.query(func.avg(Activity.steps))
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == w_type,
            Activity.date >= last_monday,
            Activity.date < monday,
            Activity.steps > 0,
        )
        .scalar()
    )

    # % change - higher is better normal maths
    progress = 0
    if steps_now and steps_before and steps_before > 0:
        progress = round(((steps_now - steps_before) / steps_before) * 100)

    # target walks per wk
    target = 5
    if goal and goal.workouts_per_week_target:
        target = goal.workouts_per_week_target

    return render_template(
        "walking.html",
        activities=all_walks,
        walks_this_week=walks_week,
        total_steps_week=steps_week,
        total_km_week=km_week,
        walks_1km=tiny_walks,
        walks_3km=short_walks,
        walks_5km=med_walks,
        walks_10km=long_walks,
        training_plan=plan,
        walking_goal=goal,
        streak=s,
        step_progress=progress,
        workouts_target=target,
    )


@walking_bp.route("/walking/log", methods=["POST"])
def log_walk():
    """Saves a new walk when the user submits the log form.
    
    Redirects back to the dashboard with a success message once saved.
    """
    uid = get_current_user_id()
    w_type = get_walking_type_id()

    if not w_type:
        flash("Walking exercise type was not found.", "error")
        return redirect(url_for("walking.walking_page"))

    # form
    d = request.form.get("date")
    dist = request.form.get("distance")
    dur = request.form.get("duration")
    stps = request.form.get("steps")
    cals = request.form.get("calories")
    note = request.form.get("notes")

    kg = get_user_weight(uid)

    dist_num = None
    dur_num = None

    # try convert safely
    if dist:
        try:
            dist_num = float(dist)
        except ValueError:
            dist_num = None

    if dur:
        try:
            dur_num = int(dur)
        except ValueError:
            dur_num = None

    # pace/secs per km
    pace = None
    if dist_num and dur_num and dist_num > 0:
        secs = dur_num * 60
        pace = round(secs / dist_num, 1)

    # cals typed or work out
    final_cals = None
    if cals:
        try:
            final_cals = int(cals)
        except ValueError:
            final_cals = None

    if final_cals is None and dur_num:
        # Use saved user weight if available, otherwise use a default estimate
        weight = kg if kg and kg > 0 else 70

        met = get_walking_met(dist_num, dur_num)
        final_cals = calculate_calories(met, weight, dur_num)

    # save walk
    new_walk = Activity(
        user_id=uid,
        exercise_type_id=w_type,
        date=date.fromisoformat(d) if d else date.today(),
        duration_minutes=dur_num or 0,
        distance_km=dist_num or 0.0,
        steps=int(stps) if stps else 0,
        pace_per_km=pace or 0.0,
        calories=final_cals or 0,
        notes=note or "",
    )

    db.session.add(new_walk)
    db.session.commit()

    flash("Walk logged successfully!", "success")
    return redirect(url_for("walking.walking_page"))


@walking_bp.route("/walking/plan", methods=["POST"])
def create_walking_plan():
    """Creates a walking training plan.
    
    Redirects back to the dashboard once saved.
    """
    uid = get_current_user_id()

    per_week = request.form.get("walks_per_week", type=int)
    weekly_km = request.form.get("weekly_distance", type=float)
    t_steps = request.form.get("target_steps")

    # already got a walk plan?
    plan = (
        TrainingPlan.query.filter(
            TrainingPlan.user_id == uid, TrainingPlan.name.like("%Walking%")
        )
        .order_by(TrainingPlan.plan_id.desc())
        .first()
    )

    # update or new
    if plan:
        plan.start_date = date.today()
        plan.end_date = date.today() + timedelta(weeks=8)
        plan.swims_per_week = per_week or 0
        plan.weekly_distance = weekly_km or 0.0
        plan.target_pace = t_steps or ""
    else:
        plan = TrainingPlan(
            user_id=uid,
            name="Walking Plan",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=8),
            swims_per_week=per_week or 0,
            weekly_distance=weekly_km or 0.0,
            target_pace=t_steps or "",
        )
        db.session.add(plan)

    db.session.commit()

    flash("Walking plan saved!", "success")
    return redirect(url_for("walking.walking_page"))


@walking_bp.route("/walking/goal", methods=["POST"])
def set_walking_goal():
    """Saves the user's walking goal.
    
    Redirects back to the dashboard once done.
    """
    uid = get_current_user_id()

    g_type = request.form.get("goal_type")
    t_date = request.form.get("target_date")
    per_week = request.form.get("workouts_per_week", type=int)
    step_goal = request.form.get("step_target", type=int)

    # existing walk goal
    goal = (
        UserGoal.query.filter(
            UserGoal.user_id == uid, UserGoal.goal_type.like("%walk%")
        )
        .order_by(UserGoal.id.desc())
        .first()
    )

    full_type = f"{g_type} walk" if g_type else "general walk"
    full_date = date.fromisoformat(t_date) if t_date else None

    # update or make new
    if goal:
        goal.goal_type = full_type
        goal.target_date = full_date
        goal.workouts_per_week_target = per_week or 5
        goal.step_target = step_goal or 0
    else:
        goal = UserGoal(
            user_id=uid,
            goal_type=full_type,
            target_date=full_date,
            workouts_per_week_target=per_week or 5,
            step_target=step_goal or 0,
        )
        db.session.add(goal)

    db.session.commit()

    flash("Walking goal set!", "success")
    return redirect(url_for("walking.walking_page"))


@walking_bp.route("/walking/delete/<int:activity_id>", methods=["POST"])
def delete_walk(activity_id):
    """Delete a walk.
    
    Redirects back to the dashboard with a confirmation message once deleted.
    """
    uid = get_current_user_id()

    # only del if belongs to user
    w = Activity.query.filter_by(
        activity_id=activity_id, user_id=uid, exercise_type_id=get_walking_type_id()
    ).first_or_404()

    db.session.delete(w)
    db.session.commit()

    flash("Walk deleted.", "success")
    return redirect(url_for("walking.walking_page"))
