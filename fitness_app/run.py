print("HELLO BEFORE IMPORTS")

from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

print("STARTING APP")

#to:do make password mandatory field and email unique
app=Flask(__name__)
#just needs to be randomised and long
app.secret_key="1c35fe09f628846993187fee18334585"

#Configure SQL Alchemy to work with Flask
app.config["SQLALCHEMY_DATABASE_URI"]= "sqlite:///fitness_app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db=SQLAlchemy(app)

#Database Model

class User(db.Model):
    __tablename__='users' #so we can all use the same database and user info is stored in a table
    #class variables
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(25), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    bio= db.Column(db.Text, nullable=True)

    # approved boolean to manage PTs
    date_joined = db.Column(db.DateTime, default=datetime.utcnow) 
    approved = db.Column(db.Boolean, default=True, nullable=False)

    #goals and privacy
    goals = db.relationship('UserGoal', backref='user', uselist=False, cascade="all, delete-orphan")
    privacy = db.relationship('PrivacySettings', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash=generate_password_hash(password)
        

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserGoal(db.Model):
    __tablename__ = 'user_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    step_target = db.Column(db.Integer, default=10000)
    weekly_exercise_hours = db.Column(db.Integer, default=0)
    workouts_per_week = db.Column(db.Integer, default=0)

class PrivacySettings(db.Model):
    __tablename__ = 'privacy_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    share_with_pt = db.Column(db.Boolean, default=False)
    allow_meetings = db.Column(db.Boolean, default=False)


#Routes

#Login
#GET for the page, POST for the form
@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for('user_settings'))

    if request.method=="POST":
        #Collect information from form
        print("FORM SUBMITTED")
        username=request.form["username"]
        password=request.form["password"]
        user=User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['username']=username
            return redirect(url_for('user_settings'))
        else:
            return render_template("login.html", error="Invalid username or password")
            #Check information is in the database (already registered)
            #show home page if not in database
    return render_template("login.html")

#Register, NEED TO ADD ROLE AND ACTIVITY GOALS, PERMISSION FOR PT TO SEE DATA, SET UP MEETINGS AND LINK TO FORM TO GET HELP/FAQs
@app.route("/register", methods=["GET", "POST"])
def register():
    print("REGISTER PAGE LOADED")
    if request.method=="POST":
        print("REACHED THE REGISTER ROUTE")
        #Collect information from form, add extra information compared to login
        username=request.form["username"]
        password=request.form["password"]
        confirm_password=request.form["confirm_password"]
        email=request.form["email"]
        phone_number=request.form["phone"]
        role = request.form.get("role")
        bio = request.form.get("bio") if role == "pt" else None
        user=User.query.filter_by(username=username).first()

        #validate password and confirm_password are the same
        if password != confirm_password:
            return render_template("register.html", error="Passwords don't match, please re-enter")
        
        #check username isn't already taken
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username is taken, please choose another one")

        #check email isn't already taken
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email is already registered")
        
        #PTs need to be approved, everyone else ok
        is_approved = False if role == "pt" else True
    
        #create and save new user if password and username valid
        new_user=User(username=username, 
                      email=email, 
                      phone_number=phone_number,
                      role=role, 
                      approved=(False if role == "pt" else True),
                      bio=bio
                      )
        new_user.set_password(password)

        #create goals and link to user 
        new_goals = UserGoal(
            user=new_user,
            step_target=request.form.get("step_target", 10000) or 10000,
            weekly_exercise_hours=request.form.get("weekly_hours", 0) or 0,
            workouts_per_week=request.form.get("workouts_per_week", 0) or 0,
        )

        #privacy settings and link to user
        new_privacy = PrivacySettings(
            user=new_user,
            share_with_pt=True if request.form.get("share_with_pt") else False,
            allow_meetings=True if request.form.get("allow_meetings") else False
        )

        db.session.add(new_user)
        db.session.add(new_goals)
        db.session.add(new_privacy)
        db.session.commit()


        session['username']=new_user.username # easier for others to use username on their pages if needed
        return redirect(url_for('user_settings'))
    
    return render_template("register.html")


#User settings
@app.route("/settings")
def user_settings():
    if "username" not in session:
        return redirect(url_for('login'))
    user=User.query.filter_by(username=session["username"]).first()
    return render_template("user_settings.html", user=user)

@app.route("/update_privacy", methods=["POST"])
def update_privacy():
    if "username" not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session["username"]).first()
    # Update the linked privacy table instead of the user table
    user.privacy.share_with_pt = True if request.form.get("share_with_pt") else False
    user.privacy.allow_meetings = True if request.form.get("allow_meetings") else False
    
    db.session.commit()
    return redirect(url_for('user_settings'))

#Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)