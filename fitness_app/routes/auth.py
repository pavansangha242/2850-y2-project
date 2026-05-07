"""Auth Blueprint.

This blueprint handles all user-related functionality for the application.
It is responsible for authentication (login, register, logout), account
management (settings, updating stats, deleting accounts), privacy settings,
and user-specific data such as health surveys.

It also supports role-based access:
- Customers can complete health surveys and manage their data.
- Personal Trainers (PTs) can view client lists and access shared survey data.

Additionally, it ensures user session handling and makes the current user's
role available globally for template rendering.
"""

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from fitness_app.extensions import db
from fitness_app.models import (
    HealthSurvey,
    PrivacySettings,
    StravaActivity,
    TrainingClient,
    User,
    UserGoal,
)

auth = Blueprint("auth", __name__)


@auth.route("/")
def root():
    """Redirect to the login page."""
    return redirect(url_for("auth.login"))


# make the user's role available in every template without passing it manually each time
@auth.before_app_request
def load_nav_user():
    """Make the current user's role available in all templates as g.nav_role."""
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        g.nav_role = user.role if user else None
    else:
        g.nav_role = None


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login and session creation."""
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        if user and user.role == "administrator":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("home.index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["username"] = username
            if user.role == "administrator":
                return redirect(url_for("admin.admin_dashboard"))
            return redirect(url_for("auth.user_settings"))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for("auth.login")
            )

    return render_template("login.html", show_nav=False)


@auth.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account with validation and role handling."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        email = request.form["email"]
        phone_number = request.form["phone"]
        role = request.form.get("role")

        # Security: Prevent anyone from registering as an administrator publicly
        if role == "administrator":
            # allow first admin, block any others
            existing_admin = User.query.filter_by(role="administrator").first()
            if existing_admin:
                return render_template(
                    "register.html",
                    error="An administrator account already exists. Administrator registration is disabled.",
                    show_nav=False,
                )

        bio = None
        # Bio is mandatory for PTs
        if role == "pt":
            bio = request.form.get("bio", "").strip()

            if not bio:
                return render_template(
                    "register.html", error="Please enter your bio.", show_nav=False
                )
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        # To ensure user enters first and last name, empty string not allowed
        if not first_name or not last_name:
            return render_template(
                "register.html",
                error="Please enter your first and last name.",
                show_nav=False,
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords don't match, please re-enter",
                show_nav=False,
            )

        if User.query.filter_by(username=username).first():
            return render_template(
                "register.html",
                error="Username is taken, please choose another one",
                show_nav=False,
            )

        if User.query.filter_by(email=email).first():
            return render_template(
                "register.html", error="Email is already registered", show_nav=False
            )

        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            role=role,
            approved=(
                False if role == "pt" else True
            ),  # pt accounts need manual approval, everyone else is good to go immediately
            bio=bio,
        )
        new_user.set_password(password)

        # Backend validation for health fields (customers only)
        if role == "customer":
            required_fields = [
                "step_target",
                "weekly_hours",
                "workouts_per_week",
                "age",
                "weight",
                "height",
                "sex",
            ]

            for field in required_fields:
                if not request.form.get(field):
                    return render_template(
                        "register.html",
                        error="Please fill in all health goal fields.",
                        show_nav=False,
                    )

            # goals only apply to customers, pts just have a bio
            new_goals = UserGoal(
                user=new_user,
                step_target=int(request.form.get("step_target")),
                weekly_exercise_hours=float(request.form.get("weekly_hours")),
                workouts_per_week=int(request.form.get("workouts_per_week")),
                age=int(request.form.get("age")),
                weight_kg=float(request.form.get("weight")),
                height_cm=float(request.form.get("height")),
                sex=request.form.get("sex"),
            )

            new_privacy = PrivacySettings(
                user=new_user,
                share_with_pt=True if request.form.get("share_with_pt") else False,
                allow_meetings=True if request.form.get("allow_meetings") else False,
            )

            db.session.add(new_goals)
            db.session.add(new_privacy)

        db.session.add(new_user)
        db.session.commit()

        session["username"] = new_user.username
        return redirect(url_for("auth.user_settings"))

    return render_template("register.html", show_nav=False)


@auth.route("/settings")
def user_settings():
    """Display the current user's account settings page."""
    if "username" not in session:
        return redirect(url_for("auth.login"))
    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.pop("username", None)
        return redirect(url_for("auth.login"))
    return render_template("user_settings.html", user=user)


