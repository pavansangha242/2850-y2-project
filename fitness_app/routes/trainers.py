from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from fitness_app.extensions import db
from fitness_app.models import (
    GymAssignment,
    GymExercise,
    SessionBooking,
    TrainerMessage,
    TrainerProfile,
    TrainingClient,
    User,
)

trainers = Blueprint("trainers", __name__)


def get_logged_in_user():
    username = session.get("username")

    if not username:
        return None
    return User.query.filter_by(username=username).first()


def ensure_trainer_profile(user):
    if not user or user.role != "pt":
        return None

    profile = TrainerProfile.query.filter_by(user_id=user.user_id).first()
    if profile:
        return profile

    profile = TrainerProfile(
        user_id=user.user_id,
        specialty="Personal Trainer",
        bio=user.bio
        or "Certified personal trainer.|||Gym training|||Fitness coaching|||Workout plans",
        average_rating=0,
        total_reviews=0,
    )

    db.session.add(profile)
    db.session.commit()
    return profile


# turn trainer data into one dictionary for thr template
def parse_trainer(user, profile):
    parts = (profile.bio or "").split("|||")
    return {
        "id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
        "specialty": profile.specialty,
        "bio_text": parts[0] if parts else "",
        "features": parts[1:] if len(parts) > 1 else [],
        "average_rating": profile.average_rating,
    }


@trainers.route("/trainers")
def trainers_page():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    uid = user.user_id

    if user.role == "pt":
        ensure_trainer_profile(user)

    search = request.args.get("q", "").strip().lower()
    filter_ = request.args.get("filter", "")
    selected = request.args.get("trainer_id", type=int)

    # get all approved trainers and sort the, by rating
    trainers_raw = (
        db.session.query(User, TrainerProfile)
        .join(TrainerProfile, User.user_id == TrainerProfile.user_id)
        .filter(User.role == "pt", User.approved)
        .order_by(TrainerProfile.average_rating.desc())
        .all()
    )

    trainer_list = [parse_trainer(u, tp) for u, tp in trainers_raw]

    if search:
        trainer_list = [
            t
            for t in trainer_list
            if search in t["full_name"].lower() or search in t["specialty"].lower()
        ]

    if filter_ == "top_rated":
        trainer_list = [t for t in trainer_list if t["average_rating"] >= 4.7]
    elif filter_ == "strength":
        trainer_list = [
            t
            for t in trainer_list
            if "strength" in t["specialty"].lower()
            or any("strength" in f.lower() for f in t["features"])
        ]
    elif filter_ == "weight_loss":
        trainer_list = [
            t for t in trainer_list if any("weight" in f.lower() for f in t["features"])
        ]

    # choose which trainer profile to show
    profile_trainer = None
    if selected:
        row = (
            db.session.query(User, TrainerProfile)
            .join(TrainerProfile, User.user_id == TrainerProfile.user_id)
            .filter(User.user_id == selected)
            .first()
        )

        if row:
            profile_trainer = parse_trainer(*row)

    elif trainer_list:
        profile_trainer = trainer_list[0]

    messages = []
    booking = None

    if profile_trainer:
        tid = profile_trainer["id"]

        # get chat between the user and PT
        messages = (
            TrainerMessage.query.filter(
                db.or_(
                    db.and_(
                        TrainerMessage.sender_id == uid,
                        TrainerMessage.receiver_id == tid,
                    ),
                    db.and_(
                        TrainerMessage.sender_id == tid,
                        TrainerMessage.receiver_id == uid,
                    ),
                )
            )
            .order_by(TrainerMessage.sent_at.asc())
            .all()
        )

        # get the lastest booking thats not cancelled
        booking = (
            SessionBooking.query.filter(
                SessionBooking.client_id == uid,
                SessionBooking.trainer_id == tid,
                SessionBooking.status != "cancelled",
            )
            .order_by(SessionBooking.date.desc())
            .first()
        )

    # count the unread messages for this user
    unread = TrainerMessage.query.filter_by(receiver_id=uid, is_read=False).count()

    return render_template(
        "trainers.html",
        trainers=trainer_list,
        profile_trainer=profile_trainer,
        messages=messages,
        unread=unread,
        booking=booking,
        search=search,
        active_filter=filter_,
        current_user_id=uid,
    )


