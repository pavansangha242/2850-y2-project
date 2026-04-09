# trainers.py
# personal trainers page logic

from flask import render_template, request, redirect, url_for, flash
from datetime import date
from database import get_db, get_current_user_id


# add demo trainers if the table is empty

def seed_trainers(db):
    """Insert demo trainer users + profiles if none exist yet."""
    c = db.cursor()
    c.execute("SELECT COUNT(*) as n FROM Trainer_Profile")
    if c.fetchone()['n'] > 0:
        return  

    demo = [
        ('john_smith',  'John',  'Smith', 'john@fittrack.com',  'Strength training coach',
         'Expert in powerlifting and muscle building. 8+ years coaching experience.',
         ['Strength & conditioning', 'Powerlifting', 'Muscle building', 'Nutrition planning'], 4.8),
        ('sarah_lee',   'Sarah', 'Lee',   'sarah@fittrack.com', 'Cardio specialist',
         'Cardio and endurance specialist. 6+ years coaching experience. Weight loss and endurance plans. Flexible online booking.',
         ['Cardio fitness', 'Weight loss', 'Endurance training', 'Online coaching'], 4.6),
        ('ahmed_ali',   'Ahmed', 'Ali',   'ahmed@fittrack.com', 'Cycling coach',
         'Professional cycling coach with race experience. Road, mountain and indoor cycling.',
         ['Road cycling', 'Mountain biking', 'Indoor training', 'Race preparation'], 5.0),
        ('emily_chen',  'Emily', 'Chen',  'emily@fittrack.com', 'Swimming trainer',
         'Competitive swimmer turned coach. Technique-focused approach for all levels.',
         ['Swim technique', 'Open water', 'Triathlon prep', 'All levels welcome'], 4.5),
    ]

    for username, first, last, email, specialty, bio, features, rating in demo:
        # create user with trainer role
        c.execute('''
            INSERT OR IGNORE INTO User
            (username, first_name, last_name, email, password, role, approved, join_date)
            VALUES (?, ?, ?, ?, 'trainerpass', 'trainer', 1, ?)
        ''', (username, first, last, email, date.today().isoformat()))

        user_row = c.execute("SELECT id FROM User WHERE username = ?", (username,)).fetchone()
        if not user_row:
            continue
        uid = user_row['id']

        c.execute('''
            INSERT OR IGNORE INTO Trainer_Profile
            (user_id, specialty, bio, average_rating, total_reviews)
            VALUES (?, ?, ?, ?, ?)
        ''', (uid, specialty, bio, rating, 0))

        # store features in the bio field using a separator
        full_bio = bio + '|||' + '|||'.join(features)
        c.execute("UPDATE Trainer_Profile SET bio = ? WHERE user_id = ?", (full_bio, uid))

    db.commit()


# helpers 

def parse_trainer(row):
    """Convert a db row into a dict with bio and features separated."""
    d = dict(row)
    parts = (d.get('bio') or '').split('|||')
    d['bio_text']  = parts[0] if parts else ''
    d['features']  = parts[1:] if len(parts) > 1 else []
    d['full_name'] = f"{d['first_name']} {d['last_name']}"
    return d


def ensure_message_table(db):
    db.execute('''
        CREATE TABLE IF NOT EXISTS Trainer_Message (
            message_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id    INTEGER NOT NULL,
            receiver_id  INTEGER NOT NULL,
            message      TEXT NOT NULL,
            sent_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read      INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sender_id)   REFERENCES User(id),
            FOREIGN KEY (receiver_id) REFERENCES User(id)
        )
    ''')
    db.commit()


# main page 

