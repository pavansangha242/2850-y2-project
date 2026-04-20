import os
from flask import Flask
from fitness_app1.extentions import db
from fitness_app1.module import seed_data


#set up the flask app and return it
def create_app():
    app = Flask(__name__)

    #config stuff
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    #db file goes one folder up
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'fitness.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    #start extensions
    db.init_app(app)

    #bring in all the blueprints
    from fitness_app1.routes.main import main_bp
    from fitness_app1.routes.swimming import swimming_bp
    from fitness_app1.routes.cycling import cycling_bp
    from fitness_app1.routes.running import running_bp
    from fitness_app1.routes.walking import walking_bp
    from fitness_app1.routes.gym import gym_bp

    #register them all
    app.register_blueprint(main_bp)
    app.register_blueprint(swimming_bp)
    app.register_blueprint(cycling_bp)
    app.register_blueprint(running_bp)
    app.register_blueprint(walking_bp)
    app.register_blueprint(gym_bp)

    #make db tables + put default data in
    with app.app_context():
        from fitness_app1 import module
        db.create_all()
        seed_data()

    return app