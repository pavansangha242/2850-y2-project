"""
Events page routes for the FitTrack application.
Handles competition listing, event detail views,
calendar file downloads (.ics), user registration,
and group chat for upcoming competitions.
"""
from flask import Blueprint, render_template, redirect, url_for, make_response, flash, request, jsonify, session
from fitness_app.extentions import db
from fitness_app.models import Competition, CompetitionResult, User, ChatMessage
from datetime import date, datetime, timedelta
import random

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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()
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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

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
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

    after_id = request.args.get('after', 0, type=int)

    messages = ChatMessage.query.filter_by(competition_id=competition_id) \
        .filter(ChatMessage.message_id > after_id) \
        .order_by(ChatMessage.timestamp.asc()).all()

    return jsonify([
        {
            'id': m.message_id,
            'author': m.author.first_name,
            'content': m.content,
            'time': m.timestamp.strftime('%H:%M'),
            'is_mine': m.user_id == current_user.user_id
        }
        for m in messages
    ])


@events_bp.route('/events/chat/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    """Delete a chat message (only the author can delete their own)."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()
    msg = ChatMessage.query.get_or_404(message_id)

    if msg.user_id == current_user.user_id:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'status': 'deleted'})

    return jsonify({'status': 'not allowed'}), 403

@events_bp.route('/events/<int:competition_id>/chat/auto-reply', methods=['POST'])
def auto_reply(competition_id):
    """Generate a keyword-based reply from another user so responses feel natural."""
    competition = Competition.query.get_or_404(competition_id)
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401 if request.is_json else redirect(url_for('auth.login'))
    current_user = User.query.filter_by(username=username).first()

    # Pick a random other user to reply
    other_users = User.query.filter(
        User.username != username,
        User.role == 'customer'
    ).all()

    if not other_users:
        return jsonify({'status': 'no users'}), 200

    replier = random.choice(other_users)

    # Get the last message the current user sent
    last_msg = ChatMessage.query.filter_by(
        competition_id=competition_id, user_id=current_user.user_id
    ).order_by(ChatMessage.timestamp.desc()).first()

    user_text = last_msg.content.lower() if last_msg else ''

    # Keyword-based reply mapping
    keyword_replies = {
        'hi': [
            'Hey! How are you? 👋',
            'Hi there! Excited for the event?',
            'Hello! Great to see everyone here',
        ],
        'hello': [
            'Hey! Welcome to the group 😊',
            'Hello! Good to have you here',
            'Hi! Are you training for this one?',
        ],
        'ready': [
            'So ready! Been training all month 💪',
            'Readyyy lets gooo! 🔥',
            'Born ready! Can not wait honestly',
        ],
        'excited': [
            'Same here! This is going to be amazing 🎉',
            'The excitement is real!! Lets do this',
            'So excited! Best event of the year',
        ],
        'train': [
            'Training has been going great, feeling strong',
            'I have been doing 5 sessions a week lately',
            'Yeah my training plan is going well so far!',
        ],
        'nervous': [
            'Don not worry we are all in this together! 💪',
            'A little nervous too but it will be fun!',
            'Totally normal! Just enjoy the experience 😊',
        ],
        'time': [
            'I am aiming for a personal best this time!',
            'Hoping to finish under 3 hours 🤞',
            'Not worried about time, just want to finish strong',
        ],
        'weather': [
            'Heard it should be nice! Perfect running weather ☀️',
            'Hopefully no rain, fingers crossed 🤞',
            'The forecast looks great for it!',
        ],
        'good luck': [
            'Thanks! Good luck to you too! 🍀',
            'You too! We are all gonna smash it',
            'Appreciate it! Let us all do our best 💪',
        ],
        'meet': [
            'Yeah let us meet at the starting line!',
            'Great idea! We can warm up together',
            'I will be there early, look for me near the front!',
        ],
        'food': [
            'I am bringing energy bars for everyone 😂',
            'There is a cafe near the finish line!',
            'Post-race pizza is a must honestly 🍕',
        ],
        'water': [
            'Stay hydrated! Super important 💧',
            'I am bringing my water bottle for sure',
            'There should be water stations along the route',
        ],
        'can\'t wait': [
            'Same! The countdown is on 🔥',
            'Neither can I! Going to be so good',
            'It is coming up so fast, so hyped!',
        ],
        'how': [
            'Doing good! Just keeping up with training',
            'All good here, getting prepared every day',
            'Great thanks! How about you?',
        ],
        'route': [
            'I checked it out, looks like a nice course!',
            'The route goes through the city centre I think',
            'Has anyone done a practice run on the route?',
        ],
        'tip': [
            'Start slow and build up, don not burn out early!',
            'Make sure to stretch properly before 🧘',
            'Eat a good breakfast, you will need the energy',
        ],
    }

    # Find the best matching keyword
    content = None
    for keyword, responses in keyword_replies.items():
        if keyword in user_text:
            content = random.choice(responses)
            break

    # Fallback if no keyword matched
    if content is None:
        fallback = [
            'Yeah definitely! 👍',
            'That is a great point!',
            'Agreed! Let us keep pushing 💪',
            'For sure! Can not wait for the event',
            'Haha nice one 😂',
            'So true! This group is great',
        ]
        content = random.choice(fallback)

    msg = ChatMessage(
        competition_id=competition.competition_id,
        user_id=replier.user_id,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'status': 'ok', 'author': replier.first_name})