def show_trainers_page():
    db      = get_db()
    user_id = get_current_user_id()
    ensure_message_table(db)
    seed_trainers(db)

    # filter params
    search   = request.args.get('q', '').strip().lower()
    filter_  = request.args.get('filter', '')          
    selected = request.args.get('trainer_id', type=int) 

    # fetch all approved trainers with their profile
    trainers_raw = db.execute('''
        SELECT u.id, u.first_name, u.last_name,
               tp.specialty, tp.bio, tp.average_rating, tp.trainer_profile_id
        FROM User u
        JOIN Trainer_Profile tp ON u.id = tp.user_id
        WHERE u.role = 'trainer' AND u.approved = 1
        ORDER BY tp.average_rating DESC
    ''').fetchall()

    trainers = [parse_trainer(r) for r in trainers_raw]

    # apply search filter
    if search:
        trainers = [t for t in trainers if
                    search in t['full_name'].lower() or
                    search in t['specialty'].lower() or
                    search in t['bio_text'].lower()]

    # apply quick filter buttons
    if filter_ == 'top_rated':
        trainers = [t for t in trainers if t['average_rating'] >= 4.7]
    elif filter_ == 'strength':
        trainers = [t for t in trainers if 'strength' in t['specialty'].lower() or
                    any('strength' in f.lower() for f in t['features'])]
    elif filter_ == 'weight_loss':
        trainers = [t for t in trainers if 'weight' in t['bio_text'].lower() or
                    any('weight' in f.lower() for f in t['features'])]

    # selected trainer profile for the right panel
    profile_trainer = None
    if selected:
        p = db.execute('''
            SELECT u.id, u.first_name, u.last_name,
                   tp.specialty, tp.bio, tp.average_rating, tp.trainer_profile_id
            FROM User u
            JOIN Trainer_Profile tp ON u.id = tp.user_id
            WHERE u.id = ?
        ''', (selected,)).fetchone()
        if p:
            profile_trainer = parse_trainer(p)
    elif trainers:
        # default show first trainer's profile
        profile_trainer = trainers[0]

    # messages between current user and selected trainer
    messages = []
    if profile_trainer:
        tid = profile_trainer['id']
        messages = db.execute('''
            SELECT m.*, u.first_name, u.last_name
            FROM Trainer_Message m
            JOIN User u ON u.id = m.sender_id
            WHERE (m.sender_id = ? AND m.receiver_id = ?)
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.sent_at ASC
        ''', (user_id, tid, tid, user_id)).fetchall()

    # unread message count for nav badge
    unread = db.execute('''
        SELECT COUNT(*) as n FROM Trainer_Message
        WHERE receiver_id = ? AND is_read = 0
    ''', (user_id,)).fetchone()['n']

    # existing booking for this trainer
    booking = None
    if profile_trainer:
        booking = db.execute('''
            SELECT * FROM Session_Booking
            WHERE client_id = ? AND trainer_id = ? AND status != 'cancelled'
            ORDER BY date DESC LIMIT 1
        ''', (user_id, profile_trainer['id'])).fetchone()

    db.close()

    return render_template(
        'trainers.html',
        trainers=trainers,
        profile_trainer=profile_trainer,
        messages=messages,
        unread=unread,
        booking=booking,
        search=search,
        active_filter=filter_,
        current_user_id=user_id,
    )

# book session 

def book_session():
    db         = get_db()
    user_id    = get_current_user_id()
    trainer_id = request.form.get('trainer_id', type=int)
    book_date  = request.form.get('book_date')
    book_time  = request.form.get('book_time')
    notes      = request.form.get('notes', '')

    if not trainer_id or not book_date or not book_time:
        flash('Please fill in date and time to book a session.', 'error')
        return redirect(url_for('trainers') + f'?trainer_id={trainer_id}')

    # check for existing pending/confirmed booking
    existing = db.execute('''
        SELECT * FROM Session_Booking
        WHERE client_id = ? AND trainer_id = ? AND date = ? AND status != 'cancelled'
    ''', (user_id, trainer_id, book_date)).fetchone()

    if existing:
        flash('You already have a booking with this trainer on that date.', 'error')
    else:
        db.execute('''
            INSERT INTO Session_Booking (trainer_id, client_id, date, time, status, notes)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (trainer_id, user_id, book_date, book_time, notes))
        db.commit()
        flash('Session booked! Your trainer will confirm shortly.', 'success')

    db.close()
    return redirect(url_for('trainers') + f'?trainer_id={trainer_id}')


# send message

def send_message():
    db          = get_db()
    ensure_message_table(db)
    user_id     = get_current_user_id()
    trainer_id  = request.form.get('trainer_id', type=int)
    message_txt = request.form.get('message', '').strip()

    if not trainer_id or not message_txt:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('trainers') + f'?trainer_id={trainer_id}')

    db.execute('''
        INSERT INTO Trainer_Message (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (user_id, trainer_id, message_txt))
    db.commit()
    db.close()

    # stay on the same trainer profile after sending
    return redirect(url_for('trainers') + f'?trainer_id={trainer_id}')


# cancel booking 

def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute(
        'SELECT * FROM Session_Booking WHERE booking_id = ?', (booking_id,)
    ).fetchone()

    if booking:
        trainer_id = booking['trainer_id']
        db.execute(
            "UPDATE Session_Booking SET status = 'cancelled' WHERE booking_id = ?",
            (booking_id,)
        )
        db.commit()
        flash('Booking cancelled.', 'success')
        db.close()
        return redirect(url_for('trainers') + f'?trainer_id={trainer_id}')

    db.close()
    flash('Booking not found.', 'error')
    return redirect(url_for('trainers'))
