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
    # ---- auth routes ----
    from routes.auth import auth
    app.register_blueprint(auth)

    return app