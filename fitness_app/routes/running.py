from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import ( Activity, TrainingPlan, UserGoal, get_current_user_id,
    get_exercise_type_id, get_user_weight )

running_bp = Blueprint('running', __name__)


#get running type id
def get_running_type_id():
    return get_exercise_type_id('Running')


#monday of this week
def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


#work out met from run speed
def get_running_met(distance_km, duration_mins):
    if distance_km and duration_mins and distance_km > 0 and duration_mins > 0:
        #speed = dist/time
        speed = distance_km / (duration_mins / 60)

        #faster = higher MET = more cals
        if speed >= 16:
            return 14.5
        elif speed >= 13:
            return 11.5
        elif speed >= 10:
            return 9.8
        elif speed >= 8:
            return 8.0
        else:
            return 6.0
    #def
    return 9.8


#cals = met x weight x hrs
def calculate_calories(met, weight_kg, duration_mins):
    if weight_kg and duration_mins and weight_kg > 0 and duration_mins > 0:
        hrs = duration_mins / 60
        return round(met * weight_kg * hrs)
    return None


@running_bp.route('/running')
def running_page():
    uid = get_current_user_id()
    r_type = get_running_type_id()
    monday = get_week_start()


    if not r_type:
        flash('Running exercise type was not found.', 'error')
        return render_template(
            'running.html',
            activities=[],
            runs_this_week=0,
            total_km_week=0,
            runs_5k=0,
            runs_10k=0,
            runs_half=0,
            runs_marathon=0,
            training_plan=None,
            running_goal=None,
            streak=0,
            pace_progress=0,
            workouts_target=4
        )

    #all runs user has done
    all_runs = Activity.query.filter_by(
        user_id=uid,
        exercise_type_id=r_type
    ).order_by(Activity.date.desc(), Activity.activity_id.desc()).all()

    #runs this week
    runs_week = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.date >= monday
        ).scalar() or 0

    #total km this week
    km_week = db.session.query(func.coalesce(func.sum(Activity.distance_km), 0))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.date >= monday
        ).scalar() or 0

    #5k runs
    five_k = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.distance_km > 0,
            Activity.distance_km <= 5
        ).scalar() or 0

    #10k runs
    ten_k = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.distance_km > 5,
            Activity.distance_km <= 10
        ).scalar() or 0

    #half marathon
    half_m = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.distance_km > 10,
            Activity.distance_km <= 21.1
        ).scalar() or 0

    #full marathon more than 21.1
    full_m = db.session.query(func.count(Activity.activity_id))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.distance_km > 21.1
        ).scalar() or 0

    #run plan
    plan = TrainingPlan.query.filter(
        TrainingPlan.user_id == uid,
        TrainingPlan.name.like('%Running%')
    ).order_by(TrainingPlan.plan_id.desc()).first()

    #find the user run goal
    goal = UserGoal.query.filter(
        UserGoal.user_id == uid,
        UserGoal.goal_type.like('%run%')
    ).order_by(UserGoal.id.desc()).first()

    #streak
    s = 0
    all_dates = db.session.query(Activity.date)\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type
        )\
        .distinct()\
        .order_by(Activity.date.desc())\
        .all()

    if all_dates:
        checking = date.today()
        for row in all_dates:
            run_day = row[0]

            #ran today start streak
            if run_day == checking:
                s += 1
                checking = checking - timedelta(days=1)
            #ran yestday keep goin
            elif run_day == checking - timedelta(days=1):
                s += 1
                checking = run_day - timedelta(days=1)
            else:
                #streak broke
                break

    pace_now = db.session.query(func.avg(Activity.pace_per_km))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.date >= monday,
            Activity.pace_per_km > 0
        ).scalar()

    #avg pace last week
    last_monday = monday - timedelta(days=7)
    pace_before = db.session.query(func.avg(Activity.pace_per_km))\
        .filter(
            Activity.user_id == uid,
            Activity.exercise_type_id == r_type,
            Activity.date >= last_monday,
            Activity.date < monday,
            Activity.pace_per_km > 0
        ).scalar()

    #pace lower
    progress = 0
    if pace_now and pace_before and pace_before > 0:
        progress = round(
            ((pace_before - pace_now) / pace_before) * 100
        )

    #target runs per wk
    target = 4
    if goal and goal.workouts_per_week_target:
        target = goal.workouts_per_week_target

    return render_template(
        'running.html',
        activities=all_runs,
        runs_this_week=runs_week,
        total_km_week=km_week,
        runs_5k=five_k,
        runs_10k=ten_k,
        runs_half=half_m,
        runs_marathon=full_m,
        training_plan=plan,
        running_goal=goal,
        streak=s,
        pace_progress=progress,
        workouts_target=target
    )


