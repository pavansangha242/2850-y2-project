"""Strava Blueprint.

This blueprint handles integration with the Strava API.

It allows users to:
- Connect and disconnect their Strava account via OAuth
- Automatically refresh expired access tokens
- Fetch and synchronise activity data from Strava
- Store activities in the local database
- View activity history, statistics, and detailed activity data

The blueprint also includes:
- Rate limiting protection to avoid excessive API calls
- Incremental syncing to only fetch new activities
- Basic calorie estimation when Strava data is unavailable

All routes ensure that only authenticated users can access their own data.
"""

import os
import time
from datetime import datetime, timedelta

import requests
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from fitness_app.extensions import db
from fitness_app.models import StravaActivity, User

CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

strava_bp = Blueprint("strava", __name__)


# Strava app credentials
# Get a valid access token for the current user
# Key function, it automatically refreshes if expired
def get_valid_token(user):
    """Return a valid Strava access token, refreshing it if expired."""
    now = int(time.time())  # current time as Unix timestamp

    # Check if token is expired (or will expire in next 60 seconds) - if so then treat it as though it has already expired
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
        },
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
    """Redirect the user to Strava OAuth for account connection."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    #  the callback URL has to exactly match what's registered on the Strava app dashboard, must be specific to codespace name or local server if running off vs code app
    callback_url = url_for("strava.strava_callback", _external=True)

    strava_auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={callback_url}"
        f"&response_type=code"
        f"&scope=activity:read_all"  # asking for all the data
    )
    return redirect(strava_auth_url)


# Strava redirects back here with a code
@strava_bp.route("/strava-callback")
def strava_callback():
    """Handle Strava OAuth callback and store user tokens."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    # If user clicked "Cancel" on Strava's page, then redireect to activities page
    error = request.args.get("error")
    if error:
        return redirect(url_for("strava.activities"))

    # Exchange the temporary code for real tokens
    code = request.args.get("code")
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )

    if response.status_code != 200:
        return redirect(url_for("auth.user_settings"))

    tokens = response.json()

    # Save everything to the user in DB
    user = User.query.filter_by(username=session["username"]).first()
    user.strava_access_token = tokens["access_token"]
    user.strava_refresh_token = tokens["refresh_token"]
    user.strava_token_expires_at = tokens["expires_at"]
    user.strava_athlete_id = tokens["athlete"]["id"]
    db.session.commit()

    return redirect(url_for("auth.user_settings"))


# Disconnect Strava
@strava_bp.route("/disconnect-strava", methods=["POST"])
def disconnect_strava():
    """Disconnect the user's Strava account and clear tokens."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_token_expires_at = None
    user.strava_athlete_id = None
    db.session.commit()

    return redirect(url_for("auth.user_settings"))


# For Asma to get activities for her pages
@strava_bp.route("/strava-activities")
def get_activities():
    """Fetch recent activities from Strava API for the logged-in user."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    if not user.strava_access_token:
        return jsonify({"error": "Strava not connected"}), 401

    token = get_valid_token(user)
    if not token:
        return jsonify({"error": "Could not refresh Strava token"}), 401

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 30},  # last 30 activities
    )

    return jsonify(response.json())


