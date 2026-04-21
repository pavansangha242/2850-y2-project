from flask import Blueprint, redirect, url_for

auth = Blueprint('auth', __name__)

@auth.route('/')
def home():
    return redirect(url_for('progress.progress_page'))