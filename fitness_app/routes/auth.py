from flask import Blueprint, render_template, request, redirect, session, url_for
from extensions import db
from models import User, UserGoal, PrivacySettings

auth = Blueprint('auth', __name__)
# Blueprint name is 'auth'  so url_for('auth.login'), url_for('auth.register') etc.



@auth.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for('auth.user_settings'))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['username'] = username
            return redirect(url_for('auth.user_settings'))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        email = request.form["email"]
        phone_number = request.form["phone"]
        role = request.form.get("role")
        bio = request.form.get("bio") if role == "pt" else None

        if password != confirm_password:
            return render_template("register.html", error="Passwords don't match, please re-enter")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username is taken, please choose another one")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email is already registered")

        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            role=role,
            approved=(False if role == "pt" else True),
            bio=bio
        )
        new_user.set_password(password)

        new_goals = UserGoal(
            user=new_user,
            step_target=request.form.get("step_target", 10000) or 10000,
            weekly_exercise_hours=request.form.get("weekly_hours", 0) or 0,
            workouts_per_week=request.form.get("workouts_per_week", 0) or 0,
        )

        new_privacy = PrivacySettings(
            user=new_user,
            share_with_pt=True if request.form.get("share_with_pt") else False,
            allow_meetings=True if request.form.get("allow_meetings") else False
        )

        db.session.add(new_user)
        db.session.add(new_goals)
        db.session.add(new_privacy)
        db.session.commit()

        session['username'] = new_user.username
        return redirect(url_for('auth.user_settings'))

    return render_template("register.html")


@auth.route("/settings")
def user_settings():
    if "username" not in session:
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(username=session["username"]).first()
    return render_template("user_settings.html", user=user)


@auth.route("/update_privacy", methods=["POST"])
def update_privacy():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()
    user.privacy.share_with_pt = True if request.form.get("share_with_pt") else False
    user.privacy.allow_meetings = True if request.form.get("allow_meetings") else False

    db.session.commit()
    return redirect(url_for('auth.user_settings'))


@auth.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for('auth.login'))


@auth.route("/delete_account", methods=["POST"])
def delete_account():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()

    if user:
        db.session.delete(user)
        db.session.commit()
        session.pop("username", None)

    return redirect(url_for('auth.register'))