@strava_bp.route("/sync-strava")
def sync_strava():
    """Synchronise user activities from Strava into the local database."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    if not user.strava_access_token:
        return jsonify({"error": "Strava not connected"}), 401

    # Rate limit protection
    # If they synced less than 15 minutes ago, don't sync as Strava API has limit to amount of requests
    now = datetime.utcnow()
    if getattr(user, "last_strava_sync", None):
        if now - user.last_strava_sync < timedelta(minutes=15):
            return redirect(url_for("strava.activities"))

    token = get_valid_token(user)
    if not token:
        return jsonify({"error": "Could not refresh token"}), 401

    # Incremental sync, only fetch new activities

    params = {"per_page": 30}

    # Only fetch activities newer than the last sync as we already have that information
    if getattr(user, "last_strava_activity_time", None):
        params["after"] = int(user.last_strava_activity_time.timestamp())

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )

    activities = response.json()

    # Strava sometimes returns error dict instead of a list if something went wrong
    if not isinstance(activities, list):
        return (
            jsonify({"error": "Failed to fetch activities", "details": activities}),
            400,
        )

    newest_activity_time = None

    for a in activities:

        # Checking for no duplicates, skip if it's already been saved
        existing = StravaActivity.query.filter_by(strava_id=a["id"]).first()

        if existing:
            activity = existing
        else:
            activity = StravaActivity(strava_id=a["id"], user_id=user.user_id)
            db.session.add(activity)

        # Calories without hitting API limits
        activity_type = a.get("type")
        is_manual = a.get("manual", False)

        activity.is_manual = is_manual

        weight = getattr(user.goals, "weight_kg", 70) or 70

        distance_km = (a.get("distance") or 0) / 1000
        time_hr = (a.get("moving_time") or 0) / 3600

        # 1. Use Strava calories if they exist
        if a.get("calories") is not None:
            calories = a["calories"]

        # 2. Better fallback for manual or missing data instead of 0 returned by Strava
        # rough MET-based estimates when Strava doesn't give us calories
        else:
            if activity_type == "Run":
                calories = round(1.036 * distance_km * weight)

            elif activity_type == "Ride":
                calories = round(0.35 * distance_km * weight)

            else:
                calories = round(300 * time_hr)

        # Assign fields
        activity.name = a.get("name")
        activity.activity_type = a.get("type")

        if a.get("start_date"):
            activity.start_date = datetime.strptime(
                a["start_date"], "%Y-%m-%dT%H:%M:%SZ"
            )

            # track newest activity for incremental sync
            dt = activity.start_date
            if not newest_activity_time or dt > newest_activity_time:
                newest_activity_time = dt

        activity.distance_m = a.get("distance")
        activity.moving_time_s = a.get("moving_time")
        activity.calories = calories
        activity.avg_heart_rate = a.get("average_heartrate")
        activity.max_heart_rate = a.get("max_heartrate")
        activity.elevation_gain = a.get("total_elevation_gain")
        activity.avg_speed = a.get("average_speed")
        activity.polyline = a.get("map", {}).get("summary_polyline")

    # Record when it was last synced for the rate limit check
    user.last_strava_sync = now

    # Keeps a track of the newest activity so incremental sync knows where to start next time
    if newest_activity_time:
        if not user.last_strava_activity_time:
            user.last_strava_activity_time = newest_activity_time
        else:
            user.last_strava_activity_time = max(
                user.last_strava_activity_time, newest_activity_time
            )

    db.session.commit()

    return redirect(url_for("strava.activities"))


# Dashboard to check visualisation
@strava_bp.route("/activity/<int:activity_id>")
def activity_map(activity_id):
    """Display a map view of a specific activity."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    activity = StravaActivity.query.filter_by(
        id=activity_id, user_id=user.user_id
    ).first()

    if not activity:
        return "Activity not found", 404

    return render_template("activity_detail.html", activity=activity)


@strava_bp.route("/activities")
def activities():
    """Display filtered activity history and summary statistics."""
    # Need to use username from user that is logged in to connect to strava
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    # Get filter from query string, default to 'week'
    period = request.args.get("period", "week")
    activity_type = request.args.get("type", "all")

    query = StravaActivity.query.filter_by(user_id=user.user_id)

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
        "total_time_mins": sum(a.moving_time_s or 0 for a in activities) // 60,
    }

    return render_template(
        "activities.html",
        activities=activities,
        stats=stats,
        period=period,
        activity_type=activity_type,
    )


@strava_bp.route("/activities/<int:strava_id>")
def activity_detail(strava_id):
    """Display detailed information for a specific activity."""
    if "username" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(username=session["username"]).first()

    # Make sure this activity belongs to the logged-in user
    activity = StravaActivity.query.filter_by(
        strava_id=strava_id, user_id=user.user_id
    ).first_or_404()

    return render_template("activity_detail.html", activity=activity)
