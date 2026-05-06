"""
Events page routes for the FitTrack application.
Handles competition listing, event detail views,
calendar file downloads (.ics), user registration,
and group chat for upcoming competitions.
"""
from flask import Blueprint, render_template, redirect, url_for, make_response, flash, request, jsonify, session
from fitness_app.extensions import db
from fitness_app.models import Competition, CompetitionResult, User, ChatMessage
from datetime import date, datetime, timedelta

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
    current_user = User.query.filter_by(username=session.get('username')).first()
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
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        flash('You must be logged in to register.', 'error')
        return redirect(url_for('auth.login'))
 
    # Check if already registered
    existing = CompetitionResult.query.filter_by(
        user_id=current_user.user_id, competition_id=competition.competition_id
    ).first()
 
    if not existing:
        result = CompetitionResult(user_id=current_user.user_id,
                                   competition_id=competition.competition_id)
        db.session.add(result)
        db.session.commit()
        flash('Registered successfully! A confirmation has been sent to your email.', 'success')
 
    return redirect(url_for('events.event_details', competition_id=competition_id))


@events_bp.route('/events/unregister/<int:competition_id>', methods=['POST'])
def unregister_event(competition_id):
    """Unregister the current user from a competition."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        return redirect(url_for('auth.login'))
 
    existing = CompetitionResult.query.filter_by(
        user_id=current_user.user_id, competition_id=competition.competition_id
    ).first()
 
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('You have been unregistered from this event.', 'info')
 
    return redirect(url_for('events.event_details', competition_id=competition_id))


@events_bp.route('/events/<int:competition_id>/chat')
def event_chat(competition_id):
    """Group chat page for a specific competition/event."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        return redirect(url_for('auth.login'))
 
    messages = ChatMessage.query.filter_by(competition_id=competition_id) \
        .order_by(ChatMessage.timestamp.asc()).all()
 
    return render_template('event_chat.html',
                           event=competition,
                           messages=messages,
                           current_user=current_user)


@events_bp.route('/events/<int:competition_id>/chat/send', methods=['POST'])
def send_message(competition_id):
    """Send a new chat message to the event group chat."""
    competition = Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        return redirect(url_for('auth.login'))
 
    content = request.form.get('message', '').strip()
    if content:
        msg = ChatMessage(
            competition_id=competition.competition_id,
            user_id=current_user.user_id,
            content=content,
            timestamp=datetime.utcnow()
        )
        db.session.add(msg)
        db.session.commit()
 
    return redirect(url_for('events.event_chat', competition_id=competition_id))


@events_bp.route('/events/<int:competition_id>/chat/messages')
def get_messages(competition_id):
    """JSON endpoint for polling new chat messages."""
    Competition.query.get_or_404(competition_id)
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        return jsonify([]), 401
 
    after_id = request.args.get('after', 0, type=int)
 
    messages = ChatMessage.query.filter_by(competition_id=competition_id) \
        .filter(ChatMessage.message_id > after_id) \
        .order_by(ChatMessage.timestamp.asc()).all()
 
    return jsonify([
        {
            'id': m.message_id,
            'author': m.author.first_name,
            'author_role': m.author.role,
            'user_id': m.user_id,
            'content': m.content,
            'time': m.timestamp.strftime('%H:%M'),
            'is_mine': m.user_id == current_user.user_id
        }
        for m in messages
    ])


@events_bp.route('/events/chat/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    """Delete a chat message (only the author can delete their own)."""
    current_user = User.query.filter_by(username=session.get('username')).first()
    if not current_user:
        return jsonify({'status': 'not logged in'}), 401
        
    msg = ChatMessage.query.get_or_404(message_id)
 
    if msg.user_id == current_user.user_id:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'status': 'deleted'})
 
    return jsonify({'status': 'not allowed'}), 403
