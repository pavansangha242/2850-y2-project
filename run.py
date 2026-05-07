"""Application entry point for running the Flask server."""

from dotenv import load_dotenv

from fitness_app import create_app
from fitness_app.extensions import db

load_dotenv()
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