@trainers.route("/trainers/book", methods=["POST"])
def book_session():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for("auth.login"))

    uid = user.user_id

    trainer_id = request.form.get("trainer_id", type=int)
    book_date = request.form.get("book_date")
    book_time = request.form.get("book_time")
    notes = request.form.get("notes", "")

    if not trainer_id or not book_date or not book_time:
        flash("Please fill in date and time.", "error")
        return redirect(url_for("trainers.trainers_page") + f"?trainer_id={trainer_id}")

    trainer_user = User.query.filter_by(user_id=trainer_id, role="pt").first()

    if not trainer_user:
        flash("Trainer not found.", "error")
        return redirect(url_for("trainers.trainers_page"))

    parsed_date = datetime.strptime(book_date, "%Y-%m-%d").date()

    # check for an existing booking on the same date
    existing = (
        SessionBooking.query.filter_by(
            client_id=uid, trainer_id=trainer_id, date=parsed_date
        )
        .filter(SessionBooking.status != "cancelled")
        .first()
    )

    if existing:
        flash("You already have a booking on that date.", "error")
    else:
        b = SessionBooking(
            trainer_id=trainer_id,
            client_id=uid,
            date=parsed_date,
            time=book_time,
            status="pending",
            notes=notes,
        )
        db.session.add(b)
        db.session.commit()
        flash("Session booked! Your trainer will confirm shortly.", "success")

    return redirect(url_for("trainers.trainers_page") + f"?trainer_id={trainer_id}")


@trainers.route("/trainers/message", methods=["POST"])
def send_message():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    uid = user.user_id
    trainer_id = request.form.get("trainer_id", type=int)
    message_txt = request.form.get("message", "").strip()

    if not trainer_id or not message_txt:
        flash("Message cannot be empty.", "error")
        return redirect(url_for("trainers.trainers_page") + f"?trainer_id={trainer_id}")

    # save the new message
    msg = TrainerMessage(sender_id=uid, receiver_id=trainer_id, message=message_txt)
    db.session.add(msg)
    db.session.commit()

    return redirect(url_for("trainers.trainers_page") + f"?trainer_id={trainer_id}")


@trainers.route("/trainers/cancel/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    b = SessionBooking.query.filter_by(
        booking_id=booking_id, client_id=user.user_id
    ).first()

    if b:
        trainer_id = b.trainer_id
        b.status = "cancelled"
        db.session.commit()
        flash("Booking cancelled.", "success")
        return redirect(url_for("trainers.trainers_page") + f"?trainer_id={trainer_id}")

    flash("Booking not found.", "error")
    return redirect(url_for("trainers.trainers_page"))


@trainers.route("/pt-clients")
def pt_clients():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    if user.role != "pt":
        flash("Access denied. Personal trainer privileges required.", "error")
        return redirect(url_for("home.index"))

    clients = (
        User.query.join(SessionBooking, SessionBooking.client_id == User.user_id)
        .filter(
            SessionBooking.trainer_id == user.user_id,
            SessionBooking.status == "confirmed",
        )
        .distinct()
        .all()
    )

    return render_template("pt_clients.html", clients=clients)


@trainers.route("/trainer-dashboard")
def trainer_dashboard():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    if user.role != "pt":
        flash("Access denied. Trainer account required.", "error")
        return redirect(url_for("home.index"))

    bookings = (
        SessionBooking.query.filter_by(trainer_id=user.user_id)
        .filter(SessionBooking.status != "cancelled")
        .order_by(SessionBooking.date.desc())
        .all()
    )

    messages = (
        TrainerMessage.query.filter_by(receiver_id=user.user_id)
        .order_by(TrainerMessage.sent_at.desc())
        .all()
    )

    client_ids = {b.client_id for b in bookings}

    clients = (
        User.query.filter(User.user_id.in_(client_ids)).all() if client_ids else []
    )

    client_names = {
        c.user_id: f"{c.first_name} {c.last_name}".strip() or c.username
        for c in clients
    }

    return render_template(
        "trainer_dashboard.html",
        bookings=bookings,
        messages=messages,
        client_names=client_names,
    )