@auth.route("/update_privacy", methods=["POST"])
def update_privacy():
    """Update the user's privacy preferences."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()
    user.privacy.share_with_pt = True if request.form.get("share_with_pt") else False
    user.privacy.allow_meetings = True if request.form.get("allow_meetings") else False

    db.session.commit()
    return redirect(url_for("auth.user_settings"))


@auth.route("/logout")
def logout():
    """Log the user out and clear the session."""
    session.pop("username", None)
    return redirect(url_for("auth.login"))


@auth.route("/delete_account", methods=["POST"])
def delete_account():
    """Delete the user's account and all related data."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    if not user:
        return redirect(url_for("auth.login"))

    # Delete child tables before deleting user, otherwise db error occurs
    StravaActivity.query.filter_by(user_id=user.user_id).delete()
    UserGoal.query.filter_by(user_id=user.user_id).delete()
    PrivacySettings.query.filter_by(user_id=user.user_id).delete()
    HealthSurvey.query.filter_by(user_id=user.user_id).delete()

    # Flush so child deletes are written before removing user
    db.session.flush()

    # Delete User
    db.session.delete(user)
    db.session.commit()

    session.pop("username", None)

    return redirect(url_for("auth.register"))


@auth.route("/update_stats", methods=["POST"])
def update_stats():
    """Update the user's personal statistics."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.pop("username", None)
        return redirect(url_for("auth.login"))

    user.goals.age = request.form.get("age")
    user.goals.weight_kg = request.form.get("weight")
    user.goals.height_cm = request.form.get("height")
    user.goals.sex = request.form.get("sex")

    db.session.commit()
    return redirect(url_for("auth.user_settings"))


@auth.route("/survey", methods=["GET", "POST"])
def survey():
    """Create or update a user's health survey."""
    # Only customers can fill in the survey
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role != "customer":
        return redirect(url_for("auth.user_settings"))

    existing_survey = user.survey  # None if not filled in yet

    if request.method == "POST":
        if existing_survey:
            # Update existing survey
            s = existing_survey
        else:
            # Create a new one
            s = HealthSurvey(user=user)
            db.session.add(s)

        s.workout_hours_per_day = request.form.get("workout_hours_per_day", type=float)
        s.workout_days_per_week = request.form.get("workout_days_per_week", type=int)
        s.preferred_workout_type = request.form.get("preferred_workout_type")
        s.fitness_level = request.form.get("fitness_level")
        s.sleep_hours = request.form.get("sleep_hours", type=float)
        s.water_litres = request.form.get("water_litres", type=float)
        s.smokes = request.form.get("smokes") == "true"
        s.alcohol_frequency = request.form.get("alcohol_frequency")
        s.diet_type = request.form.get("diet_type")
        s.meals_per_day = request.form.get("meals_per_day", type=int)
        s.has_injuries = request.form.get("has_injuries") == "true"
        s.injury_details = request.form.get("injury_details")
        s.medical_conditions = request.form.get("medical_conditions")
        s.fitness_goal = request.form.get("fitness_goal")
        s.motivation_level = request.form.get("motivation_level", type=int)
        s.additional_notes = request.form.get("additional_notes")

        from datetime import datetime

        s.last_updated = datetime.utcnow()

        db.session.commit()
        return render_template("survey.html", survey=s, success=True)

    return render_template("survey.html", survey=existing_survey)


@auth.route("/clients")
def pt_clients():
    """Display a list of clients assigned to the personal trainer."""
    # Only PTs can see the client list
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role != "pt":
        return redirect(url_for("auth.user_settings"))

    # Show all customers who have share_with_pt enabled, and are matched with that PT
    clients = (
        User.query.join(TrainingClient, TrainingClient.client_id == User.user_id)
        .join(PrivacySettings, PrivacySettings.user_id == User.user_id)
        .filter(
            TrainingClient.trainer_id == user.user_id,  # must be matched to this PT
            TrainingClient.active,  # only active relationships
            User.role == "customer",
            PrivacySettings.share_with_pt,  # must have sharing on
        )
        .all()
    )

    return render_template("pt_clients.html", clients=clients)


@auth.route("/clients/<int:customer_id>/survey")
def pt_view_survey(customer_id):
    """Allow a PT to view a customer's shared survey."""
    # Only PTs can view a customer's survey
    if "username" not in session:
        return redirect(url_for("auth.login"))

    pt = User.query.filter_by(username=session["username"]).first()
    if not pt or pt.role != "pt":
        return redirect(url_for("auth.user_settings"))

    customer = User.query.get_or_404(customer_id)

    # Make sure the customer has sharing enabled
    if not customer.privacy or not customer.privacy.share_with_pt:
        return redirect(url_for("auth.pt_clients"))

    return render_template(
        "pt_view_survey.html", customer=customer, survey=customer.survey
    )
