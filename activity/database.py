

import sqlite3
from datetime import date
    
    
    
##connect to the database.
def get_db():
    db = sqlite3.connect('fitness.db')
    db.row_factory = sqlite3.Row
    return db


def create_tables():
    db = get_db()
    c = db.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone_number TEXT,
            role TEXT NOT NULL DEFAULT 'casual',
            approved INTEGER NOT NULL DEFAULT 0,
            join_date DATE NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Trainer_Profile (
            trainer_profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            specialty TEXT NOT NULL,
            bio TEXT,
            average_rating REAL DEFAULT 0,
            total_reviews INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Trainer_Client (
            trainer_client_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            start_date DATE NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (trainer_id) REFERENCES User(id),
            FOREIGN KEY (client_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Trainer_Review (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            date DATE NOT NULL,
            FOREIGN KEY (trainer_id) REFERENCES User(id),
            FOREIGN KEY (client_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Session_Booking (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            date DATE NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (trainer_id) REFERENCES User(id),
            FOREIGN KEY (client_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Privacy_Settings (
            privacy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            pt_can_see_health_data INTEGER NOT NULL DEFAULT 0,
            pt_can_book_meetings INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS User_Goal (
            goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            step_target INTEGER,
            time_exercised_target INTEGER,
            workouts_per_week_target INTEGER,
            goal_type TEXT,
            target_date DATE,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Exercise_Type (
            exercise_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Training_Plan (
            plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            swims_per_week INTEGER,
            weekly_distance REAL,
            target_pace TEXT,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Planned_Workout (
            planned_workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            exercise_type_id INTEGER NOT NULL,
            planned_date DATE NOT NULL,
            target_duration INTEGER,
            target_distance REAL,
            FOREIGN KEY (plan_id) REFERENCES Training_Plan(plan_id),
            FOREIGN KEY (exercise_type_id) REFERENCES Exercise_Type(exercise_type_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Activity (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_type_id INTEGER NOT NULL,
            planned_workout_id INTEGER,
            date DATE NOT NULL,
            duration_minutes INTEGER,
            distance_km REAL,
            steps INTEGER,
            laps INTEGER,
            stroke_type TEXT,
            average_speed_kmh REAL,
            pace_per_km REAL,
            pace_per_100m REAL,
            calories INTEGER,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES User(id),
            FOREIGN KEY (exercise_type_id) REFERENCES Exercise_Type(exercise_type_id),
            FOREIGN KEY (planned_workout_id) REFERENCES Planned_Workout(planned_workout_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Competition (
            competition_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            date DATE NOT NULL,
            distance_km REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Competition_Registration (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            competition_id INTEGER NOT NULL,
            registration_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'registered',
            FOREIGN KEY (user_id) REFERENCES User(id),
            FOREIGN KEY (competition_id) REFERENCES Competition(competition_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Competition_Result (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            competition_id INTEGER NOT NULL,
            finish_time INTEGER NOT NULL,
            position INTEGER,
            goal_time INTEGER,
            FOREIGN KEY (user_id) REFERENCES User(id),
            FOREIGN KEY (competition_id) REFERENCES Competition(competition_id)
        )
    ''')

    #default data
    c.execute("SELECT COUNT(*) FROM Exercise_Type")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO Exercise_Type (name, description) VALUES ('Walking', 'Walking exercise')")
        c.execute("INSERT INTO Exercise_Type (name, description) VALUES ('Running', 'Running exercise')")
        c.execute("INSERT INTO Exercise_Type (name, description) VALUES ('Cycling', 'Cycling exercise')")
        c.execute("INSERT INTO Exercise_Type (name, description) VALUES ('Swimming', 'Swimming exercise')")

    c.execute("SELECT COUNT(*) FROM User")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO User (username, first_name, last_name, email, password, role, join_date)
            VALUES ('james123', 'James', 'Smith', 'james123@gmail.com', 'password123', 'casual', ?)
        ''', (date.today().isoformat(),))

    db.commit()
    db.close()


 #test user
def get_current_user_id():
   
    return 1


def get_user_by_id(user_id):
    ##find a user by their id
    db = get_db()
    user = db.execute("SELECT * FROM User WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return user


def get_user_by_username(username):
    ##Find a user by their username
    db = get_db()
    user = db.execute("SELECT * FROM User WHERE username = ?", (username,)).fetchone()
    db.close()
    return user


def get_exercise_type_id(exercise_name):
    db = get_db()
    result = db.execute(
        "SELECT exercise_type_id FROM Exercise_Type WHERE name = ?", (exercise_name,)
    ).fetchone()
    db.close()
    return result['exercise_type_id'] if result else None