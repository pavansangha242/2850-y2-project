from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import ( Activity, TrainingPlan, UserGoal,
    get_current_user_id, get_exercise_type_id, get_user_weight )

swimming_bp = Blueprint('swimming', __name__)


#get swim type id
def get_swimming_type_id():
    return get_exercise_type_id('Swimming')


#monday of this wk
def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


#work out met for swim based on pace
def get_swimming_met(distance_km, duration_mins):
    if distance_km and duration_mins and distance_km > 0 and duration_mins > 0:
        #convert to m and secs
        metres = distance_km * 1000
        secs = duration_mins * 60
        #pace = secs per 100m
        pace_100 = (secs / metres) * 100

        #faster pace -less secs =higheer met
        if pace_100 < 90:
            return 10.0
        elif pace_100 < 120:
            return 8.0
        elif pace_100 < 150:
            return 6.0
        else:
            return 4.5

    #default
    return 6.0


#cals = met x weight x hrs
def calculate_calories(met, weight_kg, duration_mins):
    if weight_kg and duration_mins and weight_kg > 0 and duration_mins > 0:
        hrs = duration_mins / 60
        return round(met * weight_kg * hrs)
    return None


@swimming_bp.route('/swimming')
def swimming_page():
    uid = get_current_user_id()
    sw_type = get_swimming_type_id()
    monday = get_week_start()

    #empty page if swim not in db
    if not sw_type:
        flash('Swimming exercise type was not found.', 'error')
        return render_template(
            'swimming.html',
            activities=[],
            swims_this_week=0,
            total_laps_week=0,
            swims_500m=0,
            swims_1km=0,
            swims_2km=0,
            swims_5km=0,
            training_plan=None,
            swimming_goal=None,
            streak=0,
            pace_progress=0,
            workouts_target=4
        )

    #get all swims
    all_swims = Activity.query.filter_by(
        user_id=uid,
        exercise_type_id=sw_type
    ).order_by(Activity.date.desc(), Activity.activity_id.desc()).all()

    #swims this wk
    swims_week = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.date >= monday
        ).scalar() or 0

    #total laps this wk
    laps_week = db.session.query(func.coalesce(func.sum(Activity.laps), 0))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.date >= monday
        ).scalar() or 0

    #short swim up to 500m
    tiny_swims = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.distance_km > 0,
            Activity.distance_km <= 0.5
        ).scalar() or 0

    #500m-1km swims
    short_swims = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.distance_km > 0.5,
            Activity.distance_km <= 1.0
        ).scalar() or 0

    #1-2km swims
    med_swims = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.distance_km > 1.0,
            Activity.distance_km <= 2.0
        ).scalar() or 0

    #long swim over 2km
    long_swims = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.distance_km > 2.0
        ).scalar() or 0

    #swim plan
    plan = TrainingPlan.query.filter(
        TrainingPlan.user_id == uid,
        TrainingPlan.name.like('%Swimming%')
    ).order_by(TrainingPlan.plan_id.desc()).first()

    #swim goal
    goal = UserGoal.query.filter(
        UserGoal.user_id == uid,
        UserGoal.goal_type.like('%swim%')
    ).order_by(UserGoal.id.desc()).first()

    #streak
    s = 0
    all_dates = db.session.query(Activity.date)\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type
        )\
        .distinct()\
        .order_by(Activity.date.desc())\
        .all()

    if all_dates:
        checking = date.today()
        for row in all_dates:
            swim_day = row[0]

            #swam today start streak
            if swim_day == checking:
                s += 1
                checking = checking - timedelta(days=1)
            #swam yestday streak continues
            elif swim_day == checking - timedelta(days=1):
                s += 1
                checking = swim_day - timedelta(days=1)
            else:
                #streak broke
                break

    #avg pace this wk
    pace_now = db.session.query(func.avg(Activity.pace_per_100m))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.date >= monday,
            Activity.pace_per_100m > 0
        ).scalar()

    #avg pace last wk
    last_monday = monday - timedelta(days=7)
    pace_before = db.session.query(func.avg(Activity.pace_per_100m))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == sw_type,
            Activity.date >= last_monday,
            Activity.date < monday,
            Activity.pace_per_100m > 0
        ).scalar()


    progress = 0
    if pace_now and pace_before and pace_before > 0:
        progress = round(
            ((pace_before - pace_now) / pace_before) * 100
        )

    #target swims per wk
    target = 4
    if goal and goal.workouts_per_week_target:
        target = goal.workouts_per_week_target

    return render_template(
        'swimming.html',
        activities=all_swims,
        swims_this_week=swims_week,
        total_laps_week=laps_week,
        swims_500m=tiny_swims,
        swims_1km=short_swims,
        swims_2km=med_swims,
        swims_5km=long_swims,
        training_plan=plan,
        swimming_goal=goal,
        streak=s,
        pace_progress=progress,
        workouts_target=target
    )


