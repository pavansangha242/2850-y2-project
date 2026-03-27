
from flask import Flask, redirect, url_for
from database import create_tables

from swimming import show_swimming_page, log_swim, create_swimming_plan, set_swimming_goal, delete_swim
from cycling import show_cycling_page, log_ride, create_cycling_plan, set_cycling_goal, delete_ride
from running import show_running_page, log_run, create_running_plan, set_running_goal, delete_run
from walking import show_walking_page, log_walk, create_walking_plan, set_walking_goal, delete_walk

app = Flask(__name__)
app.secret_key = '1919iiekslsklxmjxk' 


# when someone goes to the homepage just send them to swimming for now
@app.route('/')
def home():
    return redirect(url_for('swimming'))


##swimming routes
#each route just calls the matching function from swimming.py

@app.route('/swimming')
def swimming():
    return show_swimming_page()

@app.route('/swimming/log', methods=['POST'])
def swimming_log():
    return log_swim()

@app.route('/swimming/plan', methods=['POST'])
def swimming_plan():
    return create_swimming_plan()

@app.route('/swimming/goal', methods=['POST'])
def swimming_goal():
    return set_swimming_goal()

@app.route('/swimming/delete/<int:activity_id>')
def swimming_delete(activity_id):
    return delete_swim(activity_id)


#cycling routes

@app.route('/cycling')
def cycling():
    return show_cycling_page()

@app.route('/cycling/log', methods=['POST'])
def cycling_log():
    return log_ride()

@app.route('/cycling/plan', methods=['POST'])
def cycling_plan():
    return create_cycling_plan()

@app.route('/cycling/goal', methods=['POST'])
def cycling_goal():
    return set_cycling_goal()

@app.route('/cycling/delete/<int:activity_id>')
def cycling_delete(activity_id):
    return delete_ride(activity_id)


#running routes

@app.route('/running')
def running():
    return show_running_page()

@app.route('/running/log', methods=['POST'])
def running_log():
    return log_run()

@app.route('/running/plan', methods=['POST'])
def running_plan():
    return create_running_plan()

@app.route('/running/goal', methods=['POST'])
def running_goal():
    return set_running_goal()

@app.route('/running/delete/<int:activity_id>')
def running_delete(activity_id):
    return delete_run(activity_id)


#walking routes

@app.route('/walking')
def walking():
    return show_walking_page()

@app.route('/walking/log', methods=['POST'])
def walking_log():
    return log_walk()

@app.route('/walking/plan', methods=['POST'])
def walking_plan():
    return create_walking_plan()

@app.route('/walking/goal', methods=['POST'])
def walking_goal():
    return set_walking_goal()

@app.route('/walking/delete/<int:activity_id>')
def walking_delete(activity_id):
    return delete_walk(activity_id)


#start
if __name__ == '__main__':
    create_tables()  # make sure all the tables exist before we start
    app.run(debug=True)