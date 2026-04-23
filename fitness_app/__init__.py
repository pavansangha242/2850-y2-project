import os
from flask import Flask
from fitness_app.extensions import db



#set up the flask app
def create_app():
    app = Flask(__name__)

    #config stuff
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'fitness_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    #start extensions
    db.init_app(app)

    #bring in all the blueprints
    from fitness_app.routes.swimming import swimming_bp
    from fitness_app.routes.cycling import cycling_bp
    from fitness_app.routes.running import running_bp
    from fitness_app.routes.walking import walking_bp
    from fitness_app.routes.gym import gym_bp

    # register all the blueprints
    from fitness_app.routes.auth import auth
    from fitness_app.routes.progress import progress
    from fitness_app.routes.history import history
    from fitness_app.routes.sport_stats import sport_stats
    from fitness_app.routes.trainers import trainers
    from fitness_app.routes.messages import messages_bp

    #register all
    app.register_blueprint(main_bp)
    app.register_blueprint(swimming_bp)
    app.register_blueprint(cycling_bp)
    app.register_blueprint(running_bp)
    app.register_blueprint(walking_bp)
    app.register_blueprint(gym_bp)

    app.register_blueprint(auth)
    app.register_blueprint(progress)
    app.register_blueprint(history)
    app.register_blueprint(sport_stats)
    app.register_blueprint(trainers)
    app.register_blueprint(messages_bp)


    return app
