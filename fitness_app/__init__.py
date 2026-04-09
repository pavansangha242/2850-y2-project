from flask import Flask
from extensions import db


def create_app():
    app = Flask(__name__)

    app.secret_key = "1c35fe09f628846993187fee18334585"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fitness_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialise extensions
    db.init_app(app)

    # Register blueprints
    # ---- Your auth routes ----
    from routes.auth import auth
    app.register_blueprint(auth)

    # ---- Add your teammates' blueprints here as they're ready ----
    # from routes.admin import admin
    # app.register_blueprint(admin)

    # from routes.events import events
    # app.register_blueprint(events)

    # from routes.activity import activity
    # app.register_blueprint(activity)

    return app