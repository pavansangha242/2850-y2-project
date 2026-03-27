

from flask import render_template, request, redirect, url_for, flash
from datetime import date, timedelta
from database import get_db, get_current_user_id, get_exercise_type_id



## gets the id for swimming from the exercise type table
def get_swimming_type_id():
    return get_exercise_type_id('Swimming')

## works out what date 
def get_week_start():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

  ##main function that loads all data and shows the page
def show_swimming_page():
    conn = get_db()
    user_id = get_current_user_id()
    swimming_type_id = get_swimming_type_id()
    week_start = get_week_start()

    #get all the users swimming activities, newest first
    activities = conn.execute('''
        SELECT * FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, swimming_type_id)).fetchall()

    #how many swims theyve done this week
    swims_this_week = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, swimming_type_id, week_start)).fetchone()['count']

    #add all the laps from this week
    total_laps_week = conn.execute('''
        SELECT COALESCE(SUM(laps), 0) as total FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, swimming_type_id, week_start)).fetchone()['total']

    #counting how many swims fall into each distance category
    swims_500m = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km <= 0.5 AND distance_km > 0
    ''', (user_id, swimming_type_id)).fetchone()['count']

    swims_1km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 0.5 AND distance_km <= 1.0
    ''', (user_id, swimming_type_id)).fetchone()['count']

    swims_2km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 1.0 AND distance_km <= 2.0
    ''', (user_id, swimming_type_id)).fetchone()['count']

    swims_5km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 2.0
    ''', (user_id, swimming_type_id)).fetchone()['count']

    # check if theyve got a training plan saved
    training_plan = conn.execute('''
        SELECT * FROM Training_Plan
        WHERE user_id = ? AND name LIKE '%Swimming%'
        ORDER BY plan_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # check if theyve got a swimming goal set
    swimming_goal = conn.execute('''
        SELECT * FROM User_Goal
        WHERE user_id = ? AND goal_type LIKE '%swim%'
        ORDER BY goal_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # working out the streak - how many days in a row
    # it goes backwards from today checking each date
    streak = 0
    all_dates = conn.execute('''
        SELECT DISTINCT date FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, swimming_type_id)).fetchall()

    if all_dates:
        check_date = date.today()
        for row in all_dates:
            swim_date = date.fromisoformat(row['date'])
            if swim_date == check_date:
                streak += 1
                check_date = check_date - timedelta(days=1)
            elif swim_date == check_date - timedelta(days=1):
                # if they havent swam today yet, still count yesterday
                streak += 1
                check_date = swim_date - timedelta(days=1)
            else:
                break

    # comparing this weeks average pace to last weeks
    avg_pace_this_week = conn.execute('''
        SELECT AVG(pace_per_100m) as avg_pace FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
        AND pace_per_100m IS NOT NULL
    ''', (user_id, swimming_type_id, week_start)).fetchone()['avg_pace']

    last_week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
    avg_pace_last_week = conn.execute('''
        SELECT AVG(pace_per_100m) as avg_pace FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        AND date >= ? AND date < ?
        AND pace_per_100m IS NOT NULL
    ''', (user_id, swimming_type_id, last_week_start, week_start)).fetchone()['avg_pace']

    # work out the percentage change
    pace_progress = 0
    if avg_pace_this_week and avg_pace_last_week and avg_pace_last_week > 0:
        pace_progress = round(((avg_pace_last_week - avg_pace_this_week) / avg_pace_last_week) * 100)

    # default target is 4 swims per week unless theyve set their own goal
    workouts_target = 4
    if swimming_goal and swimming_goal['workouts_per_week_target']:
        workouts_target = swimming_goal['workouts_per_week_target']

    conn.close()

    # send everything to the html template to display
    return render_template('swimming.html',
        activities=activities,
        swims_this_week=swims_this_week,
        total_laps_week=total_laps_week,
        swims_500m=swims_500m,
        swims_1km=swims_1km,
        swims_2km=swims_2km,
        swims_5km=swims_5km,
        training_plan=training_plan,
        swimming_goal=swimming_goal,
        streak=streak,
        pace_progress=pace_progress,
        workouts_target=workouts_target
    )

##saves a new swim to the database when the user fills in the form
def log_swim():
    conn = get_db()
    user_id = get_current_user_id()
    swimming_type_id = get_swimming_type_id()

    # grab all the values from the form
    swim_date = request.form.get('date')
    distance = request.form.get('distance')
    duration = request.form.get('duration')
    laps = request.form.get('laps')
    stroke_type = request.form.get('stroke_type')
    calories = request.form.get('calories')
    notes = request.form.get('notes')

    #work out pace per 100m automatically
    pace_per_100m = None
    if distance and duration:
        try:
            distance_float = float(distance)
            duration_int = int(duration)
            if distance_float > 0:
                distance_metres = distance_float * 1000
                total_seconds = duration_int * 60
                pace_per_100m = round((total_seconds / distance_metres) * 100, 1)
        except ValueError:
            pass  #if something goes wrong just leave pace empty

    # put it all in the database
    conn.execute('''
        INSERT INTO Activity (user_id, exercise_type_id, date, duration_minutes,
                            distance_km, laps, stroke_type, pace_per_100m, calories, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        swimming_type_id,
        swim_date,
        int(duration) if duration else None,
        float(distance) if distance else None,
        int(laps) if laps else None,
        stroke_type if stroke_type else None,
        pace_per_100m,
        int(calories) if calories else None,
        notes if notes else None
    ))

    conn.commit()
    conn.close()

    flash('Swim logged successfully!', 'success')
    return redirect(url_for('swimming'))

##saves a training plan
def create_swimming_plan():
    conn = get_db()
    user_id = get_current_user_id()

    swims_per_week = request.form.get('swims_per_week')
    weekly_distance = request.form.get('weekly_distance')
    target_pace = request.form.get('target_pace')

    conn.execute('''
        INSERT INTO Training_Plan (user_id, name, start_date, swims_per_week,
                                  weekly_distance, target_pace)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        'Swimming Plan',
        date.today().isoformat(),
        int(swims_per_week) if swims_per_week else None,
        float(weekly_distance) if weekly_distance else None,
        target_pace if target_pace else None
    ))

    conn.commit()
    conn.close()

    flash('Swimming plan created!', 'success')
    return redirect(url_for('swimming'))

##saves the users swimming goal
def set_swimming_goal():
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
        goal_type + ' swim' if goal_type else 'general swim',
        target_date if target_date else None,
        int(workouts_per_week) if workouts_per_week else 4
    ))

    conn.commit()
    conn.close()

    flash('Swimming goal set!', 'success')
    return redirect(url_for('swimming'))

#delete 
def delete_swim(activity_id):
    """deletes a swim from the database"""
    conn = get_db()
    conn.execute('DELETE FROM Activity WHERE activity_id = ?', (activity_id,))
    conn.commit()
    conn.close()

    flash('Swim deleted.', 'success')
    return redirect(url_for('swimming'))