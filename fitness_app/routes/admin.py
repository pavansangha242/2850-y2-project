"""
Admin dashboard routes for the FitTrack application.
Handles user management (search, delete), personal trainer
approval/rejection, and platform statistics display.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from fitness_app.extensions import db
from fitness_app.models import (
    User,
    TrainerProfile,
    Competition,
    CompetitionResult,
    ChatMessage,
    TrainerReview,
    SessionBooking,
    TrainerMessage,
)
from datetime import datetime

admin_bp = Blueprint("admin", __name__)


def get_admin_user():
    """Return the logged-in admin user, or None if the user is not an admin."""
    username = session.get("username")
    if not username:
        return None

    user = User.query.filter_by(username=username).first()
    if user and user.role == "administrator":
        return user

    return None


@admin_bp.route("/admin")
def admin_dashboard():
    """Admin dashboard — manage users, approve trainers, view platform statistics."""
    search_query = request.args.get("q", "")

    # Check if logged in and is admin
    if not session.get("username"):
        return redirect(url_for("auth.login"))

    admin_user = get_admin_user()
    if not admin_user:
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    # Get active users, with optional search
    users_query = User.query
    if search_query:
        users_query = users_query.filter(
            (User.username.ilike(f"%{search_query}%"))
            | (User.email.ilike(f"%{search_query}%"))
            | (User.first_name.ilike(f"%{search_query}%"))
            | (User.last_name.ilike(f"%{search_query}%"))
        )
    active_users = users_query.all()

    # Pending PT users (role='pt' and not yet approved)
    pending_pts = User.query.filter_by(role="pt", approved=False).all()

    # Approved PT users
    approved_pts = User.query.filter_by(role="pt", approved=True).all()

    # Platform statistics
    total_users = User.query.count()
    total_customers = User.query.filter_by(role="customer").count()
    total_pts = User.query.filter_by(role="pt").count()
    total_admins = User.query.filter_by(role="administrator").count()

    # Competition / Event management
    competitions = Competition.query.order_by(Competition.date.asc()).all()

    return render_template(
        "admin.html",
        admin_user=admin_user,
        active_users=active_users,
        pending_pts=pending_pts,
        approved_pts=approved_pts,
        competitions=competitions,
        search_query=search_query,
        total_users=total_users,
        total_customers=total_customers,
        total_pts=total_pts,
        total_admins=total_admins,
    )


@admin_bp.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    """Delete a user from the platform."""
    if not get_admin_user():
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    user = User.query.get_or_404(user_id)

    # Don't allow deleting admin users
    if user.role == "administrator":
        return redirect(url_for("admin.admin_dashboard"))

    CompetitionResult.query.filter_by(user_id=user.user_id).delete()
    ChatMessage.query.filter_by(user_id=user.user_id).delete()
    TrainerReview.query.filter(
        (TrainerReview.trainer_id == user.user_id)
        | (TrainerReview.client_id == user.user_id)
    ).delete(synchronize_session=False)
    SessionBooking.query.filter(
        (SessionBooking.trainer_id == user.user_id)
        | (SessionBooking.client_id == user.user_id)
    ).delete(synchronize_session=False)
    TrainerMessage.query.filter(
        (TrainerMessage.sender_id == user.user_id)
        | (TrainerMessage.receiver_id == user.user_id)
    ).delete(synchronize_session=False)

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} has been deleted.", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/approve-pt/<int:user_id>", methods=["POST"])
def approve_pt(user_id):
    """Approve a personal trainer application."""
    if not get_admin_user():
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    user = User.query.get_or_404(user_id)

    if user.role == "pt":
        user.approved = True

        profile = TrainerProfile.query.filter_by(user_id=user.user_id).first()

        if not profile:
            profile = TrainerProfile(
                user_id=user.user_id,
                specialty="Personal Trainer",
                bio="Certified personal trainer.|||Gym training|||Fitness coaching|||Workout plans",
                average_rating=0,
                total_reviews=0,
            )
            db.session.add(profile)
        db.session.commit()

        flash(f"Personal Trainer {user.first_name} has been approved.", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/reject-pt/<int:user_id>", methods=["POST"])
def reject_pt(user_id):
    """Reject a personal trainer application (removes the user)."""
    if not get_admin_user():
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    user = User.query.get_or_404(user_id)

    if user.role == "pt" and not user.approved:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f"PT application for {username} has been rejected.", "info")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/add-event", methods=["POST"])
def add_event():
    """Add a new competition/event."""
    if not get_admin_user():
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    date_str = request.form.get("date", "").strip()
    distance_str = request.form.get("distance", "").strip()

    if name and date_str:
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            distance = float(distance_str) if distance_str else 0.0
            new_event = Competition(
                name=name, location=location, date=event_date, distance=distance
            )
            db.session.add(new_event)
            db.session.commit()
            flash(f'Event "{name}" has been created.', "success")
        except ValueError:
            flash("Please enter a valid date and distance.", "danger")
    else:
        flash("Please enter an event name and date.", "danger")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/delete-event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    """Delete a competition/event."""
    if not get_admin_user():
        flash("Access denied. Administrator privileges required.", "danger")
        return redirect(url_for("home.index"))

    event = Competition.query.get_or_404(event_id)
    CompetitionResult.query.filter_by(competition_id=event.competition_id).delete()
    ChatMessage.query.filter_by(competition_id=event.competition_id).delete()
    db.session.delete(event)
    db.session.commit()
    flash(f'Event "{event.name}" has been deleted.', "success")

    return redirect(url_for("admin.admin_dashboard"))
