from datetime import date, timedelta

from flask import Blueprint, render_template, request, session, redirect, url_for
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import Activity, ExerciseType, User
progress = Blueprint('progress', __name__)


def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_sport_type(sport):
    if sport and sport != 'all':
        return ExerciseType.query.filter_by(name=sport).first()
    return None


def build_query(user_id, sport_type):
    query = Activity.query.filter_by(user_id=user_id)
    if sport_type:
        query = query.filter_by(exercise_type_id=sport_type.exercise_type_id)
    return query


@progress.route("/progress")
def progress_page():
    username = session.get("username")

    if not username:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=username).first()

    if not user:
        return redirect(url_for("auth.login"))

    uid = user.user_id
    selected_sport = request.args.get('sport', 'all')
    sport_type     = get_sport_type(selected_sport)
    query          = build_query(uid, sport_type)

    total_sessions = query.count()
    has_data       = total_sessions > 0

    if has_data:
        # build filter list so we can reuse it cleanly
        sport_filter = [Activity.exercise_type_id == sport_type.exercise_type_id] if sport_type else []

        total_distance = round(db.session.query(
            func.coalesce(func.sum(Activity.distance_km), 0)
        ).filter(Activity.user_id == uid, *sport_filter).scalar() or 0, 1)

        best_pace = db.session.query(func.min(Activity.pace_per_km)).filter(
            Activity.user_id == uid,
            Activity.pace_per_km > 0,
            *sport_filter
        ).scalar()

        longest_run = db.session.query(func.max(Activity.distance_km)).filter(
            Activity.user_id == uid, *sport_filter
        ).scalar()
        if longest_run:
            longest_run = round(longest_run, 1)

        total_calories = db.session.query(
            func.coalesce(func.sum(Activity.calories), 0)
        ).filter(Activity.user_id == uid, *sport_filter).scalar() or 0
        chart_labels = []
        chart_pace_values = []
        
        if selected_sport == 'Swimming':
            pace_data = (
                query.filter(Activity.pace_per_100m > 0)
                .order_by(Activity.date.desc())
                .limit(8)
                .all()
            )

            pace_data = list(reversed(pace_data))

            for session_row in pace_data:
                chart_labels.append(
                    session_row.notes[:10] if session_row.notes else str(session_row.date)
                )
                val = float(session_row.pace_per_100m)
                chart_pace_values.append(round(val, 1))

        else:
            pace_data = (
                query.filter(
                    Activity.distance_km > 0,
                    Activity.duration_minutes > 0
                )
                .order_by(Activity.date.desc())
                .limit(8)
                .all()
            )

            pace_data = list(reversed(pace_data))

            for session_row in pace_data:
                chart_labels.append(
                    session_row.notes[:10] if session_row.notes else str(session_row.date)
                )

                if selected_sport == 'Cycling':
                    hours = session_row.duration_minutes / 60
                    val = session_row.distance_km / hours if hours > 0 else 0
                else:
                    val = session_row.duration_minutes / session_row.distance_km

                chart_pace_values.append(round(val, 2))

            if chart_pace_values:
                if selected_sport == "Cycling":
                    best_pace = max(chart_pace_values)
                else:
                    best_pace = min(chart_pace_values)

        dist_data     = query.filter(Activity.distance_km > 0).order_by(Activity.date.desc()).limit(8).all()
        dist_data     = list(reversed(dist_data))
        chart2_labels = [str(s.date) for s in dist_data]
        chart2_values = [round(float(s.distance_km), 2) for s in dist_data]

        # donut chart, only shown on all tab
        if selected_sport == 'all':
            sport_data = db.session.query(
                ExerciseType.name, func.sum(Activity.distance_km)
            ).join(Activity, Activity.exercise_type_id == ExerciseType.exercise_type_id
            ).filter(Activity.user_id == uid, Activity.distance_km > 0
            ).group_by(ExerciseType.name).all()
            sport_labels    = [r[0] for r in sport_data]
            sport_distances = [round(r[1], 1) for r in sport_data]
        else:
            sport_labels, sport_distances = [], []

        # last 8 weeks activity count
        weekly_labels, weekly_counts = [], []
        for i in range(7, -1, -1):
            week_start = get_week_start() - timedelta(weeks=i)
            week_end   = week_start + timedelta(days=6)
            count      = query.filter(Activity.date >= week_start, Activity.date <= week_end).count()
            weekly_labels.append(f'W{8-i}')
            weekly_counts.append(count)

        # distance per day this week
        monday = get_week_start()
        daily_distances = []
        for i in range(7):
            day = monday + timedelta(days=i)
            km  = db.session.query(func.coalesce(func.sum(Activity.distance_km), 0)).filter(
                Activity.user_id == uid, Activity.date == day, *sport_filter
            ).scalar() or 0
            daily_distances.append(round(float(km), 1))
        week_max_km = max(daily_distances) if any(daily_distances) else 1

        # count streak
        streak = 0
        all_dates = db.session.query(Activity.date).filter(
            Activity.user_id == uid, *sport_filter
        ).distinct().order_by(Activity.date.desc()).all()
        if all_dates:
            check = date.today()
            for (activity_date,) in all_dates:
                if activity_date == check:
                    streak += 1
                    check -= timedelta(days=1)
                elif activity_date == check - timedelta(days=1):
                    streak += 1
                    check = activity_date - timedelta(days=1)
                else:
                    break
    else:
        total_distance = 0; best_pace = None; longest_run = None
        total_calories = 0; chart_labels = []; chart_pace_values = []
        chart2_labels = []; chart2_values = []; sport_labels = []
        sport_distances = []; weekly_labels = []; weekly_counts = []
        daily_distances = [0]*7; week_max_km = 1; streak = 0

    return render_template('progress.html',
        active_sport=selected_sport, has_data=has_data,
        total_sessions=total_sessions, total_distance=total_distance,
        best_pace=best_pace, longest_run=longest_run,
        total_calories=total_calories, chart_labels=chart_labels,
        chart_pace_values=chart_pace_values, chart2_labels=chart2_labels,
        chart2_values=chart2_values, sport_labels=sport_labels,
        sport_distances=sport_distances, weekly_labels=weekly_labels,
        weekly_counts=weekly_counts, week_daily_km=daily_distances,
        week_max_km=week_max_km, current_streak=streak,
    )