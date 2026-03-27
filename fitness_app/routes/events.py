from flask import Blueprint, render_template, redirect, url_for
from fitness_app.extentions import db
from fitness_app.models import Competition, CompetitionResult, User
from datetime import date

events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
def events_page():
    """Events page — upcoming competitions, calendar, next competition."""
    upcoming = Competition.query.filter(Competition.date >= date.today()).order_by(Competition.date).all()
    next_event = upcoming[0] if upcoming else None

    return render_template('events.html',
                           events=upcoming,
                           next_event=next_event)


@events_bp.route('/events/register/<int:competition_id>', methods=['POST'])
def register_event(competition_id):
    """Register the current user for a competition (create a placeholder result)."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username='alex').first()

    # Check if already registered
    existing = CompetitionResult.query.filter_by(
        user_id=current_user.user_id, competition_id=competition.competition_id
    ).first()

    if not existing:
        result = CompetitionResult(user_id=current_user.user_id,
                                   competition_id=competition.competition_id)
        db.session.add(result)
        db.session.commit()

    return redirect(url_for('events.events_page'))
