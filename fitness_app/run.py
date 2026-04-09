from flask import Flask
from extensions import db

def create_app():
    app = Flask(__name__)
    app.secret_key = "1c35fe09f628846993187fee18334585"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fitness_app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from routes.auth import auth
    app.register_blueprint(auth)

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)