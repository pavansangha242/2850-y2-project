# messages.py for messaging between customers and trainers
# messages: customer views their trainer conversations
# trainer inbox: trainer views all client messages

from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import or_, and_

from fitness.extentions import db
from fitness.models import User, TrainerProfile, TrainerMessage

messages_bp = Blueprint('messages', __name__)


# user massgaes page

@messages_bp.route('/messages')
def messages():
    user = User.query.first()
    if not user:
        return "No users found in database."

    selected_id = request.args.get('trainer_id', type=int)

    # find all trainers this user has talked to
    subq = db.session.query(
        db.case(
            (TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id),
            else_=TrainerMessage.sender_id
        )
    ).filter(
        or_(
            TrainerMessage.sender_id == user.user_id,
            TrainerMessage.receiver_id == user.user_id
        )
    ).distinct().all()

    trainer_ids = [r[0] for r in subq]

    conversations = []
    for tid in trainer_ids:
        trainer = User.query.get(tid)
        if not trainer:
            continue

        profile = TrainerProfile.query.filter_by(user_id=tid).first()

        latest = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == tid),
                and_(TrainerMessage.sender_id == tid, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.desc()).first()

        unread = TrainerMessage.query.filter_by(
            sender_id=tid,
            receiver_id=user.user_id,
            is_read=False
        ).count()

        conversations.append({
            'trainer': trainer,
            'profile': profile,
            'latest': latest,
            'unread': unread,
        })

    conversations.sort(
        key=lambda x: x['latest'].sent_at if x['latest'] else 0,
        reverse=True
    )

    selected_trainer = None
    msgs = []

    if selected_id:
        selected_trainer = User.query.get(selected_id)
    elif conversations:
        selected_trainer = conversations[0]['trainer']
        selected_id = selected_trainer.user_id

    if selected_trainer:
        # mark messages as read when conversation is opened
        TrainerMessage.query.filter_by(
            sender_id=selected_trainer.user_id,
            receiver_id=user.user_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()

        msgs = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == selected_trainer.user_id),
                and_(TrainerMessage.sender_id == selected_trainer.user_id, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.asc()).all()

    selected_profile = TrainerProfile.query.filter_by(user_id=selected_id).first() if selected_id else None

    return render_template(
        'messages.html',
        current_user=user,
        conversations=conversations,
        selected_trainer=selected_trainer,
        selected_profile=selected_profile,
        messages=msgs,
        selected_id=selected_id,
    )


@messages_bp.route('/messages/send', methods=['POST'])
def send_user_message():
    user = User.query.first()
    if not user:
        return "No users found in database."

    trainer_id = request.form.get('trainer_id', type=int)
    message_txt = request.form.get('message', '').strip()

    if trainer_id and message_txt:
        msg = TrainerMessage(
            sender_id=user.user_id,
            receiver_id=trainer_id,
            message=message_txt
        )
        db.session.add(msg)
        db.session.commit()

    return redirect(url_for('messages.messages') + f'?trainer_id={trainer_id}')


# trainer inbox page

@messages_bp.route('/trainer/inbox')
def trainer_inbox():
    user = User.query.filter_by(username='ahmed_ali').first()
    if not user:
        return "Ahmed trainer not found."

    selected_id = request.args.get('client_id', type=int)
    search = request.args.get('q', '').strip().lower()

    # find all clients this trainer has talked to
    subq = db.session.query(
        db.case(
            (TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id),
            else_=TrainerMessage.sender_id
        )
    ).filter(
        or_(
            TrainerMessage.sender_id == user.user_id,
            TrainerMessage.receiver_id == user.user_id
        )
    ).distinct().all()

    client_ids = [r[0] for r in subq]

    conversations = []
    for cid in client_ids:
        client = User.query.get(cid)
        if not client:
            continue

        first_name = (client.first_name or '').lower()
        last_name = (client.last_name or '').lower()

        if search and search not in first_name and search not in last_name:
            continue

        latest = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == cid),
                and_(TrainerMessage.sender_id == cid, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.desc()).first()

        unread = TrainerMessage.query.filter_by(
            sender_id=cid,
            receiver_id=user.user_id,
            is_read=False
        ).count()

        goal_text = ''
        if hasattr(client, 'goals') and client.goals:
            goal_text = client.goals.goal_type or ''

        conversations.append({
            'client': client,
            'latest': latest,
            'unread': unread,
            'goal': goal_text,
        })

    conversations.sort(
        key=lambda x: x['latest'].sent_at if x['latest'] else 0,
        reverse=True
    )

    selected_client = None
    msgs = []

    if selected_id:
        selected_client = User.query.get(selected_id)
    elif conversations:
        selected_client = conversations[0]['client']
        selected_id = selected_client.user_id

    if selected_client:
        # mark messages as read when conversation is opened
        TrainerMessage.query.filter_by(
            sender_id=selected_client.user_id,
            receiver_id=user.user_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()

        msgs = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == selected_client.user_id),
                and_(TrainerMessage.sender_id == selected_client.user_id, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.asc()).all()

    selected_goal = ''
    if selected_client and hasattr(selected_client, 'goals') and selected_client.goals:
        selected_goal = selected_client.goals.goal_type or ''

    total_unread = TrainerMessage.query.filter_by(
        receiver_id=user.user_id,
        is_read=False
    ).count()

    return render_template(
        'trainer_inbox.html',
        current_user=user,
        conversations=conversations,
        selected_client=selected_client,
        selected_goal=selected_goal,
        messages=msgs,
        selected_id=selected_id,
        search=search,
        total_unread=total_unread,
    )


@messages_bp.route('/trainer/inbox/send', methods=['POST'])
def send_trainer_message():
    user = User.query.filter_by(username='ahmed_ali').first()
    if not user:
        return "Ahmed trainer not found."

    client_id = request.form.get('client_id', type=int)
    message_txt = request.form.get('message', '').strip()

    if client_id and message_txt:
        msg = TrainerMessage(
            sender_id=user.user_id,
            receiver_id=client_id,
            message=message_txt
        )
        db.session.add(msg)
        db.session.commit()

    return redirect(url_for('messages.trainer_inbox') + f'?client_id={client_id}')