@trainers.route("/trainers/booking/confirm/<int:booking_id>", methods=["POST"])
def confirm_booking(booking_id):
    user = get_logged_in_user()
    if not user or user.role != "pt":
        return redirect(url_for("auth.login"))

    b = SessionBooking.query.filter_by(
        booking_id=booking_id, trainer_id=user.user_id
    ).first()

    if b:
        b.status = "confirmed"

        existing_client = TrainingClient.query.filter_by(
            trainer_id=user.user_id, client_id=b.client_id
        ).first()

        if existing_client:
            existing_client.active = True
        else:
            new_client = TrainingClient(
                trainer_id=user.user_id, client_id=b.client_id, active=True
            )
            db.session.add(new_client)

        db.session.commit()
        flash("Booking confirmed and client added!", "success")

    return redirect(url_for("trainers.trainer_dashboard"))


@trainers.route("/trainers/booking/decline/<int:booking_id>", methods=["POST"])
def decline_booking(booking_id):
    user = get_logged_in_user()
    if not user or user.role != "pt":
        return redirect(url_for("auth.login"))

    b = SessionBooking.query.filter_by(
        booking_id=booking_id, trainer_id=user.user_id
    ).first()

    if b:
        b.status = "cancelled"
        db.session.commit()
        flash("Booking declined.", "success")

    return redirect(url_for("trainers.trainer_dashboard"))


@trainers.route("/trainer-profile/edit", methods=["GET", "POST"])
def edit_trainer_profile():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    if user.role != "pt":
        flash("Access denied. Trainer account required.", "error")
        return redirect(url_for("home.index"))

    profile = ensure_trainer_profile(user)

    if request.method == "POST":
        profile.specialty = request.form.get("specialty", "").strip()

        bio_text = request.form.get("bio", "").strip()
        features = request.form.get("features", "").strip()

        if features:
            profile.bio = bio_text + "|||" + features.replace("\n", "|||")
        else:
            profile.bio = bio_text

        db.session.commit()
        flash("Trainer profile updated!", "success")
        return redirect(url_for("trainers.trainer_dashboard"))

    parts = (profile.bio or "").split("|||")
    bio_text = parts[0] if parts else ""
    features_text = "\n".join(parts[1:]) if len(parts) > 1 else ""

    return render_template(
        "edit_trainer_profile.html",
        profile=profile,
        bio_text=bio_text,
        features_text=features_text,
    )


@trainers.route("/trainer/assign-exercise", methods=["GET", "POST"])
def assign_exercise():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for("auth.login"))

    if user.role != "pt":
        flash("Access denied. Trainer account required.", "error")
        return redirect(url_for("home.index"))

    clients = (
        User.query.join(TrainingClient, TrainingClient.client_id == User.user_id)
        .filter(
            TrainingClient.trainer_id == user.user_id, TrainingClient.active)
        .all()
    )

    exercises = GymExercise.query.order_by(GymExercise.name.asc()).all()

    if request.method == "POST":
        client_id = request.form.get("client_id", type=int)
        exercise_id = request.form.get("exercise_id", type=int)
        sets = request.form.get("sets", type=int)
        reps = request.form.get("reps", type=int)
        weight_kg = request.form.get("weight_kg", type=float)
        notes = request.form.get("notes", "").strip()

        if not client_id or not exercise_id:
            flash("Please choose a client and an exercise.", "error")
            return redirect(url_for("trainers.assign_exercise"))

        assignment = GymAssignment(
            trainer_id=user.user_id,
            client_id=client_id,
            gym_exercise_id=exercise_id,
            sets=sets or 0,
            reps=reps or 0,
            weight_kg=weight_kg or 0,
            notes=notes,
        )

        db.session.add(assignment)
        db.session.commit()

        flash("Exercise assigned to client!", "success")
        return redirect(url_for("trainers.assign_exercise"))

    return render_template("assign_exercise.html", clients=clients, exercises=exercises)
