from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from fitness_app.extensions import db
from fitness_app.models import Activity, ExerciseType, User

history = Blueprint('history', __name__)

PER_PAGE = 10


@history.route('/history')
def history_page():
    user = User.query.first()
    if not user:
        return "No users found in database."

    uid = user.user_id
    selected_sport = request.args.get('sport', 'all')
    current_page = int(request.args.get('page', 1))
    offset = (current_page - 1) * PER_PAGE

    # join sport name so template can access it
    query = db.session.query(
        Activity,
        ExerciseType.name.label('sport_name')
    ).join(
        ExerciseType,
        Activity.exercise_type_id == ExerciseType.exercise_type_id
    ).filter(
        Activity.user_id == uid
    )

    if selected_sport and selected_sport != 'all':
        query = query.filter(ExerciseType.name == selected_sport)

    total_count = query.count()
    rows = query.order_by(
        Activity.date.desc()
    ).limit(PER_PAGE).offset(offset).all()

    # convert rows to dicts so the template can access sport_name easily
    activities = []
    for act, sport_name in rows:
        activity_dict = {c.name: getattr(act, c.name) for c in act.__table__.columns}
        activity_dict['sport_name'] = sport_name
        activities.append(activity_dict)

    # avoid querying sport twice
    sport_type = ExerciseType.query.filter_by(name=selected_sport).first() if selected_sport != 'all' else None
    sport_filter = [Activity.exercise_type_id == sport_type.exercise_type_id] if sport_type else []

    best_pace = db.session.query(
        func.min(Activity.pace_per_km)
    ).filter(
        Activity.user_id == uid,
        Activity.pace_per_km > 0,
        *sport_filter
    ).scalar()

    longest_run = db.session.query(
        func.max(Activity.distance_km)
    ).filter(
        Activity.user_id == uid,
        *sport_filter
    ).scalar()

    best_pace_shown = round(best_pace, 1) if best_pace else None
    longest_shown = round(longest_run, 1) if longest_run else None
    total_pages = max(1, -(-total_count // PER_PAGE))

    return render_template(
        'history.html',
        activities=activities,
        active_sport=selected_sport,
        current_page=current_page,
        total_pages=total_pages,
        best_pace_shown=best_pace_shown,
        longest_shown=longest_shown,
    )


@history.route('/history/delete/<int:activity_id>', methods=['POST'])
def delete_activity(activity_id):
    act = Activity.query.get(activity_id)
    if act:
        db.session.delete(act)
        db.session.commit()

    flash('Session deleted.', 'success')
    return redirect(url_for('history.history_page'))