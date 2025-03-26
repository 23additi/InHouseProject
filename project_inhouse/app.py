from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session 
import mysql.connector
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# app.secret_key = "your_secret_key"  # Change this to a secure key
app.secret_key = "your_secret_key"  # Change this to a secure key
app.config["SESSION_TYPE"] = "filesystem"  # ✅ Store session data in files instead of browser cookies
app.config["SESSION_PERMANENT"] = False  # ✅ Keeps session active while the browser is open
app.config["SESSION_USE_SIGNER"] = True  # ✅ Encrypts session cookie for security
app.config["SESSION_FILE_DIR"] = "./flask_sessions"  # ✅ Stores session files

Session(app) 


# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'health_db'
}

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Establish MySQL connection
def get_db_connection():
    """Returns a database connection with dictionary cursor."""
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


# Initialize Database
def create_db():
    """Creates the database and required tables if they don't exist."""
    conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS health_db")
    cursor.close()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS registration (
                        user_id VARCHAR(255) PRIMARY KEY,
                        full_name VARCHAR(255) NOT NULL,
                        dob DATE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS profile (
                        user_id VARCHAR(20) PRIMARY KEY,  -- user_id as Primary Key (also a Foreign Key)
                        full_name VARCHAR(255) NOT NULL,  -- Full name fetched from registration table
                        age INT NOT NULL,  -- Age calculated from DOB in registration table
                        gender ENUM('Male', 'Female', 'Other') NOT NULL,
                        height INT NOT NULL,  -- Height in cm
                        weight INT NOT NULL,  -- Weight in kg
                        city VARCHAR(100) NOT NULL,
                        state VARCHAR(100) NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES registration(user_id) ON DELETE CASCADE
                      )''')

    conn.commit()
    conn.close()


# Call function to create database on start
create_db()


def calculate_age(dob):
    """Calculate age from date of birth (YYYY-MM-DD)."""
    birth_date = datetime.strptime(dob, "%Y-%m-%d")  # Convert string to date
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def generate_user_id(full_name, dob):
    """Generates a user_id using the first 4 letters of the full name + DOB (YYYYMMDD)."""
    name_part = full_name[:4].upper()  # First 4 letters in uppercase
    dob_part = dob.replace('-', '')   # Remove hyphens from DOB (YYYYMMDD)
    return f"{name_part}{dob_part}"


@app.route('/')
def register_page():
    """Render the registration page."""
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    """Handle user registration."""
    data = request.json
    full_name = data.get('full_name')
    dob = data.get('dob')
    email = data.get('email')
    password = data.get('password')

    user_id = generate_user_id(full_name, dob)  # Generate user_id
    password_hash = generate_password_hash(password)  # ✅ Hash the password

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO registration (user_id, full_name, dob, email, password) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, full_name, dob, email, password_hash))  # ✅ Store hashed password
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Registration successful! Your User ID is {user_id}.'})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)})


@app.route('/login')
def login_page():
    """Render the registration page."""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT user_id, password FROM registration WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    print("Session before login:", dict(session))  # ✅ Debugging before login

    if user and check_password_hash(user['password'], password):
        session.clear()  # ✅ Clear old session data
        session['user_id'] = user['user_id']  # ✅ Set user ID in session
        session.modified = True  # ✅ Ensure session updates
        print("Session after login:", dict(session))  # ✅ Debugging after setting session
        return redirect(url_for('profile'))
    
    flash("Invalid email or password.", "danger")
    return redirect(url_for('login'))




# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'GET':
#         return render_template('login.html')

#     email = request.form['email']
#     password = request.form['password']

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     query = "SELECT user_id, password FROM registration WHERE email = %s"
#     cursor.execute(query, (email,))
#     user = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if user:
#         print("User found in database:", user)

#         if check_password_hash(user['password'], password):
#             session['user_id'] = user['user_id']
#             print("Session after login:", session)  # Debugging log
#             flash("Login successful!", "success")
#             return redirect('profile.html')
#         else:
#             print("Password incorrect")
#             flash("Invalid email or password.", "danger")
#     else:
#         print("User not found")
#         flash("Invalid email or password.", "danger")

#     return redirect(url_for('login'))



@app.route('/profile')
def profile_page():
    """Render the registration page."""
    return render_template('profile.html')


# @app.route('/profile', methods=['GET'])
# def profile():
#     # if 'user_id' not in session:
#     #     flash("Please log in first.", "warning")
#     #     return redirect(url_for('login'))

#     user_id = session['user_id']

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         # Fetch name and DOB (for age calculation) from registration table
#         cursor.execute("SELECT full_name, dob FROM registration WHERE user_id = %s", (user_id,))
#         user_data = cursor.fetchone()

#         if not user_data:
#             flash("User not found in registration table.", "danger")
#             return redirect(url_for('login'))

#         # Calculate age from DOB
#         birth_date = datetime.strptime(user_data['dob'], "%Y-%m-%d")
#         today = datetime.today()
#         age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

#         # Fetch existing profile data from profile table
#         cursor.execute("SELECT * FROM profile WHERE user_id = %s", (user_id,))
#         profile = cursor.fetchone() or {}

#         # Add name and age to profile data
#         profile['full_name'] = user_data['full_name']
#         profile['age'] = age

#         return render_template('profile.html', profile=profile)

#     except mysql.connector.Error as e:
#         flash(f"Database error: {e}", "danger")
#         return redirect(url_for('login'))

#     finally:
#         if conn:
#             conn.close()

@app.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        print("Session lost! No user_id found.")  # 🔹 If session is missing
        return jsonify({"message": "Unauthorized", "success": False}), 401

    user_id = session['user_id']
    print("Profile page: Session user_id =", user_id)  # ✅ Debugging log

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch name and DOB for age calculation
        cursor.execute("SELECT full_name, dob FROM registration WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            flash("User not found in registration table.", "danger")
            return redirect(url_for('login'))

        # Calculate age
        birth_date = datetime.strptime(user_data['dob'], "%Y-%m-%d")
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Fetch profile data
        cursor.execute("SELECT * FROM profile WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone() or {}

        profile['full_name'] = user_data['full_name']
        profile['age'] = age

        return render_template('profile.html', profile=profile)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('login'))

    finally:
        conn.close()



conn = mysql.connector.connect(
    host='localhost', user='root', password='1234', database='health_db'
)
cursor = conn.cursor()


# @app.route('/update_profile', methods=['POST'])
# def update_profile():
#     # Fetch user_id from session (or form if necessary)
#     user_id = session.get('user_id')  # Ensure user is logged in
#     if not user_id:
#         return jsonify({'success': False, 'message': 'User not logged in'})

#     # Fetch data from the form
#     gender = request.form['gender']
#     height = request.form['height']
#     weight = request.form['weight']
#     city = request.form['city']
#     state = request.form['state']

#     # Execute the query
#     query = """
#     INSERT INTO profile (user_id, full_name, age, gender, height, weight, city, state)
#     SELECT 
#         r.user_id, 
#         r.full_name, 
#         TIMESTAMPDIFF(YEAR, r.dob, CURDATE()) AS age, 
#         %s, %s, %s, %s, %s
#     FROM registration r
#     WHERE r.user_id = %s
#     ON DUPLICATE KEY UPDATE 
#         gender = VALUES(gender),
#         height = VALUES(height),
#         weight = VALUES(weight),
#         city = VALUES(city),
#         state = VALUES(state);
#     """

#     cursor.execute(query, (gender, height, weight, city, state, user_id))
#     conn.commit()

#     return jsonify({'success': True, 'message': 'Profile updated successfully!'})

# @app.route('/check_session')
# def check_session():
#     if 'user_id' in session:
#         return jsonify({'logged_in': True})
#     return jsonify({'logged_in': False}), 401


@app.route("/update_profile", methods=["POST"])
def update_profile():
    print("Session data before update:", dict(session))  # ✅ Debugging session

    if "user_id" not in session:
        print("Session lost! No user_id found.")  # ✅ Debugging log
        return jsonify({"message": "Unauthorized", "success": False}), 401  

    user_id = session["user_id"]
    print("Profile update: user_id =", user_id)  # ✅ Debugging log

    try:
        data = request.get_json()  

        gender = data.get('gender')
        height = data.get('height')
        weight = data.get('weight')
        city = data.get('city')
        state = data.get('state')

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO profile (user_id, full_name, age, gender, height, weight, city, state)
        SELECT 
            r.user_id, 
            r.full_name, 
            TIMESTAMPDIFF(YEAR, r.dob, CURDATE()) AS age, 
            %s, %s, %s, %s, %s
        FROM registration r
        WHERE r.user_id = %s
        ON DUPLICATE KEY UPDATE 
            gender = VALUES(gender),
            height = VALUES(height),
            weight = VALUES(weight),
            city = VALUES(city),
            state = VALUES(state);
        """

        cursor.execute(query, (gender, height, weight, city, state, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Profile updated successfully!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500  



@app.route('/homepage')
def homepage():
    """Render the home page."""
    return render_template('index.html')


# <!-- EHR Module -->
@app.route('/ehr')
def ehr():
    """Render the ehr dashboard."""
    return render_template('ehr.html')



# <!-- Diet Recommendation Module -->
@app.route('/diet')
def diet():
    """Render the diet."""
    return render_template('diet.html')


# <!-- Find Doctor Module -->
@app.route('/doctors')
def doctors():
    """Render the find doctor."""
    return render_template('index2.html')




if __name__ == '__main__':
    app.run(debug=True)


# from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
# import mysql.connector
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime
# from flask import send_from_directory
# import requests,os
# import logging
# import sqlite3
# import google.generativeai as genai
# from werkzeug.security import generate_password_hash, check_password_hash
# from reportlab.lib.pagesizes import letter, portrait
# # from reportlab.pdfgen import canvas
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,PageBreak
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib.units import inch
# from bs4 import BeautifulSoup




# app = Flask(__name__)
# app.secret_key = "your_secret_key"  # Change this to a secure key


# # Database Configuration
# DB_CONFIG = {
#     'host': 'localhost',  # Change this if using a remote database
#     'user': 'root',
#     'password': '1234',
#     'database': 'health_db'
# }


# UPLOAD_FOLDER = "uploads"
# if not os.path.exists(UPLOAD_FOLDER):
#     os.makedirs(UPLOAD_FOLDER)

# # Establish MySQL connection
# def get_db_connection():
#     return mysql.connector.connect(**DB_CONFIG)

# # Initialize Database
# def create_db():
#     """Creates the database and required tables if they don't exist."""
#     conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
#     cursor = conn.cursor()
#     cursor.execute("CREATE DATABASE IF NOT EXISTS health_db")
#     cursor.close()
#     conn.close()

#     conn = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor()

#     cursor.execute('''CREATE TABLE IF NOT EXISTS registration (
#                         user_id VARCHAR(255) PRIMARY KEY,
#                         full_name VARCHAR(255) NOT NULL,
#                         dob DATE NOT NULL,
#                         email VARCHAR(255) UNIQUE NOT NULL,
#                         password VARCHAR(255) NOT NULL
#                       )''')
#     conn.commit()
#     conn.close()

# # Call function to create database on start
# create_db()

# def calculate_age(dob):
#     """Calculate age from date of birth (YYYY-MM-DD)."""
#     birth_date = datetime.strptime(dob, "%Y-%m-%d")  # Convert string to date
#     today = datetime.today()
#     age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
#     return age

# def generate_user_id(full_name, dob):
#     """Generates a user_id using the first 4 letters of the full name + DOB (YYYYMMDD)."""
#     name_part = full_name[:4].upper()  # First 4 letters in uppercase
#     dob_part = dob.replace('-', '')   # Remove hyphens from DOB (YYYYMMDD)
#     return f"{name_part}{dob_part}"

# @app.route('/')
# def register_page():
#     """Render the registration page."""
#     return render_template('register.html')

# @app.route('/register', methods=['POST'])
# def register():
#     """Handle user registration."""
#     data = request.json
#     full_name = data.get('full_name')
#     dob = data.get('dob')
#     email = data.get('email')
#     password = data.get('password')

#     user_id = generate_user_id(full_name, dob)  # Generate user_id

#     try:
#         conn = mysql.connector.connect(**DB_CONFIG)
#         cursor = conn.cursor()
#         cursor.execute("INSERT INTO registration (user_id, full_name, dob, email, password) VALUES (%s, %s, %s, %s, %s)",
#                        (user_id, full_name, dob, email, password))
#         conn.commit()
#         conn.close()
#         return jsonify({'success': True, 'message': f'Registration successful! Your User ID is {user_id}.'})
#     except mysql.connector.Error as err:
#         return jsonify({'success': False, 'message': str(err)})



# def get_db_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="1234",
#         database="health_db"
#     )


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'GET':
#         return render_template('login.html')

#     email = request.form['email']
#     password = request.form['password']

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     # cursor = conn.cursor()
#     cursor.execute("SELECT * FROM registration WHERE email = %s", (email,)) 
#     user = cursor.fetchone()
#     conn.close()

#     if user and check_password_hash(user['password'], password):
#         session['user_id'] = user['user_id']
#         return redirect(url_for('profile'))
#     flash("Invalid email or password.", "danger")
#     return redirect(url_for('login'))





# @app.route('/profile', methods=['GET', 'POST'])  # ✅ Allow both GET and POST
# def profile():
#     if 'user_id' not in session:
#         flash("Please log in first.", "warning")
#         return redirect(url_for('login'))  # Redirect to login if session is missing

#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         cursor.execute("SELECT * FROM profile WHERE user_id = %s", (session['user_id'],))
#         profile = cursor.fetchone()

#         if not profile:
#             flash("Profile not found. Please complete your profile.", "warning")
#             return redirect(url_for('update_profile'))  # Redirect if profile is missing

#         return render_template('profile.html', profile=profile)

#     except mysql.connector.Error as e:
#         flash(f"Database error: {e}", "danger")
#         return redirect(url_for('login'))

#     finally:
#         if conn is not None:
#             conn.close()





# @app.route('/update_profile', methods=['GET', 'POST'])  # ✅ Allow GET for form display
# def update_profile():
#     if request.method == 'POST':
#         flash("Profile updated successfully!", "success")
#         return redirect(url_for('home'))

#     return render_template('update_profile.html')  # Show update form on GET request




# # Profile Route
# # @app.route('/profile', methods=['GET', 'POST'])
# # def profile():
# #     if 'user_id' not in session:
# #         flash("Please log in first.", "warning")
# #         return redirect(url_for('login'))

# #     user_id = session['user_id']

# #     # Fetch user details from MySQL
# #     conn = mysql.connector.connect(**db_config)
# #     cursor = conn.cursor(dictionary=True)
# #     cursor.execute("SELECT full_name, dob FROM registration WHERE user_id = %s", (user_id,))
# #     user = cursor.fetchone()

# #     if user:
# #         full_name = user['full_name']
# #         dob = user['dob']
# #         age = calculate_age(dob)
# #     else:
# #         flash("User not found!", "danger")
# #         return redirect(url_for('login'))

# #     conn.close()

#     # return render_template('profile.html', full_name=full_name, dob=dob, age=age)

# # Logout Route
# @app.route('/logout')
# def logout():
#     session.clear()
#     flash("You have been logged out.", "info")
#     return redirect(url_for('login'))












# @app.route('/diet')
# def diet():
#     return render_template('diet.html')

# def fetch_user_profile(user_id):
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     cursor.execute("SELECT dob, height, weight, state FROM profile WHERE user_id = %s", (user_id,))
#     profile = cursor.fetchone()
#     conn.close()

#     if profile:
#         profile["age"] = calculate_age(profile["dob"])
#         return profile  # Returns {'dob': 'YYYY-MM-DD', 'height': X, 'weight': Y, 'state': 'Z', 'age': N}
    
#     return None  # If no profile found

# def generate_meal_plan(bmi, state, age, food_preference, activity_level):
#     if bmi < 18.5:
#         return f"High-calorie {food_preference} diet suitable for an underweight individual from {state}, age {age}, with {activity_level} activity level."
#     elif 18.5 <= bmi < 24.9:
#         return f"Balanced {food_preference} diet suitable for a healthy individual from {state}, age {age}, with {activity_level} activity level."
#     elif 25 <= bmi < 29.9:
#         return f"Low-calorie {food_preference} diet suitable for an overweight individual from {state}, age {age}, with {activity_level} activity level."
#     else:
#         return f"Low-sugar, low-calorie {food_preference} diet suitable for an obese individual from {state}, age {age}, with {activity_level} activity level."


# def calculate_bmi(weight, height):
#     if height == 0:
#         return None  # Prevent division by zero
#     return round(weight / ((height / 100) ** 2), 2)  # BMI formula


# @app.route('/calculate', methods=['POST'])
# def calculate():
#     user_id = request.form.get('user_id')  # Get user ID from form
#     food_preference = request.form.get('food_preference')  # Get food preference from form
#     activity_level = request.form.get('activity_level')  # Get activity level from form

#     # Fetch user profile from MySQL
#     profile = fetch_user_profile(user_id)
    
#     if not profile:
#         return jsonify({"error": "User profile not found"}), 404

#     # Extract details
#     age, height, weight, state = profile["age"], profile["height"], profile["weight"], profile["state"]

#     # Calculate BMI
#     bmi = calculate_bmi(weight, height)

#     # Generate Meal Plan
#     meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)

#     # Render result with user details
#     return render_template(
#         'result.html',
#         user_id=user_id,
#         age=age,
#         height=height,
#         weight=weight,
#         state=state,
#         bmi=bmi,
#         meal_plan=meal_plan
#     )


# # Function to extract table data from HTML using BeautifulSoup
# def extract_table_from_html(html_content):
#     soup = BeautifulSoup(html_content, "html.parser")
#     table_data = []

#     for row in soup.find_all("tr"):
#         cells = [Paragraph(cell.get_text(" ", strip=True), getSampleStyleSheet()["BodyText"]) for cell in row.find_all(["th", "td"])]
#         if cells:
#             table_data.append(cells)

#     return table_data

# @app.route('/generate_diet_pdf', methods=['POST'])
# def generate_diet_pdf():
#     meal_plan_html = request.form.get('meal_plan')
#     bmi = request.form.get('bmi')

#     if not meal_plan_html:
#         return jsonify({"success": False, "message": "No meal plan provided"})

#     filename = f"diet_plan_{int(datetime.now().timestamp())}.pdf"
#     filepath = os.path.join(UPLOAD_FOLDER, filename)

#     meal_plan_table = extract_table_from_html(meal_plan_html)
    
#     if not meal_plan_table or len(meal_plan_table) < 2:
#         return jsonify({"success": False, "message": "Invalid table format in meal plan"})

#     doc = SimpleDocTemplate(filepath, pagesize=portrait(letter))
#     elements = [Paragraph("<b>Your Diet Plan</b>", getSampleStyleSheet()["Title"])]
#     elements.append(Paragraph(f"<b>BMI:</b> {bmi}", getSampleStyleSheet()["Normal"]))
#     elements.append(Spacer(1, 12))
#     day_table = Table(meal_plan_table)
#     day_table.setStyle(TableStyle([
#         ('GRID', (0, 0), (-1, -1), 1, colors.black),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#     ]))
#     elements.append(day_table)
#     doc.build(elements)

#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO diet_reports (filename, upload_time) VALUES (%s, %s)", (filename, datetime.now()))
#     conn.commit()
#     conn.close()

#     return jsonify({"success": True, "filename": filename})

# @app.route('/diet_reports')
# def diet_reports():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, filename, upload_time FROM diet_reports ORDER BY upload_time DESC")
#     reports = cursor.fetchall()
#     conn.close()
#     return jsonify({"success": True, "reports": reports})

# if __name__ == '__main__':
#     app.run(debug=True)
