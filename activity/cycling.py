from flask import render_template, request, redirect, url_for, flash
from datetime import date, timedelta
from database import get_db, get_current_user_id, get_exercise_type_id



## gets the id for cycling from the exercise type table
def get_cycling_type_id():
    return get_exercise_type_id('Cycling')

## works out what date monday was this week
def get_week_start():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

## main function that loads all cycling data and shows the page
def show_cycling_page():
    conn = get_db()
    user_id = get_current_user_id()
    cycling_type_id = get_cycling_type_id()
    week_start = get_week_start()

    #get all the users cycling activities, newest first
    activities = conn.execute('''
        SELECT * FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, cycling_type_id)).fetchall()

    #how many rides theyve done this week
    rides_this_week = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, cycling_type_id, week_start)).fetchone()['count']

    #total km cycled this week
    total_km_week = conn.execute('''
        SELECT COALESCE(SUM(distance_km), 0) as total FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
    ''', (user_id, cycling_type_id, week_start)).fetchone()['total']

    #counting how many rides fall into each distance category
    rides_10km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km <= 10 AND distance_km > 0
    ''', (user_id, cycling_type_id)).fetchone()['count']

    rides_25km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 10 AND distance_km <= 25
    ''', (user_id, cycling_type_id)).fetchone()['count']

    rides_50km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 25 AND distance_km <= 50
    ''', (user_id, cycling_type_id)).fetchone()['count']

    rides_100km = conn.execute('''
        SELECT COUNT(*) as count FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND distance_km > 50
    ''', (user_id, cycling_type_id)).fetchone()['count']

    # check if theyve got a training plan saved
    training_plan = conn.execute('''
        SELECT * FROM Training_Plan
        WHERE user_id = ? AND name LIKE '%Cycling%'
        ORDER BY plan_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # check if theyve got a cycling goal set
    cycling_goal = conn.execute('''
        SELECT * FROM User_Goal
        WHERE user_id = ? AND goal_type LIKE '%cycle%'
        ORDER BY goal_id DESC LIMIT 1
    ''', (user_id,)).fetchone()

    # working out the streak - how many days in a row
    # it goes backwards from today checking each date
    streak = 0
    all_dates = conn.execute('''
        SELECT DISTINCT date FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        ORDER BY date DESC
    ''', (user_id, cycling_type_id)).fetchall()

    if all_dates:
        check_date = date.today()
        for row in all_dates:
            ride_date = date.fromisoformat(row['date'])
            if ride_date == check_date:
                streak += 1
                check_date = check_date - timedelta(days=1)
            elif ride_date == check_date - timedelta(days=1):
                # if they havent cycled today yet, still count yesterday
                streak += 1
                check_date = ride_date - timedelta(days=1)
            else:
                break

    # comparing this weeks average speed to last weeks
    avg_speed_this_week = conn.execute('''
        SELECT AVG(average_speed_kmh) as avg_speed FROM Activity
        WHERE user_id = ? AND exercise_type_id = ? AND date >= ?
        AND average_speed_kmh IS NOT NULL
    ''', (user_id, cycling_type_id, week_start)).fetchone()['avg_speed']

    last_week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
    avg_speed_last_week = conn.execute('''
        SELECT AVG(average_speed_kmh) as avg_speed FROM Activity
        WHERE user_id = ? AND exercise_type_id = ?
        AND date >= ? AND date < ?
        AND average_speed_kmh IS NOT NULL
    ''', (user_id, cycling_type_id, last_week_start, week_start)).fetchone()['avg_speed']

    # work out the percentage change
    # higher speed = better so its the other way round to swimming
    speed_progress = 0
    if avg_speed_this_week and avg_speed_last_week and avg_speed_last_week > 0:
        speed_progress = round(((avg_speed_this_week - avg_speed_last_week) / avg_speed_last_week) * 100)

    # default target is 5 rides per week unless theyve set their own goal
    workouts_target = 5
    if cycling_goal and cycling_goal['workouts_per_week_target']:
        workouts_target = cycling_goal['workouts_per_week_target']

    conn.close()

    # send everything to the html template to display
    return render_template('cycling.html',
        activities=activities,
        rides_this_week=rides_this_week,
        total_km_week=total_km_week,
        rides_10km=rides_10km,
        rides_25km=rides_25km,
        rides_50km=rides_50km,
        rides_100km=rides_100km,
        training_plan=training_plan,
        cycling_goal=cycling_goal,
        streak=streak,
        speed_progress=speed_progress,
        workouts_target=workouts_target
    )

##saves a new ride to the database when the user fills in the form
def log_ride():
    conn = get_db()
    user_id = get_current_user_id()
    cycling_type_id = get_cycling_type_id()

    ride_date = request.form.get('date')
    distance = request.form.get('distance')
    duration = request.form.get('duration')
    average_speed = request.form.get('average_speed')
    calories = request.form.get('calories')
    notes = request.form.get('notes')

    #if they typed in a speed use that otherwise work it out
    calc_speed = None
    if average_speed:
        try:
            calc_speed = float(average_speed)
        except ValueError:
            pass
    elif distance and duration:
        try:
            distance_float = float(distance)
            duration_int = int(duration)
            if duration_int > 0:
                hours = duration_int / 60
                calc_speed = round(distance_float / hours, 1)
        except ValueError:
            pass  #if something goes wrong just leave speed empty

    # put it all in the database
    conn.execute('''
        INSERT INTO Activity (user_id, exercise_type_id, date, duration_minutes,
                            distance_km, average_speed_kmh, calories, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        cycling_type_id,
        ride_date,
        int(duration) if duration else None,
        float(distance) if distance else None,
        calc_speed,
        int(calories) if calories else None,
        notes if notes else None
    ))

    conn.commit()
    conn.close()

    flash('Ride logged successfully!', 'success')
    return redirect(url_for('cycling'))

##saves a training plan
def create_cycling_plan():
    conn = get_db()
    user_id = get_current_user_id()

    rides_per_week = request.form.get('rides_per_week')
    weekly_distance = request.form.get('weekly_distance')
    target_speed = request.form.get('target_speed')

    conn.execute('''
        INSERT INTO Training_Plan (user_id, name, start_date, swims_per_week,
                                  weekly_distance, target_pace)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        'Cycling Plan',
        date.today().isoformat(),
        int(rides_per_week) if rides_per_week else None,
        float(weekly_distance) if weekly_distance else None,
        target_speed if target_speed else None
    ))

    conn.commit()
    conn.close()

    flash('Cycling plan created!', 'success')
    return redirect(url_for('cycling'))

##saves the users cycling goal
def set_cycling_goal():
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
        goal_type + ' cycle' if goal_type else 'general cycle',
        target_date if target_date else None,
        int(workouts_per_week) if workouts_per_week else 5
    ))

    conn.commit()
    conn.close()

    flash('Cycling goal set!', 'success')
    return redirect(url_for('cycling'))

#delete
def delete_ride(activity_id):
    """deletes a ride from the database"""
    conn = get_db()
    conn.execute('DELETE FROM Activity WHERE activity_id = ?', (activity_id,))
    conn.commit()
    conn.close()

    flash('Ride deleted.', 'success')
    return redirect(url_for('cycling'))