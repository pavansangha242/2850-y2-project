"""
Leaderboard page routes for the FitTrack application.
Ranks users by the number of workouts completed in the
current week, along with total calories and distance.
Supports filtering by time period (week, month, all time).
"""
from flask import Blueprint, render_template, request, session, redirect, url_for
from fitness_app.extentions import db
from fitness_app.models import User, Activity
from datetime import date, timedelta
from sqlalchemy import func

leaderboard_bp = Blueprint('leaderboard', __name__)


@leaderboard_bp.route('/leaderboard')
def leaderboard_page():
    """Leaderboard page — rank users by workouts in the selected period."""
    period = request.args.get('period', 'week')

    # Work out the start date based on the selected period
    today = date.today()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'month':
        start_date = today.replace(day=1)
    else:
        start_date = date(2000, 1, 1)  # All time

    # Query: count workouts, total calories, total distance per user
    rankings = (
        db.session.query(
            User.user_id,
            User.first_name,
            User.last_name,
            User.username,
            func.count(Activity.activity_id).label('workout_count'),
            func.coalesce(func.sum(Activity.calories), 0).label('total_calories'),
            func.coalesce(func.sum(Activity.distance_km), 0).label('total_distance')
        )
        .outerjoin(Activity, (User.user_id == Activity.user_id) & (Activity.date >= start_date))
        .filter(User.role == 'customer')
        .group_by(User.user_id)
        .order_by(
            func.count(Activity.activity_id).desc(),
            func.coalesce(func.sum(Activity.distance_km), 0).desc(),
            func.coalesce(func.sum(Activity.calories), 0).desc()
        )
        .all()
    )

    # Get the current user to highlight their row
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

    return render_template('leaderboard.html',
                           rankings=rankings,
                           period=period,
                           current_user=current_user)
