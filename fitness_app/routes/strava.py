import requests
from flask import Blueprint

strava_bp = Blueprint('strava', __name__)

@strava_bp.route("/test-strava")
def test_strava():
    ACCESS_TOKEN = "0eeaa84fe52d2b9149a4644fb9a6c54217a57169"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    res = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers
    )

    return res.json()