@swimming_bp.route('/swimming/log', methods=['POST'])
def log_swim():
    uid = get_current_user_id()
    sw_type = get_swimming_type_id()

    if not sw_type:
        flash('Swimming exercise type was not found.', 'error')
        return redirect(url_for('swimming.swimming_page'))

    #form
    d = request.form.get('date')
    dist = request.form.get('distance')
    dur = request.form.get('duration')
    laps = request.form.get('laps')
    stroke = request.form.get('stroke_type')
    cals = request.form.get('calories')
    note = request.form.get('notes')

    kg = get_user_weight(uid)

    dist_num = None
    dur_num = None
    pace_100 = None

    #convert nums
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
    laps_num = 0
    if laps:
        try:
            laps_num = int(laps)
        except ValueError:
            laps_num = 0

    # If distance is blank, estimate it from laps.
    # Assumes 25m pool: 1 lap = 25m = 0.025 km
    if (not dist_num or dist_num <= 0) and laps_num > 0:
        dist_num = laps_num * 0.025

    #pace per 100m
    if dist_num and dur_num and dist_num > 0:
        metres = dist_num * 1000
        secs = dur_num * 60
        pace_100 = round((secs / metres) * 100, 1)

    #cals
    final_cals = None
    if cals:
        try:
            final_cals = int(cals)
        except ValueError:
            final_cals = None

    if final_cals is None and dur_num:
        # Use saved user weight if available, otherwise use a default estimate
        weight = kg if kg and kg > 0 else 70

        met = get_swimming_met(dist_num, dur_num)
        final_cals = calculate_calories(met, weight, dur_num)

    #save
    new_swim = Activity(
        user_id=uid,
        exercise_type_id=sw_type,
        date=date.fromisoformat(d) if d else date.today(),
        duration_minutes=dur_num or 0,
        distance_km=dist_num or 0.0,
        laps=laps_num,
        pace_per_100m=pace_100 or 0.0,
        stroke_type=stroke or '',
        calories=final_cals or 0,
        notes=note or ''
    )

    db.session.add(new_swim)
    db.session.commit()

    flash('Swim logged successfully!', 'success')
    return redirect(url_for('swimming.swimming_page'))


@swimming_bp.route('/swimming/plan', methods=['POST'])
def create_swimming_plan():
    uid = get_current_user_id()

    per_week = request.form.get('swims_per_week', type=int)
    weekly_km = request.form.get('weekly_distance', type=float)
    t_pace = request.form.get('target_pace')

    #existing plan?
    plan = TrainingPlan.query.filter(
        TrainingPlan.user_id == uid,
        TrainingPlan.name.like('%Swimming%')
    ).order_by(TrainingPlan.plan_id.desc()).first()

    #update or new
    if plan:
        plan.start_date = date.today()
        plan.end_date = date.today() + timedelta(weeks=8)
        plan.swims_per_week = per_week or 0
        plan.weekly_distance = weekly_km or 0.0
        plan.target_pace = t_pace or ''
    else:
        plan = TrainingPlan(
            user_id=uid,
            name='Swimming Plan',
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=8),
            swims_per_week=per_week or 0,
            weekly_distance=weekly_km or 0.0,
            target_pace=t_pace or ''
        )
        db.session.add(plan)

    db.session.commit()

    flash('Swimming plan saved!', 'success')
    return redirect(url_for('swimming.swimming_page'))


@swimming_bp.route('/swimming/goal', methods=['POST'])
def set_swimming_goal():
    uid = get_current_user_id()

    g_type = request.form.get('goal_type')
    t_date = request.form.get('target_date')
    per_week = request.form.get('workouts_per_week', type=int)

    #existing goal
    goal = UserGoal.query.filter(
        UserGoal.user_id == uid,
        UserGoal.goal_type.like('%swim%')
    ).order_by(UserGoal.id.desc()).first()

    #goal string
    full_type = f'{g_type} swim' if g_type else 'general swim'
    full_date = date.fromisoformat(t_date) if t_date else None

    #update/make
    if goal:
        goal.goal_type = full_type
        goal.target_date = full_date
        goal.workouts_per_week_target = per_week or 4
    else:
        goal = UserGoal(
            user_id=uid,
            goal_type=full_type,
            target_date=full_date,
            workouts_per_week_target=per_week or 4
        )
        db.session.add(goal)

    db.session.commit()

    flash('Swimming goal set!', 'success')
    return redirect(url_for('swimming.swimming_page'))


@swimming_bp.route('/swimming/delete/<int:activity_id>', methods=['POST'])
def delete_swim(activity_id):
    uid = get_current_user_id()

    #only del if belongs to user
    sw = Activity.query.filter_by(
        activity_id=activity_id,
        user_id=uid,
        exercise_type_id=get_swimming_type_id()
    ).first_or_404()

    db.session.delete(sw)
    db.session.commit()

    flash('Swim deleted.', 'success')
    return redirect(url_for('swimming.swimming_page'))
