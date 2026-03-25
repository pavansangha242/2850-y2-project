from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

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

    def set_password(self, password):
        self.password_hash=generate_password_hash(password)
        

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




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
        user=User.query.filter_by(username=username).first()

        #validate password and confirm_password are the same
        if password != confirm_password:
            return render_template("register.html", error="Passwords don't match, please re-enter")
        
        #check username isn't already taken
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username is taken, please choose another one")
    
        #create and save new user if password and username valid
        new_user=User(username=username, email=email, phone_number=phone_number)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        print("USER SAVED:", username)

        session['username']=username # easier for others to use username on their pages if needed
        return redirect(url_for('user_settings'))
    
    return render_template("register.html")


#User settings
@app.route("/settings")
def user_settings():
    if "username" not in session:
        return redirect(url_for('login'))
    user=User.query.filter_by(username=session["username"]).first()
    return render_template("user_settings.html", user=user)


#Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)