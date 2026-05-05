"""
Home page routes for the FitTrack application.
Handles the main dashboard view with today's summary
statistics (calories, distance), weekly workout count,
quick actions, and recommended activities.
"""
from flask import Blueprint, render_template, session, redirect, url_for
from fitness_app.models import User, Activity
from datetime import date, timedelta

home_bp = Blueprint('home', __name__)


@home_bp.route('/home')
def index():
    """Home page — dashboard with today's summary, quick actions, recommended activities."""
    # Check if user is logged in
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()


    if not current_user:
        session.pop("username", None)
        return redirect(url_for('auth.login'))

    # Today's summary
    today = date.today()
    today_activities = Activity.query.filter_by(user_id=current_user.user_id, date=today).all()

    total_calories = sum((a.calories or 0) for a in today_activities)
    total_distance = sum((a.distance_km or 0) for a in today_activities)

    # Workouts this week (count of activity entries in the last 7 days)
    week_start = today - timedelta(days=today.weekday())
    workouts_this_week = Activity.query.filter(
        Activity.user_id == current_user.user_id,
        Activity.date >= week_start
    ).count()

    return render_template('home.html',
                           user=current_user,
                           total_calories=total_calories,
                           total_distance=total_distance,
                           workouts_this_week=workouts_this_week)
