import time
import requests
from flask import Blueprint, redirect, request, session, url_for, jsonify, render_template
from extensions import db
from models import User
import os
# For Strava activities being added
from models import User, StravaActivity
from datetime import datetime, timedelta

CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

strava_bp = Blueprint('strava', __name__)

# Strava app credentials
# Move to environment variables once implemented - can't store on github for security


# Get a valid access token for the current user
# Key function, it automatically refreshes if expired
def get_valid_token(user):
    now = int(time.time())  # current time as Unix timestamp

    # Check if token is expired (or will expire in next 60 seconds)
    if user.strava_token_expires_at and user.strava_token_expires_at > now + 60:
        # Token is still valid, just return it
        return user.strava_access_token

    # Token is expired, use refresh token to get a new one
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": user.strava_refresh_token,
        }
    )

    if response.status_code != 200:
        return None  # refresh failed 

    tokens = response.json()

    # Save the new tokens back to the DB
    user.strava_access_token = tokens["access_token"]
    user.strava_refresh_token = tokens["refresh_token"]
    user.strava_token_expires_at = tokens["expires_at"]
    db.session.commit()

    return user.strava_access_token


# Send user to Strava to log in 
@strava_bp.route("/connect-strava")
def connect_strava():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    # Strava redirects back to /strava-callback after the user approves
    callback_url = url_for('strava.strava_callback', _external=True)

    strava_auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&response_type=code"
        f"&scope=activity:read_all"  # data asking for
    )
    return redirect(strava_auth_url)


# Strava redirects back here with a code 
@strava_bp.route("/strava-callback")
def strava_callback():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    # If user clicked "Cancel" on Strava's page
    error = request.args.get("error")
    if error:
        return redirect(url_for('auth.user_settings'))

    # Exchange the temporary code for real tokens
    code = request.args.get("code")
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        }
    )

    if response.status_code != 200:
        return redirect(url_for('auth.user_settings'))

    tokens = response.json()

    # Save everything to the user in DB
    user = User.query.filter_by(username=session["username"]).first()
    user.strava_access_token = tokens["access_token"]
    user.strava_refresh_token = tokens["refresh_token"]
    user.strava_token_expires_at = tokens["expires_at"]
    user.strava_athlete_id = tokens["athlete"]["id"]
    db.session.commit()

    return redirect(url_for('auth.user_settings'))


# Disconnect Strava 
@strava_bp.route("/disconnect-strava", methods=["POST"])
def disconnect_strava():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_token_expires_at = None
    user.strava_athlete_id = None
    db.session.commit()

    return redirect(url_for('auth.user_settings'))


# For Asma to get activities for her pages
@strava_bp.route("/strava-activities")
def get_activities():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()

    if not user.strava_access_token:
        return jsonify({"error": "Strava not connected"}), 401

    token = get_valid_token(user)
    if not token:
        return jsonify({"error": "Could not refresh Strava token"}), 401

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 30}  # last 30 activities
    )

    return jsonify(response.json())

@strava_bp.route("/sync-strava")
def sync_strava():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()

    if not user.strava_access_token:
        return jsonify({"error": "Strava not connected"}), 401

    token = get_valid_token(user)
    if not token:
        return jsonify({"error": "Could not refresh token"}), 401

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 50}  # last 50 activities
    )

    activities = response.json()
    new_count = 0

    for a in activities:
        # To fix error of db getting locked
        existing = StravaActivity.query.filter_by(strava_id=a["id"]).first()

        if existing:
            activity = existing
        else:
            activity = StravaActivity(
                strava_id=a["id"],
                user_id=user.id
            )
            db.session.add(activity)

        # Get detailed activity
        detail_res = requests.get(
            f"https://www.strava.com/api/v3/activities/{a['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )

        calories = None

        if detail_res.status_code == 200:
            detail = detail_res.json()
            calories = detail.get("calories")

        if not calories:
            calories = a.get("calories")

        # 🔥 ALWAYS ensure calories exist
        if not calories:
            distance_km = (a.get("distance") or 0) / 1000
            weight = getattr(user, "weight_kg", 70)
            calories = round(1.036 * distance_km * weight)

        #print("Saving:", a["id"], calories)

        # Assign all fields
        activity.name = a.get("name")
        activity.activity_type = a.get("type")
        activity.start_date = datetime.strptime(a["start_date"], "%Y-%m-%dT%H:%M:%SZ")
        activity.distance_m = a.get("distance")
        activity.moving_time_s = a.get("moving_time")
        activity.calories = calories
        activity.avg_heart_rate = a.get("average_heartrate")
        activity.max_heart_rate = a.get("max_heartrate")
        activity.elevation_gain = a.get("total_elevation_gain")
        activity.avg_speed = a.get("average_speed")
        activity.polyline = a.get("map", {}).get("summary_polyline")

        new_count += 1

        #print("Activity:", a["id"], "Calories:", calories)
    

    db.session.commit()
    return redirect(url_for('strava.activities')) ##

# Dashboard to check visualisation 
@strava_bp.route("/activity/<int:activity_id>")
def activity_map(activity_id):
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()

    activity = StravaActivity.query.filter_by(
        id=activity_id,
        user_id=user.id
    ).first()

    if not activity:
        return "Activity not found", 404

    return render_template("activity_detail.html", activity=activity)

@strava_bp.route("/activities")
def activities():
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()
    
    # Get filter from query string, default to 'week'
    period = request.args.get("period", "week")
    activity_type = request.args.get("type", "all")

    query = StravaActivity.query.filter_by(user_id=user.id)

    # Date filter
    if period == "week":
        query = query.filter(
            StravaActivity.start_date >= datetime.utcnow() - timedelta(days=7)
        )
    elif period == "month":
        query = query.filter(
            StravaActivity.start_date >= datetime.utcnow() - timedelta(days=30)
        )
    # all needs no date filter

    # Type filter
    if activity_type != "all":
        query = query.filter_by(activity_type=activity_type)

    activities = query.order_by(StravaActivity.start_date.desc()).all()

    # Summary stats for whatever is currently filtered
    stats = {
        "total_km": round(sum(a.distance_m or 0 for a in activities) / 1000, 1),
        "total_calories": round(sum(a.calories or 0 for a in activities)),
        "total_activities": len(activities),
        "total_time_mins": sum(a.moving_time_s or 0 for a in activities) // 60
    }

    return render_template(
        "activities.html",
        activities=activities,
        stats=stats,
        period=period,
        activity_type=activity_type
    )


@strava_bp.route("/activities/<int:strava_id>")
def activity_detail(strava_id):
    if "username" not in session:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session["username"]).first()
    
    # Make sure this activity belongs to the logged-in user
    activity = StravaActivity.query.filter_by(
        strava_id=strava_id,
        user_id=user.id
    ).first_or_404()

    return render_template("activity_detail.html", activity=activity)