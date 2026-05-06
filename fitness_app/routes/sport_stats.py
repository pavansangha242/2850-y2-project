from datetime import date, timedelta

from flask import Blueprint, render_template, abort
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import Activity, ExerciseType, User

sport_stats = Blueprint('sport_stats', __name__)


def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


# count streak days, with at least one activity
def calc_streak(user_id, sport_type):
    current_streak = 0

    rows = db.session.query(Activity.date).filter(
        Activity.user_id == user_id,
        Activity.exercise_type_id == sport_type.exercise_type_id
    ).distinct().order_by(Activity.date.desc()).all()

    if rows:
        check = date.today()

        for (activity_date,) in rows:
            if activity_date == check:
                current_streak += 1
                check -= timedelta(days=1)
            elif activity_date == check - timedelta(days=1):
                current_streak += 1
                check = activity_date - timedelta(days=1)
            else:
                break

    return current_streak


# return km per day for the current week 7 values
def get_daily_distances(user_id, sport_type):
    monday = get_week_start()
    daily_distances = []

    for i in range(7):
        day = monday + timedelta(days=i)

        km = db.session.query(
            func.coalesce(func.sum(Activity.distance_km), 0)
        ).filter(
            Activity.user_id == user_id,
            Activity.exercise_type_id == sport_type.exercise_type_id,
            Activity.date == day
        ).scalar() or 0

        daily_distances.append(round(float(km), 1))

    return daily_distances


# grap the last n sessions for chart data
def get_recent_sessions(user_id, sport_type, n=8):
    return Activity.query.filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).order_by(Activity.date.desc()).limit(n).all()


def fmt_pace(seconds):
    if not seconds:
        return '—'
    return f'{int(seconds // 60)}:{int(seconds % 60):02d}/km'


