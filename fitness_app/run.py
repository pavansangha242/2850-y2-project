from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

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
    password_hash = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(25), nullable=False)

    def set_password(self, password):
        self.password_hash=generate_password_hash(password)
        

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




#Routes

#Login
#GET for the page, POST for the
@app.route("/", methods["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for('user_settings'))

@app.route("/register")
def register():
    return render_template("register.html")

#Login
@app.route("/login", methods=["POST"])
def login():
    #Collect information from form
    username=request.form["username"]
    password=request.form["password"]
    user=User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['username']=username
        return redirect(url_for('user_settings'))
    else:
        return render_template("login.html")
    #Check information is in the database (already registered)

    #Show home page if not in database
#Register
@app.route("/register", methods=["POST"])
def register():
    username=request.form["username"]
    password=request.form["password"]
    user=User.query.filter_by(username=username).first()
    #email+phone+validate pass to do
    if user:
        return render_template("login.html", error="This user already exists!")
    else:
        new_user=User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['username']=username
        return redirect(url_for('user_settings'))


#User settings


#Logout



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)