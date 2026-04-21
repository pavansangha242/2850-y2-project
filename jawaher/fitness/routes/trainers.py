
from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from fitness.extentions import db
from fitness.models import User, TrainerProfile, SessionBooking, TrainerMessage

trainers = Blueprint('trainers', __name__)


# add 4 demo trainers if there are none yet
def seed_trainers():
    if TrainerProfile.query.count() > 0:
        return

    demo = [
        ('john_smith', 'John', 'Smith', 'john@fittrack.com', 'Strength training coach',
         '8+ years coaching experience.|||Strength & conditioning|||Powerlifting|||Muscle building|||Nutrition planning', 4.8),
        ('sarah_lee', 'Sarah', 'Lee', 'sarah@fittrack.com', 'Cardio specialist',
         '6+ years coaching experience.|||Cardio fitness|||Weight loss|||Endurance training|||Online coaching', 4.6),
        ('ahmed_ali', 'Ahmed', 'Ali', 'ahmed@fittrack.com', 'Cycling coach',
         'Professional cycling coach.|||Road cycling|||Mountain biking|||Indoor training|||Race preparation', 5.0),
        ('emily_chen', 'Emily', 'Chen', 'emily@fittrack.com', 'Swimming trainer',
         'Competitive swimmer turned coach.|||Swim technique|||Open water|||Triathlon prep|||All levels welcome', 4.5),
    ]

    for username, first, last, email, specialty, bio, rating in demo:
        existing = User.query.filter_by(username=username).first()

        if not existing:
            u = User(
                username=username,
                first_name=first,
                last_name=last,
                email=email,
                role='pt',
                approved=True,
                join_date=date.today()
            )
            u.set_password('trainerpass')
            db.session.add(u)
            db.session.flush()
            uid = u.user_id
        else:
            uid = existing.user_id

        if not TrainerProfile.query.filter_by(user_id=uid).first():
            tp = TrainerProfile(
                user_id=uid,
                specialty=specialty,
                bio=bio,
                average_rating=rating,
                total_reviews=0
            )
            db.session.add(tp)

    db.session.commit()


# turn trainer data into one dictionary for thr template
def parse_trainer(user, profile):
    parts = (profile.bio or '').split('|||')
    return {
        'id': user.user_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': f'{user.first_name} {user.last_name}',
        'specialty': profile.specialty,
        'bio_text': parts[0] if parts else '',
        'features': parts[1:] if len(parts) > 1 else [],
        'average_rating': profile.average_rating,
    }


