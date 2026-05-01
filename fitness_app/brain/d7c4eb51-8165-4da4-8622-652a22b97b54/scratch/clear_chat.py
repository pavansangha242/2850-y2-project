from fitness_app import create_app
from fitness_app.extensions import db
from fitness_app.models import ChatMessage, TrainerMessage

app = create_app()
with app.app_context():
    try:
        db.session.query(ChatMessage).delete()
        db.session.query(TrainerMessage).delete()
        db.session.commit()
        print("Successfully cleared all chat history!")
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing chat: {e}")
