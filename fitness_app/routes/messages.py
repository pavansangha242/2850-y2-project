# messages.py for messaging between customers and trainers
# messages: customer views their trainer conversations
# trainer inbox: trainer views all client messages

from flask import Blueprint, render_template, request, redirect, url_for, session
from sqlalchemy import or_, and_

from fitness_app.extensions import db
from fitness_app.models import User, TrainerProfile, TrainerMessage, ChatMessage, Competition
from datetime import datetime

messages_bp = Blueprint('messages', __name__)

def get_logged_in_user():
    username = session.get('username')
    if not username:
        return None
    return User.query.filter_by(username=username).first()

# user massgaes page

@messages_bp.route('/messages')
def messages():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))

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
 
    user_ids = [r[0] for r in subq]
 
    conversations = []
    for uid in user_ids:
        contact = User.query.get(uid)
        if not contact:
            continue
 
        profile = TrainerProfile.query.filter_by(user_id=uid).first()
 
        latest = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == uid),
                and_(TrainerMessage.sender_id == uid, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.desc()).first()
 
        unread = TrainerMessage.query.filter_by(
            sender_id=uid,
            receiver_id=user.user_id,
            is_read=False
        ).count()
 
        conversations.append({
            'type': 'dm',
            'contact': contact,
            'profile': profile,
            'latest_msg': latest.message if latest else '',
            'latest_time': latest.sent_at if latest else datetime.min,
            'unread': unread,
        })
 
    # find all groups this user has chatted in
    group_subq = db.session.query(ChatMessage.competition_id).filter_by(user_id=user.user_id).distinct().all()
    for (gid,) in group_subq:
        comp = Competition.query.get(gid)
        if not comp: continue
        
        latest = ChatMessage.query.filter_by(competition_id=gid).order_by(ChatMessage.timestamp.desc()).first()
        
        conversations.append({
            'type': 'group',
            'group': comp,
            'latest_msg': latest.content if latest else '',
            'latest_time': latest.timestamp if latest else datetime.min,
            'unread': 0
        })
 
    conversations.sort(key=lambda x: x['latest_time'], reverse=True)
 
    selected_contact = None
    selected_group = None
    msgs = []
 
    if selected_group_id:
        selected_group = Competition.query.get(selected_group_id)
        if selected_group:
            msgs = ChatMessage.query.filter_by(competition_id=selected_group_id).order_by(ChatMessage.timestamp.asc()).all()
    elif selected_id:
        selected_contact = User.query.get(selected_id)
    elif conversations:
        # Auto-select the first conversation
        first = conversations[0]
        if first['type'] == 'dm':
            selected_contact = first['contact']
            selected_id = selected_contact.user_id
        else:
            selected_group = first['group']
            selected_group_id = selected_group.competition_id
            msgs = ChatMessage.query.filter_by(competition_id=selected_group_id).order_by(ChatMessage.timestamp.asc()).all()
 
    if selected_contact:
        # mark messages as read when conversation is opened
        TrainerMessage.query.filter_by(
            sender_id=selected_contact.user_id,
            receiver_id=user.user_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
 
        msgs = TrainerMessage.query.filter(
            or_(
                and_(TrainerMessage.sender_id == user.user_id, TrainerMessage.receiver_id == selected_contact.user_id),
                and_(TrainerMessage.sender_id == selected_contact.user_id, TrainerMessage.receiver_id == user.user_id)
            )
        ).order_by(TrainerMessage.sent_at.asc()).all()
 
    selected_profile = TrainerProfile.query.filter_by(user_id=selected_id).first() if selected_id else None
 
    normalized_messages = []
    for m in msgs:
        if hasattr(m, 'message'): # TrainerMessage
            normalized_messages.append({
                'is_mine': m.sender_id == user.user_id,
                'text': m.message,
                'time': m.sent_at,
                'author_name': user.first_name if m.sender_id == user.user_id else (selected_contact.first_name if selected_contact else 'Unknown')
            })
        else: # ChatMessage
            normalized_messages.append({
                'is_mine': m.user_id == user.user_id,
                'text': m.content,
                'time': m.timestamp,
                'author_name': m.author.first_name
            })

    return render_template(
        'messages.html',
        current_user=user,
        conversations=conversations,
        selected_contact=selected_contact,
        selected_group=selected_group,
        selected_profile=selected_profile,
        messages=normalized_messages,
        selected_id=selected_id,
        selected_group_id=selected_group_id
    )
 
 
@messages_bp.route('/messages/send', methods=['POST'])
def send_user_message():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))

    trainer_id = request.form.get('trainer_id', type=int)
    message_txt = request.form.get('message', '').strip()
 
    if contact_id and message_txt:
        msg = TrainerMessage(
            sender_id=user.user_id,
            receiver_id=contact_id,
            message=message_txt
        )
        db.session.add(msg)
        db.session.commit()
 
    return redirect(url_for('messages.messages') + f'?user_id={contact_id}')


# trainer inbox page

@messages_bp.route('/trainer/inbox')
def trainer_inbox():
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))
   
    if user.role != 'pt':
        return redirect(url_for('messages.messages'))

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
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    if user.role != 'pt':
        return redirect(url_for('messages.messages'))

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