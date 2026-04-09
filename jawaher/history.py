# history.py
# handles the workout history page

from flask import render_template, request, redirect, url_for, flash
from database import get_db, get_current_user_id

PER_PAGE = 10


def show_history_page():
    conn = get_db()
    user_id = get_current_user_id()
    active_sport = request.args.get('sport', 'all')
    current_page = int(request.args.get('page', 1))
    offset = (current_page - 1) * PER_PAGE

    if active_sport and active_sport != 'all':
        activities = conn.execute(
            '''
            SELECT a.*, et.name as sport_name
            FROM Activity a
            JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
            WHERE a.user_id = ? AND et.name = ?
            ORDER BY a.date DESC
            LIMIT ? OFFSET ?
            ''',
            (user_id, active_sport, PER_PAGE, offset)
        ).fetchall()

        total_count = conn.execute(
            '''
            SELECT COUNT(*) as c
            FROM Activity a
            JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
            WHERE a.user_id = ? AND et.name = ?
            ''',
            (user_id, active_sport)
        ).fetchone()['c']

        best_pace_row = conn.execute(
            '''
            SELECT MIN(a.pace_per_km) as bp
            FROM Activity a
            JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
            WHERE a.user_id = ? AND et.name = ? AND a.pace_per_km IS NOT NULL
            ''',
            (user_id, active_sport)
        ).fetchone()

        longest_row = conn.execute(
            '''
            SELECT ROUND(MAX(a.distance_km), 1) as l
            FROM Activity a
            JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
            WHERE a.user_id = ? AND et.name = ?
            ''',
            (user_id, active_sport)
        ).fetchone()
    else:
        activities = conn.execute(
            '''
            SELECT a.*, et.name as sport_name
            FROM Activity a
            JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
            WHERE a.user_id = ?
            ORDER BY a.date DESC
            LIMIT ? OFFSET ?
            ''',
            (user_id, PER_PAGE, offset)
        ).fetchall()

        total_count = conn.execute(
            'SELECT COUNT(*) as c FROM Activity WHERE user_id = ?',
            (user_id,)
        ).fetchone()['c']

        best_pace_row = conn.execute(
            '''
            SELECT MIN(pace_per_km) as bp
            FROM Activity
            WHERE user_id = ? AND pace_per_km IS NOT NULL
            ''',
            (user_id,)
        ).fetchone()

        longest_row = conn.execute(
            'SELECT ROUND(MAX(distance_km), 1) as l FROM Activity WHERE user_id = ?',
            (user_id,)
        ).fetchone()

    best_pace_shown = best_pace_row['bp'] if best_pace_row and best_pace_row['bp'] else None
    longest_shown = longest_row['l'] if longest_row and longest_row['l'] else None
    total_pages = max(1, -(-total_count // PER_PAGE))

    conn.close()

    return render_template(
        'history.html',
        activities=activities,
        active_sport=active_sport,
        current_page=current_page,
        total_pages=total_pages,
        best_pace_shown=best_pace_shown,
        longest_shown=longest_shown,
    )


def delete_history_activity(activity_id):
    conn = get_db()
    conn.execute('DELETE FROM Activity WHERE activity_id = ?', (activity_id,))
    conn.commit()
    conn.close()

    flash('Session deleted.', 'success')
    return redirect(request.referrer or url_for('history'))