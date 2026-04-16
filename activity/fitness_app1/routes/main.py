from flask import Blueprint, redirect, url_for

main_bp = Blueprint('main', __name__)


# main page swimming
@main_bp.route('/')
def home():
    return redirect(url_for('swimming.swimming_page'))
