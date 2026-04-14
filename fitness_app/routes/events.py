"""
Events page routes for the FitTrack application.
Handles competition listing, event detail views,
calendar file downloads (.ics), and user registration
for upcoming competitions.
"""
from flask import Blueprint, render_template, redirect, url_for, make_response, flash
from fitness_app.extentions import db
from fitness_app.models import Competition, CompetitionResult, User
from datetime import date, timedelta

events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
def events_page():
    """Events page — upcoming competitions, calendar, next competition."""
    upcoming = Competition.query.filter(Competition.date >= date.today()).order_by(Competition.date).all()
    next_event = upcoming[0] if upcoming else None

    return render_template('events.html',
                           events=upcoming,
                           next_event=next_event)


@events_bp.route('/events/<int:competition_id>')
def event_details(competition_id):
    """View full details for a single competition/event."""
    competition = Competition.query.get_or_404(competition_id)

    # Check if current user is already registered
    current_user = User.query.filter_by(username='ahmed').first()
    is_registered = False
    if current_user:
        existing = CompetitionResult.query.filter_by(
            user_id=current_user.user_id, competition_id=competition.competition_id
        ).first()
        is_registered = existing is not None

    return render_template('event_details.html',
                           event=competition,
                           is_registered=is_registered)


@events_bp.route('/events/<int:competition_id>/calendar')
def add_to_calendar(competition_id):
    """Download an .ics calendar file for a competition."""
    competition = Competition.query.get_or_404(competition_id)

    # Build iCalendar (.ics) content
    event_date = competition.date.strftime('%Y%m%d')
    event_end = (competition.date + timedelta(days=1)).strftime('%Y%m%d')

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//FitTrack//Events//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART;VALUE=DATE:{event_date}\r\n"
        f"DTEND;VALUE=DATE:{event_end}\r\n"
        f"SUMMARY:{competition.name}\r\n"
        f"LOCATION:{competition.location}\r\n"
        f"DESCRIPTION:Distance: {competition.distance} km\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={competition.name.replace(" ", "_")}.ics'
    return response


@events_bp.route('/events/register/<int:competition_id>', methods=['POST'])
def register_event(competition_id):
    """Register the current user for a competition (create a placeholder result)."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username='ahmed').first()

    # Check if already registered
    existing = CompetitionResult.query.filter_by(
        user_id=current_user.user_id, competition_id=competition.competition_id
    ).first()

    if not existing:
        result = CompetitionResult(user_id=current_user.user_id,
                                   competition_id=competition.competition_id)
        db.session.add(result)
        db.session.commit()

    return redirect(url_for('events.event_details', competition_id=competition_id))


@events_bp.route('/events/unregister/<int:competition_id>', methods=['POST'])
def unregister_event(competition_id):
    """Unregister the current user from a competition."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username='ahmed').first()

    existing = CompetitionResult.query.filter_by(
        user_id=current_user.user_id, competition_id=competition.competition_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()

    return redirect(url_for('events.event_details', competition_id=competition_id))
