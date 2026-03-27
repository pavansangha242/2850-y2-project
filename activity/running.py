from flask import render_template, request, redirect, url_for, flash
from datetime import date, timedelta
from database import get_db, get_current_user_id, get_exercise_type_id



## gets the id for running from the exercise type table
def get_running_type_id():
    return get_exercise_type_id('Running')

## works out what date monday was this week
def get_week_start():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

## main function that loads all running data and shows the page
def show_running_page():
    conn = get_db()
    user_id = get_current_user_id()
    running_type_id = get_running_type_id()
    week_start = get_week_start()

    #get all the users running activities, newest first
    activities = conn.execute('''
        SELECT * FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, running_type_id)).fetchall()

    #how many runs theyve done this week
    runs_this_week = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, running_type_id, week_start)).fetchone()['count']

    #total km ran this week
    total_km_week = conn.execute('''
        SELECT COALESCE(SUM(distance_km), 0) as total FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, running_type_id, week_start)).fetchone()['total']

    #counting how many runs fall into each distance category
    runs_5k = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km <= 5 AND distance_km > 0
    ''', (user_id, running_type_id)).fetchone()['count']

    runs_10k = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 5 AND distance_km <= 10
    ''', (user_id, running_type_id)).fetchone()['count']

    runs_half = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 10 AND distance_km <= 21.1
    ''', (user_id, running_type_id)).fetchone()['count']

    runs_marathon = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 21.1
    ''', (user_id, running_type_id)).fetchone()['count']

    # check if theyve got a training plan saved
    training_plan = conn.execute('''
        SELECT * FROM Training_Plan
        WHERE user_id = ? AND name LIKE '%Running%'
        ORDER BY plan_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # check if theyve got a running goal set
    running_goal = conn.execute('''
        SELECT * FROM User_Goal
        WHERE user_id = ? AND goal_type LIKE '%run%'
        ORDER BY goal_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # working out the streak - how many days in a row
    # it goes backwards from today checking each date
    streak = 0
    all_dates = conn.execute('''
        SELECT DISTINCT date FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, running_type_id)).fetchall()

    if all_dates:
        check_date = date.today()
        for row in all_dates:
            run_date = date.fromisoformat(row['date'])
            if run_date == check_date:
                streak += 1
                check_date = check_date - timedelta(days=1)
            elif run_date == check_date - timedelta(days=1):
                # if they havent ran today yet, still count yesterday
                streak += 1
                check_date = run_date - timedelta(days=1)
            else:
                break

    # comparing this weeks average pace to last weeks
    # lower pace = faster = better, same as swimming
    avg_pace_this_week = conn.execute('''
        SELECT AVG(pace_per_km) as avg_pace FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
        AND pace_per_km IS NOT NULL
    ''', (user_id, running_type_id, week_start)).fetchone()['avg_pace']

    last_week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
    avg_pace_last_week = conn.execute('''
        SELECT AVG(pace_per_km) as avg_pace FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        AND date >= ? AND date < ?
        AND pace_per_km IS NOT NULL
    ''', (user_id, running_type_id, last_week_start, week_start)).fetchone()['avg_pace']

    # work out the percentage change
    pace_progress = 0
    if avg_pace_this_week and avg_pace_last_week and avg_pace_last_week > 0:
        pace_progress = round(((avg_pace_last_week - avg_pace_this_week) / avg_pace_last_week) * 100)

    # default target is 4 runs per week unless theyve set their own goal
    workouts_target = 4
    if running_goal and running_goal['workouts_per_week_target']:
        workouts_target = running_goal['workouts_per_week_target']

    conn.close()

    # send everything to the html template to display
    return render_template('running.html',
        activities=activities,
        runs_this_week=runs_this_week,
        total_km_week=total_km_week,
        runs_5k=runs_5k,
        runs_10k=runs_10k,
        runs_half=runs_half,
        runs_marathon=runs_marathon,
        training_plan=training_plan,
        running_goal=running_goal,
        streak=streak,
        pace_progress=pace_progress,
        workouts_target=workouts_target
    )

##saves a new run to the database when the user fills in the form
def log_run():
    conn = get_db()
    user_id = get_current_user_id()
    running_type_id = get_running_type_id()

    # grab all the values from the form
    run_date = request.form.get('date')
    distance = request.form.get('distance')
    duration = request.form.get('duration')
    calories = request.form.get('calories')
    notes = request.form.get('notes')

    #work out pace per km automatically
    #e.g. 5km in 25 mins = 300 seconds per km
    pace_per_km = None
    if distance and duration:
        try:
            distance_float = float(distance)
            duration_int = int(duration)
            if distance_float > 0:
                total_seconds = duration_int * 60
                pace_per_km = round(total_seconds / distance_float, 1)
        except ValueError:
            pass  #if something goes wrong just leave pace empty

    # put it all in the database
    conn.execute('''
        INSERT INTO Activity (user_id, exercise_type_id, date, duration_minutes,
                            distance_km, pace_per_km, calories, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        running_type_id,
        run_date,
        int(duration) if duration else None,
        float(distance) if distance else None,
        pace_per_km,
        int(calories) if calories else None,
        notes if notes else None
    ))

    conn.commit()
    conn.close()

    flash('Run logged successfully!', 'success')
    return redirect(url_for('running'))

##saves a training plan
def create_running_plan():
    conn = get_db()
    user_id = get_current_user_id()

    runs_per_week = request.form.get('runs_per_week')
    weekly_distance = request.form.get('weekly_distance')
    target_pace = request.form.get('target_pace')

    conn.execute('''
        INSERT INTO Training_Plan (user_id, name, start_date, swims_per_week,
                                  weekly_distance, target_pace)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        'Running Plan',
        date.today().isoformat(),
        int(runs_per_week) if runs_per_week else None,
        float(weekly_distance) if weekly_distance else None,
        target_pace if target_pace else None
    ))

    conn.commit()
    conn.close()

    flash('Running plan created!', 'success')
    return redirect(url_for('running'))

##saves the users running goal
def set_running_goal():
    conn = get_db()
    user_id = get_current_user_id()

    goal_type = request.form.get('goal_type')
    target_date = request.form.get('target_date')
    workouts_per_week = request.form.get('workouts_per_week')

    conn.execute('''
        INSERT INTO User_Goal (user_id, goal_type, target_date, workouts_per_week_target)
        VALUES (?, ?, ?, ?)
    ''', (
        user_id,
        goal_type + ' run' if goal_type else 'general run',
        target_date if target_date else None,
        int(workouts_per_week) if workouts_per_week else 4
    ))

    conn.commit()
    conn.close()

    flash('Running goal set!', 'success')
    return redirect(url_for('running'))

#delete
def delete_run(activity_id):
    """deletes a run from the database"""
    conn = get_db()
    conn.execute('DELETE FROM Activity WHERE activity_id = ?', (activity_id,))
    conn.commit()
    conn.close()

    flash('Run deleted.', 'success')
    return redirect(url_for('running'))