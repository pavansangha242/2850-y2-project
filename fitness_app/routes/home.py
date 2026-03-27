from flask import Blueprint, render_template
from fitness_app.extentions import db
from fitness_app.models import User, Activity, ExerciseType
from datetime import date, timedelta

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def index():
    """Home page — dashboard with today's summary, quick actions, recommended activities."""
    # For now, use the sample user "Alex"
    current_user = User.query.filter_by(username='alex').first()

    # Today's summary
    today = date.today()
    today_activities = Activity.query.filter_by(user_id=current_user.user_id, date=today).all() if current_user else []

    total_steps = 0
    total_calories = sum(a.calories for a in today_activities)
    total_distance = sum(a.distance_km for a in today_activities)

    # Workouts this week (count of activity entries in the last 7 days)
    week_start = today - timedelta(days=today.weekday())
    workouts_this_week = Activity.query.filter(
        Activity.user_id == current_user.user_id,
        Activity.date >= week_start
    ).count() if current_user else 0

    return render_template('home.html',
                           user=current_user,
                           total_calories=total_calories,
                           total_distance=total_distance,
                           workouts_this_week=workouts_this_week)
