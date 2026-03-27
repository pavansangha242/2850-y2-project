from flask import render_template, request, redirect, url_for, flash
from datetime import date, timedelta
from database import get_db, get_current_user_id, get_exercise_type_id



## gets the id for walking from the exercise type table
def get_walking_type_id():
    return get_exercise_type_id('Walking')

## works out what date monday was this week
def get_week_start():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

## main function that loads all walking data and shows the page
def show_walking_page():
    conn = get_db()
    user_id = get_current_user_id()
    walking_type_id = get_walking_type_id()
    week_start = get_week_start()

    #get all the users walking activities, newest first
    activities = conn.execute('''
        SELECT * FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, walking_type_id)).fetchall()

    #how many walks theyve done this week
    walks_this_week = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, walking_type_id, week_start)).fetchone()['count']

    #total steps this week - main stat for walking
    total_steps_week = conn.execute('''
        SELECT COALESCE(SUM(steps), 0) as total FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, walking_type_id, week_start)).fetchone()['total']

    #total km walked this week
    total_km_week = conn.execute('''
        SELECT COALESCE(SUM(distance_km), 0) as total FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, walking_type_id, week_start)).fetchone()['total']

    #counting how many walks fall into each distance category
    walks_1km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km <= 1 AND distance_km > 0
    ''', (user_id, walking_type_id)).fetchone()['count']

    walks_3km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 1 AND distance_km <= 3
    ''', (user_id, walking_type_id)).fetchone()['count']

    walks_5km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 3 AND distance_km <= 5
    ''', (user_id, walking_type_id)).fetchone()['count']

    walks_10km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 5
    ''', (user_id, walking_type_id)).fetchone()['count']

    # check if theyve got a training plan saved
    training_plan = conn.execute('''
        SELECT * FROM Training_Plan
        WHERE user_id = ? AND name LIKE '%Walking%'
        ORDER BY plan_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # check if theyve got a walking goal set
    walking_goal = conn.execute('''
        SELECT * FROM User_Goal
        WHERE user_id = ? AND goal_type LIKE '%walk%'
        ORDER BY goal_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # working out the streak - how many days in a row
    # it goes backwards from today checking each date
    streak = 0
    all_dates = conn.execute('''
        SELECT DISTINCT date FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, walking_type_id)).fetchall()

    if all_dates:
        check_date = date.today()
        for row in all_dates:
            walk_date = date.fromisoformat(row['date'])
            if walk_date == check_date:
                streak += 1
                check_date = check_date - timedelta(days=1)
            elif walk_date == check_date - timedelta(days=1):
                # if they havent walked today yet, still count yesterday
                streak += 1
                check_date = walk_date - timedelta(days=1)
            else:
                break

    # comparing this weeks average steps to last weeks
    # more steps = better so its the opposite to pace
    avg_steps_this_week = conn.execute('''
        SELECT AVG(steps) as avg_steps FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
        AND steps IS NOT NULL
    ''', (user_id, walking_type_id, week_start)).fetchone()['avg_steps']

    last_week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
    avg_steps_last_week = conn.execute('''
        SELECT AVG(steps) as avg_steps FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        AND date >= ? AND date < ?
        AND steps IS NOT NULL
    ''', (user_id, walking_type_id, last_week_start, week_start)).fetchone()['avg_steps']

    # work out the percentage change
    step_progress = 0
    if avg_steps_this_week and avg_steps_last_week and avg_steps_last_week > 0:
        step_progress = round(((avg_steps_this_week - avg_steps_last_week) / avg_steps_last_week) * 100)

    # default target is 5 walks per week unless theyve set their own goal
    workouts_target = 5
    if walking_goal and walking_goal['workouts_per_week_target']:
        workouts_target = walking_goal['workouts_per_week_target']

    conn.close()

    # send everything to the html template to display
    return render_template('walking.html',
        activities=activities,
        walks_this_week=walks_this_week,
        total_steps_week=total_steps_week,
        total_km_week=total_km_week,
        walks_1km=walks_1km,
        walks_3km=walks_3km,
        walks_5km=walks_5km,
        walks_10km=walks_10km,
        training_plan=training_plan,
        walking_goal=walking_goal,
        streak=streak,
        step_progress=step_progress,
        workouts_target=workouts_target
    )

##saves a new walk to the database when the user fills in the form
def log_walk():
    conn = get_db()
    user_id = get_current_user_id()
    walking_type_id = get_walking_type_id()

    # grab all the values from the form
    walk_date = request.form.get('date')
    distance = request.form.get('distance')
    duration = request.form.get('duration')
    steps = request.form.get('steps')
    calories = request.form.get('calories')
    notes = request.form.get('notes')

    #work out pace per km automatically
    #same as running but obviously walking is slower
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
                            distance_km, steps, pace_per_km, calories, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        walking_type_id,
        walk_date,
        int(duration) if duration else None,
        float(distance) if distance else None,
        int(steps) if steps else None,
        pace_per_km,
        int(calories) if calories else None,
        notes if notes else None
    ))

    conn.commit()
    conn.close()

    flash('Walk logged successfully!', 'success')
    return redirect(url_for('walking'))

##saves a training plan
def create_walking_plan():
    conn = get_db()
    user_id = get_current_user_id()

    walks_per_week = request.form.get('walks_per_week')
    weekly_distance = request.form.get('weekly_distance')
    target_steps = request.form.get('target_steps')

    conn.execute('''
        INSERT INTO Training_Plan (user_id, name, start_date, swims_per_week,
                                  weekly_distance, target_pace)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        'Walking Plan',
        date.today().isoformat(),
        int(walks_per_week) if walks_per_week else None,
        float(weekly_distance) if weekly_distance else None,
        target_steps if target_steps else None
    ))

    conn.commit()
    conn.close()

    flash('Walking plan created!', 'success')
    return redirect(url_for('walking'))

##saves the users walking goal
##walking also has a step target which the other sports dont have
def set_walking_goal():
    conn = get_db()
    user_id = get_current_user_id()

    goal_type = request.form.get('goal_type')
    target_date = request.form.get('target_date')
    workouts_per_week = request.form.get('workouts_per_week')
    step_target = request.form.get('step_target')

    conn.execute('''
        INSERT INTO User_Goal (user_id, goal_type, target_date, workouts_per_week_target, step_target)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user_id,
        goal_type + ' walk' if goal_type else 'general walk',
        target_date if target_date else None,
        int(workouts_per_week) if workouts_per_week else 5,
        int(step_target) if step_target else None
    ))

    conn.commit()
    conn.close()

    flash('Walking goal set!', 'success')
    return redirect(url_for('walking'))

#delete
def delete_walk(activity_id):
    """deletes a walk from the database"""
    conn = get_db()
    conn.execute('DELETE FROM Activity WHERE activity_id = ?', (activity_id,))
    conn.commit()
    conn.close()

    flash('Walk deleted.', 'success')
    return redirect(url_for('walking'))