"""
Admin dashboard routes for the FitTrack application.
Handles user management (search, delete), personal trainer
approval/rejection, and platform statistics display.
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from fitness_app.extentions import db
from fitness_app.models import User

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
def admin_dashboard():
    """Admin dashboard — manage users, approve trainers, view platform statistics."""
    search_query = request.args.get('q', '')

    # Get admin user
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
    admin_user = User.query.filter_by(username=username).first()
    if not admin_user or admin_user.role != 'administrator':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('home.index'))

    # Get active (non-admin) users, with optional search
    users_query = User.query.filter(User.role != 'administrator')
    if search_query:
        users_query = users_query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%'))
        )
    active_users = users_query.all()

    # Pending PT users (role='pt' and not yet approved)
    pending_pts = User.query.filter_by(role='pt', approved=False).all()

    # Approved PT users
    approved_pts = User.query.filter_by(role='pt', approved=True).all()

    # Platform statistics
    total_users = User.query.count()
    total_customers = User.query.filter_by(role='customer').count()
    total_pts = User.query.filter_by(role='pt').count()
    total_admins = User.query.filter_by(role='administrator').count()

    return render_template('admin.html',
                           admin_user=admin_user,
                           active_users=active_users,
                           pending_pts=pending_pts,
                           approved_pts=approved_pts,
                           search_query=search_query,
                           total_users=total_users,
                           total_customers=total_customers,
                           total_pts=total_pts,
                           total_admins=total_admins)


@admin_bp.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user from the platform."""
    user = User.query.get_or_404(user_id)

    # Don't allow deleting admin users
    if user.role == 'administrator':
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} has been deleted.', 'success')

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/approve-pt/<int:user_id>', methods=['POST'])
def approve_pt(user_id):
    """Approve a personal trainer application."""
    user = User.query.get_or_404(user_id)

    if user.role == 'pt':
        user.approved = True
        db.session.commit()
        flash(f'Personal Trainer {user.first_name} has been approved.', 'success')

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/reject-pt/<int:user_id>', methods=['POST'])
def reject_pt(user_id):
    """Reject a personal trainer application (removes the user)."""
    user = User.query.get_or_404(user_id)

    if user.role == 'pt' and not user.approved:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'PT application for {username} has been rejected.', 'info')

    return redirect(url_for('admin.admin_dashboard'))

