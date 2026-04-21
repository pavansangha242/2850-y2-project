import os
from flask import Flask
from fitness.extentions import db
from fitness.models import seed_data

def create_app():
    app = Flask(__name__)

    # set up config and database path
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'fitness.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # register all the blueprints
    from fitness.routes.auth import auth
    from fitness.routes.progress import progress
    from fitness.routes.history import history
    from fitness.routes.sport_stats import sport_stats
    from fitness.routes.trainers import trainers
    from fitness.routes.messages import messages_bp

    app.register_blueprint(auth)
    app.register_blueprint(progress)
    app.register_blueprint(history)
    app.register_blueprint(sport_stats)
    app.register_blueprint(trainers)
    app.register_blueprint(messages_bp)

    # create the tables and seed defualt data
    with app.app_context():
        db.create_all()
        seed_data()

    return app