@trainers.route('/trainers')
def trainers_page():
    user = User.query.first()
    if not user:
        return "No users found in database."

    uid = user.user_id
    seed_trainers()

    search = request.args.get('q', '').strip().lower()
    filter_ = request.args.get('filter', '')
    selected = request.args.get('trainer_id', type=int)

    # get all approved trainers and sort the, by rating
    trainers_raw = db.session.query(
        User, TrainerProfile
    ).join(
        TrainerProfile, User.user_id == TrainerProfile.user_id
    ).filter(
        User.role == 'pt',
        User.approved == True
    ).order_by(
        TrainerProfile.average_rating.desc()
    ).all()

    trainer_list = [parse_trainer(u, tp) for u, tp in trainers_raw]

    if search:
        trainer_list = [
            t for t in trainer_list
            if search in t['full_name'].lower() or search in t['specialty'].lower()
        ]

    if filter_ == 'top_rated':
        trainer_list = [t for t in trainer_list if t['average_rating'] >= 4.7]
    elif filter_ == 'strength':
        trainer_list = [
            t for t in trainer_list
            if 'strength' in t['specialty'].lower()
            or any('strength' in f.lower() for f in t['features'])
        ]
    elif filter_ == 'weight_loss':
        trainer_list = [
            t for t in trainer_list
            if any('weight' in f.lower() for f in t['features'])
        ]

    # choose which trainer profile to show
    profile_trainer = None
    if selected:
        row = db.session.query(
            User, TrainerProfile
        ).join(
            TrainerProfile, User.user_id == TrainerProfile.user_id
        ).filter(
            User.user_id == selected
        ).first()

        if row:
            profile_trainer = parse_trainer(*row)

    elif trainer_list:
        profile_trainer = trainer_list[0]

    messages = []
    booking = None

    if profile_trainer:
        tid = profile_trainer['id']

        # get chat between the user and PT
        messages = TrainerMessage.query.filter(
            db.or_(
                db.and_(TrainerMessage.sender_id == uid, TrainerMessage.receiver_id == tid),
                db.and_(TrainerMessage.sender_id == tid, TrainerMessage.receiver_id == uid)
            )
        ).order_by(TrainerMessage.sent_at.asc()).all()

        # get the lastest booking thats not cancelled
        booking = SessionBooking.query.filter(
            SessionBooking.client_id == uid,
            SessionBooking.trainer_id == tid,
            SessionBooking.status != 'cancelled'
        ).order_by(SessionBooking.date.desc()).first()

    # count the unread messages for this user
    unread = TrainerMessage.query.filter_by(receiver_id=uid, is_read=False).count()

    return render_template(
        'trainers.html',
        trainers=trainer_list,
        profile_trainer=profile_trainer,
        messages=messages,
        unread=unread,
        booking=booking,
        search=search,
        active_filter=filter_,
        current_user_id=uid,
    )


@trainers.route('/trainers/book', methods=['POST'])
def book_session():
    user = User.query.first()
    if not user:
        return "No users found in database."

    uid = user.user_id
    trainer_id = request.form.get('trainer_id', type=int)
    book_date = request.form.get('book_date')
    book_time = request.form.get('book_time')
    notes = request.form.get('notes', '')

    if not trainer_id or not book_date or not book_time:
        flash('Please fill in date and time.', 'error')
        return redirect(url_for('trainers.trainers_page') + f'?trainer_id={trainer_id}')

    parsed_date = datetime.strptime(book_date, '%Y-%m-%d').date()

    # check for an existing booking on the same date
    existing = SessionBooking.query.filter_by(
        client_id=uid,
        trainer_id=trainer_id,
        date=parsed_date
    ).filter(
        SessionBooking.status != 'cancelled'
    ).first()

    if existing:
        flash('You already have a booking on that date.', 'error')
    else:
        b = SessionBooking(
            trainer_id=trainer_id,
            client_id=uid,
            date=parsed_date,
            time=book_time,
            status='pending',
            notes=notes
        )
        db.session.add(b)
        db.session.commit()
        flash('Session booked! Your trainer will confirm shortly.', 'success')

    return redirect(url_for('trainers.trainers_page') + f'?trainer_id={trainer_id}')


@trainers.route('/trainers/message', methods=['POST'])
def send_message():
    user = User.query.first()
    if not user:
        return "No users found in database."

    uid = user.user_id
    trainer_id = request.form.get('trainer_id', type=int)
    message_txt = request.form.get('message', '').strip()

    if not trainer_id or not message_txt:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('trainers.trainers_page') + f'?trainer_id={trainer_id}')

    # save the new message
    msg = TrainerMessage(
        sender_id=uid,
        receiver_id=trainer_id,
        message=message_txt
    )
    db.session.add(msg)
    db.session.commit()

    return redirect(url_for('trainers.trainers_page') + f'?trainer_id={trainer_id}')


@trainers.route('/trainers/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    b = SessionBooking.query.get(booking_id)

    if b:
        trainer_id = b.trainer_id
        b.status = 'cancelled'
        db.session.commit()
        flash('Booking cancelled.', 'success')
        return redirect(url_for('trainers.trainers_page') + f'?trainer_id={trainer_id}')

    flash('Booking not found.', 'error')
    return redirect(url_for('trainers.trainers_page'))