@running_bp.route('/running/log', methods=['POST'])
def log_run():
    uid = get_current_user_id()
    r_type = get_running_type_id()

    if not r_type:
        flash('Running exercise type was not found.', 'error')
        return redirect(url_for('running.running_page'))

    #form
    d = request.form.get('date')
    dist = request.form.get('distance')
    dur = request.form.get('duration')
    cals = request.form.get('calories')
    note = request.form.get('notes')

    kg = get_user_weight(uid)

    #turn to nums safely
    dist_num = None
    dur_num = None

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

    #work out pace 
    pace = None
    if dist_num and dur_num and dist_num > 0:
        secs = dur_num * 60
        pace = round(secs / dist_num, 1)

    #cals typedd or work out the cal
    final_cals = None
    if cals:
        try:
            final_cals = int(cals)
        except ValueError:
            final_cals = None

    if final_cals is None and dur_num:
    # Use saved user weight if available, otherwise use a default estimate
        weight = kg if kg and kg > 0 else 70

        met = get_running_met(dist_num, dur_num)
        final_cals = calculate_calories(met, weight, dur_num)

    #save run
    new_run = Activity(
        user_id=uid,
        exercise_type_id=r_type,
        date=date.fromisoformat(d) if d else date.today(),
        duration_minutes=dur_num or 0,
        distance_km=dist_num or 0.0,
        pace_per_km=pace or 0.0,
        calories=final_cals or 0,
        notes=note or ''
    )

    db.session.add(new_run)
    db.session.commit()

    flash('Run logged successfully!', 'success')
    return redirect(url_for('running.running_page'))


@running_bp.route('/running/plan', methods=['POST'])
def create_running_plan():
    uid = get_current_user_id()

    per_week = request.form.get('runs_per_week', type=int)
    weekly_km = request.form.get('weekly_distance', type=float)
    t_pace = request.form.get('target_pace')

    #existing run plan
    plan = TrainingPlan.query.filter(
        TrainingPlan.user_id == uid,
        TrainingPlan.name.like('%Running%')
    ).order_by(TrainingPlan.plan_id.desc()).first()

    #update or new one
    if plan:
        plan.start_date = date.today()
        plan.end_date = date.today() + timedelta(weeks=8)
        plan.swims_per_week = per_week or 0
        plan.weekly_distance = weekly_km or 0.0
        plan.target_pace = t_pace or ''
    else:
        plan = TrainingPlan(
            user_id=uid,
            name='Running Plan',
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=8),
            swims_per_week=per_week or 0,
            weekly_distance=weekly_km or 0.0,
            target_pace=t_pace or ''
        )
        db.session.add(plan)

    db.session.commit()

    flash('Running plan saved!', 'success')
    return redirect(url_for('running.running_page'))


@running_bp.route('/running/goal', methods=['POST'])
def set_running_goal():
    uid = get_current_user_id()

    g_type = request.form.get('goal_type')
    t_date = request.form.get('target_date')
    per_week = request.form.get('workouts_per_week', type=int)

    #existing goal
    goal = UserGoal.query.filter(
        UserGoal.user_id == uid,
        UserGoal.goal_type.like('%run%')
    ).order_by(UserGoal.id.desc()).first()

    full_type = f'{g_type} run' if g_type else 'general run'
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

    flash('Running goal set!', 'success')
    return redirect(url_for('running.running_page'))


@running_bp.route('/running/delete/<int:activity_id>', methods=['POST'])
def delete_run(activity_id):
    uid = get_current_user_id()

    #only del if belongs to user
    r = Activity.query.filter_by(
        activity_id=activity_id,
        user_id=uid,
        exercise_type_id=get_running_type_id()
    ).first_or_404()

    db.session.delete(r)
    db.session.commit()

    flash('Run deleted.', 'success')
    return redirect(url_for('running.running_page'))
