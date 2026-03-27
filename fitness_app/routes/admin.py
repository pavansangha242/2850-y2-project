from flask import Blueprint, render_template, redirect, url_for, request
from fitness_app.extentions import db
from fitness_app.models import User

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
def admin_dashboard():
    """Admin dashboard — manage users."""
    search_query = request.args.get('q', '')

    # Get admin user
    admin_user = User.query.filter_by(role='administrator').first()

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

    # Pending PT users (role='pt' who could be awaiting approval — for now just list PTs)
    pending_pts = User.query.filter_by(role='pt').all()

    return render_template('admin.html',
                           admin_user=admin_user,
                           active_users=active_users,
                           pending_pts=pending_pts,
                           search_query=search_query)


@admin_bp.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user from the platform."""
    user = User.query.get_or_404(user_id)

    # Don't allow deleting admin users
    if user.role == 'administrator':
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('admin.admin_dashboard'))
