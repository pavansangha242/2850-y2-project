import time
import requests
from flask import Blueprint, redirect, request, session, url_for, jsonify
from extensions import db
from models import User
import os

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