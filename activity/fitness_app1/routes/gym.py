from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from fitness_app1.extentions import db
from fitness_app1.module import User, GymExercise, GymAssignment, GymWorkout, get_current_user_id

gym_bp = Blueprint('gym', __name__)


#  get the monday of this week
def get_week_start():
    today = date.today()
    # monday is 0 
    return today - timedelta(days=today.weekday())


@gym_bp.route('/gym')
def gym_page():
    # get the user who is logged in
    user = User.query.get_or_404(get_current_user_id())
    monday = get_week_start()

    # all the exer sorted by muscle group then name
    all_exercises = GymExercise.query.order_by(GymExercise.muscle_group, GymExercise.name).all()

    # list of different muscle groups
    m_groups = db.session.query(GymExercise.muscle_group)\
        .distinct()\
        .order_by(GymExercise.muscle_group)\
        .all()
    #list
    m_groups = [g[0] for g in m_groups]

    # get all the assignments the useer given by a trainer
    rows1 = db.session.query(GymAssignment, GymExercise, User)\
        .join(GymExercise, GymAssignment.gym_exercise_id == GymExercise.gym_exercise_id)\
        .join(User, GymAssignment.trainer_id == User.user_id)\
        .filter(GymAssignment.client_id == user.user_id)\
        .order_by(GymAssignment.date_assigned.desc())\
        .all()

    #put extra info onto each assignment so the template can show it
    my_assignments = []
    for a, ex, trainer in rows1:
        a.exercise_name = ex.name
        a.muscle_group = ex.muscle_group
        a.trainer_name = f'{trainer.first_name} {trainer.last_name}'
        my_assignments.append(a)

    #the workouts user done
    rows2 = db.session.query(GymWorkout, GymExercise)\
        .join(GymExercise, GymWorkout.gym_exercise_id == GymExercise.gym_exercise_id)\
        .filter(GymWorkout.user_id == user.user_id)\
        .order_by(GymWorkout.date.desc(), GymWorkout.gym_workout_id.desc())\
        .all()

    #add the exers name/ muscle type to each workout
    my_workouts = []
    for w, ex in rows2:
        w.exercise_name = ex.name
        w.muscle_group = ex.muscle_group
        my_workouts.append(w)

    #count how many different days the user went to g
    gym_days = db.session.query(func.count(func.distinct(GymWorkout.date)))\
        .filter(GymWorkout.user_id == user.user_id,
                GymWorkout.date >= monday)\
        .scalar() or 0

    #add all sets 
    sets_week = db.session.query(func.coalesce(func.sum(GymWorkout.sets_completed), 0))\
        .filter(GymWorkout.user_id == user.user_id,
                GymWorkout.date >= monday)\
        .scalar() or 0

    #muscle type user worked the most this week
    best_muscle = db.session.query(GymExercise.muscle_group, func.count(GymWorkout.gym_workout_id))\
        .join(GymWorkout, GymWorkout.gym_exercise_id == GymExercise.gym_exercise_id)\
        .filter(GymWorkout.user_id == user.user_id,
                GymWorkout.date >= monday)\
        .group_by(GymExercise.muscle_group)\
        .order_by(func.count(GymWorkout.gym_workout_id).desc())\
        .first()

    #none if nthing
    best_muscle_name = best_muscle[0] if best_muscle else 'None yet'

    # send everything to the html page
    return render_template(
        'gym.html',
        exercises=all_exercises,
        muscle_groups=m_groups,
        assignments=my_assignments,
        workouts=my_workouts,
        sessions_this_week=gym_days,
        total_sets_week=sets_week,
        top_muscle_name=best_muscle_name
    )


@gym_bp.route('/gym/log', methods=['POST'])
def log_gym_workout():
    #loged in user
    user = User.query.get_or_404(get_current_user_id())

    # form
    w_date = request.form.get('date')
    ex_id = request.form.get('gym_exercise_id', type=int)
    a_id = request.form.get('assignment_id', type=int)
    sets_done = request.form.get('sets_completed', type=int)
    reps_done = request.form.get('reps_completed', type=int)
    kg = request.form.get('weight_kg', type=float)
    mins = request.form.get('duration', type=int)
    note = request.form.get('notes')

    #error if they didnt choose
    if not ex_id:
        flash('Please choose an exercise.', 'error')
        return redirect(url_for('gym.gym_page'))

    #new workoutt/ save it
    new_workout = GymWorkout(
        user_id=user.user_id,
        gym_exercise_id=ex_id,
        assignment_id=a_id,
        date=date.fromisoformat(w_date) if w_date else date.today(),
        sets_completed=sets_done or 0,
        reps_completed=reps_done or 0,
        weight_kg=kg or 0.0,
        duration_minutes=mins or 0,
        notes=note or ''
    )

    db.session.add(new_workout)
    db.session.commit()

    flash('Gym workout logged!', 'success')
    return redirect(url_for('gym.gym_page'))


@gym_bp.route('/gym/assign', methods=['POST'])
def assign_exercise():
    # the trainer 
    trainer = User.query.get_or_404(get_current_user_id())

    # get the form data
    c_id = request.form.get('client_id', type=int)
    ex_id = request.form.get('gym_exercise_id', type=int)
    num_sets = request.form.get('sets', type=int)
    num_reps = request.form.get('reps', type=int)
    kg = request.form.get('weight_kg', type=float)
    note = request.form.get('notes')

    #they have to choose one clint or error
    if not c_id or not ex_id:
        flash('Client and exercise are required.', 'error')
        return redirect(url_for('gym.gym_page'))

    # make assignment
    new_assign = GymAssignment(
        trainer_id=trainer.user_id,
        client_id=c_id,
        gym_exercise_id=ex_id,
        sets=num_sets or 0,
        reps=num_reps or 0,
        weight_kg=kg or 0.0,
        notes=note or '',
        date_assigned=date.today()
    )

    db.session.add(new_assign)
    db.session.commit()

    flash('Exercise assigned!', 'success')
    return redirect(url_for('gym.gym_page'))


@gym_bp.route('/gym/delete/<int:gym_workout_id>', methods=['POST'])
def delete_gym_workout(gym_workout_id):
    # find the user
    user = User.query.get_or_404(get_current_user_id())

    # find workout only if itss to user
    w = GymWorkout.query.filter_by(
        gym_workout_id=gym_workout_id,
        user_id=user.user_id
    ).first_or_404()

    # delete it
    db.session.delete(w)
    db.session.commit()

    flash('Workout deleted.', 'success')
    return redirect(url_for('gym.gym_page'))