# one function per sport returns none if no data
def _running_stats(user_id, sport_type):
    sessions = get_recent_sessions(user_id, sport_type)
    if not sessions:
        return None

    total_sessions = Activity.query.filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).count()

    total_distance = db.session.query(
        func.coalesce(func.sum(Activity.distance_km), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0
    total_distance = round(total_distance, 1)

    best_pace = db.session.query(
        func.min(Activity.pace_per_km)
    ).filter(
        Activity.user_id == user_id,
        Activity.exercise_type_id == sport_type.exercise_type_id,
        Activity.pace_per_km > 0
    ).scalar()

    longest = db.session.query(
        func.max(Activity.distance_km)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    total_calories = db.session.query(
        func.coalesce(func.sum(Activity.calories), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    pace_sessions = [s for s in reversed(sessions) if s.pace_per_km and s.pace_per_km > 0]
    chart1_labels = [s.notes[:10] if s.notes else str(s.date) for s in pace_sessions]
    chart1_values = [round(float(s.pace_per_km) / 60, 3) for s in pace_sessions]

    chart2_labels = [str(s.date) for s in reversed(sessions) if s.distance_km]
    chart2_values = [round(float(s.distance_km), 2) for s in reversed(sessions) if s.distance_km]

    breakdown_rows = [
        {'label': '5k and under', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km <= 5, Activity.distance_km > 0).count()},
        {'label': '5k – 10k', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 5, Activity.distance_km <= 10).count()},
        {'label': 'Half marathon', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 10, Activity.distance_km <= 21.1).count()},
        {'label': 'Marathon+', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 21.1).count()},
    ]

    personal_bests = [
        {'label': f'Best pace: {fmt_pace(best_pace)}', 'sub': 'All time', 'dot_class': ''},
        {'label': f'Longest run: {round(longest, 1)} km', 'sub': 'Single session', 'dot_class': 'two'},
        {'label': f'{total_sessions} sessions total', 'sub': 'All time', 'dot_class': 'green'},
        {'label': f'{total_distance} km total distance', 'sub': 'All time', 'dot_class': 'amber'},
        {'label': f'{total_calories} kcal burned', 'sub': 'All time', 'dot_class': ''},
    ]

    return dict(
        tile1_value=fmt_pace(best_pace),
        tile1_label='Best Pace',
        tile2_value=f'{round(longest, 1)} km',
        tile2_label='Longest Run',
        chart1_title='Pace per Session',
        chart1_metric='Pace',
        chart1_unit='min/km',
        chart1_labels=chart1_labels,
        chart1_values=chart1_values,
        chart2_labels=chart2_labels,
        chart2_values=chart2_values,
        breakdown_title='Runs by Distance',
        breakdown_rows=breakdown_rows,
        personal_bests=personal_bests,
        total_sessions=total_sessions,
        total_distance=total_distance
    )


def _walking_stats(user_id, sport_type):
    sessions = get_recent_sessions(user_id, sport_type)
    if not sessions:
        return None

    total_sessions = Activity.query.filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).count()

    total_distance = db.session.query(
        func.coalesce(func.sum(Activity.distance_km), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0
    total_distance = round(total_distance, 1)

    total_steps = db.session.query(
        func.coalesce(func.sum(Activity.steps), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    max_steps = db.session.query(
        func.max(Activity.steps)
    ).filter(
        Activity.user_id == user_id,
        Activity.exercise_type_id == sport_type.exercise_type_id,
        Activity.steps > 0
    ).scalar() or 0

    longest = db.session.query(
        func.max(Activity.distance_km)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    step_sessions = [s for s in reversed(sessions) if s.steps and s.steps > 0]
    chart1_labels = [str(s.date) for s in step_sessions]
    chart1_values = [s.steps for s in step_sessions]

    chart2_labels = [str(s.date) for s in reversed(sessions) if s.distance_km]
    chart2_values = [round(float(s.distance_km), 2) for s in reversed(sessions) if s.distance_km]

    breakdown_rows = [
        {'label': 'Under 1 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km <= 1, Activity.distance_km > 0).count()},
        {'label': '1 km – 3 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 1, Activity.distance_km <= 3).count()},
        {'label': '3 km – 5 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 3, Activity.distance_km <= 5).count()},
        {'label': 'Over 5 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 5).count()},
    ]

    personal_bests = [
        {'label': f'{max_steps:,} steps in one session', 'sub': 'Personal best', 'dot_class': ''},
        {'label': f'{round(longest, 1)} km longest walk', 'sub': 'Single session', 'dot_class': 'two'},
        {'label': f'{total_steps:,} steps total', 'sub': 'All time', 'dot_class': 'green'},
        {'label': f'{total_distance} km total', 'sub': 'All time', 'dot_class': 'amber'},
        {'label': f'{total_sessions} walks logged', 'sub': 'All time', 'dot_class': ''},
    ]

    return dict(
        tile1_value=f'{total_steps:,}',
        tile1_label='Total Steps',
        tile2_value=f'{round(longest, 1)} km',
        tile2_label='Longest Walk',
        chart1_title='Steps per Session',
        chart1_metric='Steps',
        chart1_unit='',
        chart1_labels=chart1_labels,
        chart1_values=chart1_values,
        chart2_labels=chart2_labels,
        chart2_values=chart2_values,
        breakdown_title='Walks by Distance',
        breakdown_rows=breakdown_rows,
        personal_bests=personal_bests,
        total_sessions=total_sessions,
        total_distance=total_distance
    )


def _cycling_stats(user_id, sport_type):
    sessions = get_recent_sessions(user_id, sport_type)
    if not sessions:
        return None

    total_sessions = Activity.query.filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).count()

    total_distance = db.session.query(
        func.coalesce(func.sum(Activity.distance_km), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0
    total_distance = round(total_distance, 1)

    best_speed = db.session.query(
        func.max(Activity.average_speed_kmh)
    ).filter(
        Activity.user_id == user_id,
        Activity.exercise_type_id == sport_type.exercise_type_id,
        Activity.average_speed_kmh > 0
    ).scalar() or 0

    longest = db.session.query(
        func.max(Activity.distance_km)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    total_calories = db.session.query(
        func.coalesce(func.sum(Activity.calories), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    speed_sessions = [s for s in reversed(sessions) if s.average_speed_kmh and s.average_speed_kmh > 0]
    chart1_labels = [str(s.date) for s in speed_sessions]
    chart1_values = [round(float(s.average_speed_kmh), 1) for s in speed_sessions]

    chart2_labels = [str(s.date) for s in reversed(sessions) if s.distance_km]
    chart2_values = [round(float(s.distance_km), 2) for s in reversed(sessions) if s.distance_km]

    breakdown_rows = [
        {'label': 'Under 10 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km <= 10, Activity.distance_km > 0).count()},
        {'label': '10 km – 25 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 10, Activity.distance_km <= 25).count()},
        {'label': '25 km – 50 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 25, Activity.distance_km <= 50).count()},
        {'label': 'Over 50 km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 50).count()},
    ]

    personal_bests = [
        {'label': f'Top speed: {round(best_speed, 1)} km/h', 'sub': 'Personal best', 'dot_class': ''},
        {'label': f'Longest ride: {round(longest, 1)} km', 'sub': 'Single session', 'dot_class': 'two'},
        {'label': f'{total_sessions} rides logged', 'sub': 'All time', 'dot_class': 'green'},
        {'label': f'{total_distance} km total', 'sub': 'All time', 'dot_class': 'amber'},
        {'label': f'{total_calories} kcal burned', 'sub': 'All time', 'dot_class': ''},
    ]

    return dict(
        tile1_value=f'{round(best_speed, 1)} km/h',
        tile1_label='Top Speed',
        tile2_value=f'{round(longest, 1)} km',
        tile2_label='Longest Ride',
        chart1_title='Speed per Session',
        chart1_metric='Speed',
        chart1_unit='km/h',
        chart1_labels=chart1_labels,
        chart1_values=chart1_values,
        chart2_labels=chart2_labels,
        chart2_values=chart2_values,
        breakdown_title='Rides by Distance',
        breakdown_rows=breakdown_rows,
        personal_bests=personal_bests,
        total_sessions=total_sessions,
        total_distance=total_distance
    )


def _swimming_stats(user_id, sport_type):
    sessions = get_recent_sessions(user_id, sport_type)
    if not sessions:
        return None

    total_sessions = Activity.query.filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).count()

    total_distance = db.session.query(
        func.coalesce(func.sum(Activity.distance_km), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0
    total_distance = round(total_distance, 1)

    total_laps = db.session.query(
        func.coalesce(func.sum(Activity.laps), 0)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    best_pace_100m = db.session.query(
        func.min(Activity.pace_per_100m)
    ).filter(
        Activity.user_id == user_id,
        Activity.exercise_type_id == sport_type.exercise_type_id,
        Activity.pace_per_100m > 0
    ).scalar()

    longest = db.session.query(
        func.max(Activity.distance_km)
    ).filter_by(
        user_id=user_id,
        exercise_type_id=sport_type.exercise_type_id
    ).scalar() or 0

    def fmt_swim(secs):
        if not secs:
            return '—'
        return f'{int(secs // 60)}:{int(secs % 60):02d}/100m'

    pace_sessions = [s for s in reversed(sessions) if s.pace_per_100m and s.pace_per_100m > 0]
    chart1_labels = [str(s.date) for s in pace_sessions]
    chart1_values = [round(float(s.pace_per_100m), 1) for s in pace_sessions]

    chart2_labels = [str(s.date) for s in reversed(sessions) if s.distance_km]
    chart2_values = [round(float(s.distance_km) * 1000, 0) for s in reversed(sessions) if s.distance_km]

    breakdown_rows = [
        {'label': 'Under 500m', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km <= 0.5, Activity.distance_km > 0).count()},
        {'label': '500m – 1km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 0.5, Activity.distance_km <= 1).count()},
        {'label': '1km – 2km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 1, Activity.distance_km <= 2).count()},
        {'label': 'Over 2km', 'count': Activity.query.filter(Activity.user_id == user_id, Activity.exercise_type_id == sport_type.exercise_type_id, Activity.distance_km > 2).count()},
    ]

    personal_bests = [
        {'label': f'Best pace: {fmt_swim(best_pace_100m)}', 'sub': 'Per 100m', 'dot_class': ''},
        {'label': f'Longest swim: {round(longest, 1)} km', 'sub': 'Single session', 'dot_class': 'two'},
        {'label': f'{total_laps} total laps', 'sub': 'All time', 'dot_class': 'green'},
        {'label': f'{total_distance} km total', 'sub': 'All time', 'dot_class': 'amber'},
        {'label': f'{total_sessions} swims logged', 'sub': 'All time', 'dot_class': ''},
    ]

    return dict(
        tile1_value=fmt_swim(best_pace_100m),
        tile1_label='Best Pace /100m',
        tile2_value=f'{round(longest, 1)} km',
        tile2_label='Longest Swim',
        chart1_title='Pace per Session (sec/100m)',
        chart1_metric='Pace',
        chart1_unit='s',
        chart1_labels=chart1_labels,
        chart1_values=chart1_values,
        chart2_labels=chart2_labels,
        chart2_values=chart2_values,
        breakdown_title='Swims by Distance',
        breakdown_rows=breakdown_rows,
        personal_bests=personal_bests,
        total_sessions=total_sessions,
        total_distance=total_distance
    )


# maps URL slug to its configs and stats function
SPORT_THEMES = {
    'running': {'sport_name': 'Running', 'sport_icon': '🏃', 'hero_from': '#6d28d9', 'hero_to': '#db2777', 'accent': '#7c3aed', 'accent2': '#db2777', 'stats_fn': _running_stats},
    'walking': {'sport_name': 'Walking', 'sport_icon': '🚶', 'hero_from': '#065a82', 'hero_to': '#10b981', 'accent': '#10b981', 'accent2': '#065a82', 'stats_fn': _walking_stats},
    'cycling': {'sport_name': 'Cycling', 'sport_icon': '🚴', 'hero_from': '#b45309', 'hero_to': '#f59e0b', 'accent': '#f59e0b', 'accent2': '#b45309', 'stats_fn': _cycling_stats},
    'swimming': {'sport_name': 'Swimming', 'sport_icon': '🏊', 'hero_from': '#0e7490', 'hero_to': '#db2777', 'accent': '#22d3ee', 'accent2': '#db2777', 'stats_fn': _swimming_stats},
}


@sport_stats.route('/stats/<sport_slug>')
def sport_stats_page(sport_slug):
    from flask import session, redirect, url_for
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('auth.login'))

    user_id = user.user_id
    
    # check if the sport slug is valid before doing anything else
    theme = SPORT_THEMES.get(sport_slug.lower())
    if not theme:
        abort(404)

    sport_type = ExerciseType.query.filter_by(name=theme['sport_name']).first()
    if not sport_type:
        abort(404)

    current_streak = calc_streak(user_id, sport_type)
    daily_distances = get_daily_distances(user_id, sport_type)
    week_max = max(daily_distances) if any(daily_distances) else 1
    sport_data = theme['stats_fn'](user_id, sport_type)
    has_data = sport_data is not None

    return render_template(
        'sport_stats.html',
        sport_name=theme['sport_name'],
        sport_icon=theme['sport_icon'],
        hero_from=theme['hero_from'],
        hero_to=theme['hero_to'],
        accent=theme['accent'],
        accent2=theme['accent2'],
        has_data=has_data,
        current_streak=current_streak,
        week_daily=daily_distances,
        week_max=week_max,
        **(sport_data or {}),
    )