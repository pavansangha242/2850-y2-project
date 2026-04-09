# progress.py
# handles the progress page

from flask import render_template, request
from datetime import date, timedelta
from database import get_db, get_current_user_id, get_exercise_type_id


def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


def _sport_filter(user_id, sport):
    """Return the filter for the selected sport."""
    if sport and sport != 'all':
        type_id = get_exercise_type_id(sport)
        if type_id:
            return 'user_id = ? AND exercise_type_id = ?', (user_id, type_id), type_id
    return 'user_id = ?', (user_id,), None


def show_progress_page():
    conn = get_db()
    user_id = get_current_user_id()
    active_sport = request.args.get('sport', 'all')

    where, params, type_id = _sport_filter(user_id, active_sport)

    total_sessions = conn.execute(
        f'SELECT COUNT(*) as c FROM Activity WHERE {where}', params
    ).fetchone()['c']

    has_data = total_sessions > 0

    if has_data:
        total_distance = float(
            conn.execute(
                f'SELECT ROUND(COALESCE(SUM(distance_km),0),1) as d FROM Activity WHERE {where}',
                params
            ).fetchone()['d'] or 0
        )

        best_pace = conn.execute(
            f'''
            SELECT MIN(pace_per_km) as bp
            FROM Activity
            WHERE {where} AND pace_per_km IS NOT NULL AND pace_per_km > 0
            ''',
            params
        ).fetchone()['bp']

        longest_run = conn.execute(
            f'SELECT ROUND(MAX(distance_km),1) as l FROM Activity WHERE {where}',
            params
        ).fetchone()['l']

        total_calories = conn.execute(
            f'SELECT COALESCE(SUM(calories),0) as c FROM Activity WHERE {where}',
            params
        ).fetchone()['c'] or 0

        # pick the right metric column for each sport
        if active_sport == 'Cycling':
            metric_col = 'average_speed_kmh'
        elif active_sport == 'Swimming':
            metric_col = 'pace_per_100m'
        else:
            metric_col = 'pace_per_km'

        metric_rows = conn.execute(
            f'''
            SELECT date, {metric_col} as mv, notes, distance_km
            FROM Activity
            WHERE {where} AND {metric_col} IS NOT NULL AND {metric_col} > 0
            ORDER BY date DESC
            LIMIT 8
            ''',
            params
        ).fetchall()
        metric_rows = list(reversed(metric_rows))

        chart_labels = []
        chart_pace_values = []

        for session in metric_rows:
            chart_labels.append(session['notes'][:10] if session['notes'] else session['date'])
            value = float(session['mv'])
            if active_sport != 'Cycling':
                value = round(value / 60, 3)
            chart_pace_values.append(round(value, 2))

        dist_rows = conn.execute(
            f'''
            SELECT date, ROUND(distance_km,2) as d
            FROM Activity
            WHERE {where} AND distance_km IS NOT NULL
            ORDER BY date DESC
            LIMIT 8
            ''',
            params
        ).fetchall()
        dist_rows = list(reversed(dist_rows))
        chart2_labels = [session['date'] for session in dist_rows]
        chart2_values = [float(session['d']) for session in dist_rows]

        # show donut chart only for all sports
        if active_sport == 'all':
            sport_rows = conn.execute(
                '''
                SELECT et.name as sport, ROUND(SUM(a.distance_km),1) as total_km
                FROM Activity a
                JOIN Exercise_Type et ON a.exercise_type_id = et.exercise_type_id
                WHERE a.user_id = ? AND a.distance_km IS NOT NULL
                GROUP BY et.name
                HAVING total_km > 0
                ''',
                (user_id,)
            ).fetchall()
            sport_labels = [row['sport'] for row in sport_rows]
            sport_distances = [row['total_km'] for row in sport_rows]
        else:
            sport_labels = []
            sport_distances = []

        # weekly counts for the last 8 weeks
        weekly_labels = []
        weekly_counts = []

        for i in range(7, -1, -1):
            ws = (get_week_start() - timedelta(weeks=i)).isoformat()
            we = (get_week_start() - timedelta(weeks=i) + timedelta(days=6)).isoformat()
            count = conn.execute(
                f'''
                SELECT COUNT(*) as c
                FROM Activity
                WHERE {where} AND date >= ? AND date <= ?
                ''',
                (*params, ws, we)
            ).fetchone()['c']

            weekly_labels.append(f'W{8 - i}')
            weekly_counts.append(count)

        monday = get_week_start()
        week_daily_km = []

        for i in range(7):
            day = (monday + timedelta(days=i)).isoformat()
            km = conn.execute(
                f'''
                SELECT ROUND(COALESCE(SUM(distance_km),0),1) as km
                FROM Activity
                WHERE {where} AND date = ?
                ''',
                (*params, day)
            ).fetchone()['km']
            week_daily_km.append(float(km) if km else 0)

        week_max_km = max(week_daily_km) if any(week_daily_km) else 1

        current_streak = 0
        all_dates = conn.execute(
            f'SELECT DISTINCT date FROM Activity WHERE {where} ORDER BY date DESC',
            params
        ).fetchall()

        if all_dates:
            check = date.today()
            for row in all_dates:
                day = date.fromisoformat(row['date'])
                if day == check:
                    current_streak += 1
                    check -= timedelta(days=1)
                elif day == check - timedelta(days=1):
                    current_streak += 1
                    check = day - timedelta(days=1)
                else:
                    break

    else:
        total_distance = 0
        best_pace = None
        longest_run = None
        total_calories = 0
        chart_labels = []
        chart_pace_values = []
        chart2_labels = []
        chart2_values = []
        sport_labels = []
        sport_distances = []
        weekly_labels = []
        weekly_counts = []
        week_daily_km = [0] * 7
        week_max_km = 1
        current_streak = 0

    conn.close()

    return render_template(
        'progress.html',
        active_sport=active_sport,
        has_data=has_data,
        total_sessions=total_sessions,
        total_distance=total_distance,
        best_pace=best_pace,
        longest_run=longest_run,
        total_calories=total_calories,
        chart_labels=chart_labels,
        chart_pace_values=chart_pace_values,
        chart2_labels=chart2_labels,
        chart2_values=chart2_values,
        sport_labels=sport_labels,
        sport_distances=sport_distances,
        weekly_labels=weekly_labels,
        weekly_counts=weekly_counts,
        week_daily_km=week_daily_km,
        week_max_km=week_max_km,
        current_streak=current_streak,
    )