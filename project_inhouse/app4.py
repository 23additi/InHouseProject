from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify,send_from_directory,send_file
import MySQLdb
import pymysql
import mysql.connector
import pymysql.cursors
from datetime import datetime, date  , timedelta
import google.generativeai as genai
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import requests
import os
from reportlab.lib.pagesizes import letter, portrait
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from bs4 import BeautifulSoup
from io import BytesIO
import joblib
import pandas as pd

app = Flask(__name__)

# Flask Secure Cookie-Based Session Configuration
app.config["SECRET_KEY"] = "your_strong_secret_key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_NAME"] = "my_secure_session"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True if using HTTPS
app.secret_key = 'your_secret_key'  # Required for session handling
app.config['SESSION_TYPE'] = 'filesystem'  # Ensures session data is stored


# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'health_db'
    
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ✅ Save session as binary (BLOB)
def save_session_to_db(session_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()

    expiry = datetime.now() + timedelta(days=1)  # Session expires in 1 day
    pickled_data = pickle.dumps(data)  # ✅ Convert session data to binary

    query = """INSERT INTO sessions (session_id, data, expiry)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE data = %s, expiry = %s"""

    cursor.execute(query, (session_id, pickled_data, expiry, pickled_data, expiry))
    conn.commit()
    conn.close()

# # ✅ Load session as binary (BLOB)
# def load_session_from_db(session_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     query = "SELECT data FROM sessions WHERE session_id = %s AND expiry > NOW()"
#     cursor.execute(query, (session_id,))
#     result = cursor.fetchone()
#     conn.close()

#     if result and result[0]:
#         return pickle.loads(result[0])  # ✅ Convert binary back to dictionary
#     return {}

def load_session_from_db(session_id):
    conn = mysql.connector.connect(host="localhost", user="root", password="password", database="your_db")
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM sessions WHERE session_id = %s", (session_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:  # Ensure result exists before accessing index 0
        return result[0]  
    return None  # Return None if no session data found


# @app.before_request
# def before_request():
#     session.modified = True
#     session_id = session.get('session_id')

#     if session_id:
#         session_data = load_session_from_db(session_id)
#         session.update(session_data)

@app.before_request
def before_request():
    session_id = request.cookies.get("session_id")  # Ensure session_id is retrieved
    if session_id:
        session_data = load_session_from_db(session_id)
    else:
        session_data = None  # Handle missing session



@app.after_request
def after_request(response):
    session_id = session.get('session_id', str(datetime.now().timestamp()))
    session['session_id'] = session_id
    save_session_to_db(session_id, dict(session))  # ✅ Store session in MySQL
    return response

@app.route('/set_session')
def set_session():
    session["user_id"] = "USER12345"
    session["full_name"] = "John Doe"
    return "Session Set!"

@app.route('/get_session')
def get_session():
    return f"User ID: {session.get('user_id')}, Name: {session.get('full_name')}"

@app.route('/logout')
def logout():
    session_id = session.get('session_id')
    
    if session_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
        conn.commit()
        conn.close()

    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

def generate_user_id(full_name, dob):
    name_part = full_name[:4].upper()
    dob_part = dob.replace('-', '')
    return f"{name_part}{dob_part}"

def calculate_age(dob):
    if isinstance(dob, date):
        birth_date = dob
    else:
        birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
    
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

@app.route('/')
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    full_name, dob, email, password = data.get('full_name'), data.get('dob'), data.get('email'), data.get('password')
    user_id = generate_user_id(full_name, dob)
    password_hash = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO registration (user_id, full_name, dob, email, password) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, full_name, dob, email, password_hash))
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
    print("Received request with headers:", request.headers)  # Debugging step
    print("Request method:", request.method)  # Debugging step

    if request.headers.get("Content-Type") != "application/json":
        return jsonify({"success": False, "message": "Content-Type must be application/json"}), 415

    try:
        data = request.get_json(silent=True)  # ✅ Safe parsing of JSON
        print("Received request data:", data)  # Debugging step

        if not data:
            return jsonify({"success": False, "message": "Invalid JSON or empty request body"}), 400

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, full_name, password FROM registration WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]  # ✅ Store full name in session

            # ✅ Debugging session storage
            print("DEBUG: Session data after login:", session)  # Should print {'user_id': '123', 'full_name': 'John Doe'}
            print("Session user_id:", session.get("user_id"))

            return jsonify({
                "success": True, 
                "message": "Login successful!", 
                "redirect": url_for('profile'),
                "user_id": user["user_id"], 
                "full_name": user["full_name"]
            })

        return jsonify({"success": False, "message": "Invalid email or password"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    full_name = session.get('full_name')  # ✅ Get full_name from session

    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT dob FROM registration WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    user_data['full_name'] = full_name  # ✅ Ensure full_name is included
    user_data['age'] = calculate_age(user_data['dob'])

    cursor.execute("SELECT * FROM profile WHERE user_id = %s", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user=user_data, profile=profile)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if request.content_type != 'application/json':
        return jsonify({"success": False, "message": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    user_id = session.get('user_id')  # Get user_id from session
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    gender = data.get('gender')
    height = data.get('height')
    weight = data.get('weight')
    city = data.get('city')
    state = data.get('state')

    if not all([gender, height, weight, city, state]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
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
        conn.close()

        # ✅ Instead of returning HTML, return JSON with a redirect URL
        return jsonify({"success": True, "message": "Profile updated successfully!", "redirect": url_for('home')})

    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500



@app.route('/home')
def home():
    """Render the registration page."""
    return render_template('index.html')





#EHR
# Routes
app.config["UPLOAD_FOLDER"] = "uploads"

# MySQL Connection Setup
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='1234',
                             database='health_db')

cursor = connection.cursor(pymysql.cursors.DictCursor)  # Use DictCursor

@app.route('/ehr')
def ehr():
    return render_template('ehr.html')

@app.route('/ehr/doctor', methods=['GET', 'POST'])
def ehr_doctor():
    return render_template('ehr_doctors.html')

@app.route('/ehr/doctors')
def ehr_doctors():
    user_id = session.get('user_id')  # Assuming you have user authentication
    if not user_id:
        return redirect(url_for('login'))  # Redirect if not logged in
    
    conn = mysql.connector.connect(host="localhost", user="root", password="1234", database="health_db")
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT name, address, rating FROM selected_doctors WHERE user_id = %s ORDER BY rating DESC", (user_id,))
    doctors = cursor.fetchall()
    
    conn.close()
    return render_template('ehr_doctors.html', doctors=doctors)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"})

    if file:
        filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Save file info to MySQL
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            sql = "INSERT INTO reports (filename, upload_time) VALUES (%s, NOW())"
            cursor.execute(sql, (filename,))
            conn.commit()
            return jsonify({"success": True, "message": "File uploaded successfully"})
        except pymysql.MySQLError as e:
            return jsonify({"success": False, "message": f"Database error: {str(e)}"})
        finally:
            cursor.close()
            conn.close()

@app.route('/uploads')
def uploaded_files():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, upload_time FROM reports ORDER BY upload_time DESC")
    files = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('uploads.html', files=files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




#Diet
basic_prompt="I need it completely in html with styling.The data should be in white font color with quantity how much needs to be consumed should be written. Don't show any background color.There should be no suggestions and other information. Also don't include note or any extra information.The food nutrients should be displayed in a table format without background color and heading should be in white font color and bold in the left of the meal plan.The food nutrients should be in another table. Don't include tofu and provide diet according to age given. " 
# Directly set your API key here
my_api_key_gemini = "AIzaSyBWO2wo3W8jmaZ3ajUKAt8LOnYxxkldtso"  # Replace with your actual API key
genai.configure(api_key=my_api_key_gemini)

UPLOAD_FOLDER = os.path.join(app.root_path, "static/diet_records")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create folder if it doesn't exist



def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="health_db"
    )

@app.route('/diet')
def diet():
    return render_template('diet.html')

def fetch_user_profile(user_id):
    if not user_id:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT r.user_id, r.dob, p.height, p.weight, p.state, d.food_preference, d.activity_level
    FROM registration r
    JOIN profile p ON r.user_id = p.user_id
    JOIN diet d ON r.user_id = d.user_id
""")

    
    profile = cursor.fetchone()
    conn.close()
    
    print("🔍 Debug: Fetched profile from DB:", profile)  # Debugging

    if profile and profile['dob'] and profile['height'] and profile['weight'] and profile['state'] and profile['food_preference'] and profile['activity_level']:
        age = calculate_age(profile['dob'])
        return age, profile['height'], profile['weight'], profile['state'], profile['food_preference'], profile['activity_level']

    print("❌ Error: Missing data in profile")  # Debugging
    return None


def calculate_age(dob):
    birth_date = datetime.strptime(str(dob), "%Y-%m-%d")
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def calculate_bmi(weight, height):
    return weight / ((height / 100) ** 2)

def generate_meal_plan(bmi, state, age, food_preference, activity_level):
     # Create a prompt based on user data
    if bmi < 18.5:
        prompt = f"Create a weekly meal plan featuring high-calorie Indian dishes for a {food_preference} person of {age} from {state} who is underweight. Include breakfast, lunch, and dinner options.{basic_prompt}"
    elif 18.5 <= bmi < 24.9:
        prompt = f"Generate a balanced weekly meal plan featuring traditional Indian dishes for a {food_preference} person of {age} from {state} with a normal weight. Include healthy recipes for breakfast, lunch, and dinner.{basic_prompt}"
    elif 25 <= bmi < 29.9:
        prompt = f"Suggest a weekly meal plan for a {food_preference} person of {age} from {state} who is overweight. Include low-calorie Indian dishes for breakfast, lunch, and dinner.{basic_prompt}"
    else:
        prompt = f"Outline a weekly meal plan for a {food_preference} person of {age} from {state} who is obese. Include low-sugar and low-calorie Indian recipes for breakfast, lunch, and dinner.{basic_prompt}"

    # Call the Gemini API to generate the meal plan
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text.replace("```pdf","").replace("```","")

@app.route('/get_user_id', methods=['GET'])
def get_user_id():
    if 'user_id' in session:
        return jsonify({"user_id": session['user_id']})
    return jsonify({"error": "User not logged in"}), 401

# @app.route('/diet_plan', methods=['POST'])
# def get_diet_plan():
#     user_id = session.get('user_id')  # ✅ Fetch from session, not form
#     print("🔍 Debug: Retrieved user_id from session:", user_id)  # Debugging

#     if not user_id:
#         return jsonify({"error": "User ID is required"}), 400

#     profile_data = fetch_user_profile(user_id)
#     print("🔍 Debug: Profile Data:", profile_data)  # Debugging

#     if not profile_data:
#         return jsonify({"error": "User profile not found or incomplete"}), 404

#     age, height, weight, state, food_preference, activity_level = profile_data
#     print(f"✅ Retrieved: Age={age}, Height={height}, Weight={weight}, State={state}, Food Pref={food_preference}, Activity Level={activity_level}")  # Debugging

#     bmi = calculate_bmi(weight, height)
#     meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)
    
#     return render_template('result.html', bmi=bmi, meal_plan=meal_plan)

@app.route('/diet_plan', methods=['GET', 'POST'])
def diet_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if user is not logged in

    user_id = session['user_id']
    profile = fetch_user_profile(user_id)
    if not profile:
        return "Error: User profile data is incomplete", 400

    age, height, weight, state, food_preference, activity_level = profile
    bmi = calculate_bmi(weight, height)
    meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)

    # Store the meal plan in a session or pass it via URL parameters
    return render_template('result.html', food_preference=food_preference, activity_level=activity_level, meal_plan=meal_plan, bmi=bmi)


def extract_table_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    table_data = []
    for row in soup.find_all("tr"):
        cells = [Paragraph(cell.get_text(strip=True), getSampleStyleSheet()["BodyText"]) for cell in row.find_all(["th", "td"])]
        if cells:
            table_data.append(cells)
    return table_data

# @app.route('/generate_diet_pdf', methods=['POST'])
# def generate_diet_pdf():
#     meal_plan_html = request.form.get('meal_plan')
#     bmi = request.form.get('bmi')
#     if not meal_plan_html:
#         return jsonify({"success": False, "message": "No meal plan provided"})
    
#     filename = f"diet_plan_{int(datetime.now().timestamp())}.pdf"
#     filepath = os.path.join(UPLOAD_FOLDER, filename)
#     meal_plan_table = extract_table_from_html(meal_plan_html)
#     if not meal_plan_table:
#         return jsonify({"success": False, "message": "Invalid table format in meal plan"})
    
#     doc = SimpleDocTemplate(filepath, pagesize=portrait(letter))
#     elements = [Paragraph("Your Diet Plan", getSampleStyleSheet()["Title"]), Paragraph(f"BMI: {bmi}", getSampleStyleSheet()["Normal"]), Spacer(1, 12)]
#     table = Table(meal_plan_table)
#     table.setStyle(TableStyle([
#         ('GRID', (0, 0), (-1, -1), 1, colors.black),
#         ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
#     ]))
#     elements.append(table)
#     doc.build(elements)
    
#     # conn = get_db_connection()
#     # cursor = conn.cursor()
#     # cursor.execute("INSERT INTO diet_reports (filename, upload_time) VALUES (%s, %s)", (filename, datetime.now()))
#     # conn.commit()
#     # conn.close()
#     # return jsonify({"success": True, "filename": filename})
#     # Save to database
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO diet_reports (filename, upload_time) VALUES (%s, %s)",
#             (filename, datetime.now())
#         )
#         conn.commit()
#         conn.close()
#     except mysql.connector.Error as err:
#         print(f"❌ Database Error: {err}")
#         return jsonify({"success": False, "message": "Database error"}), 500

#     return jsonify({"success": True, "filename": filename})

# ✅ Ensure upload folder exists

# @app.route('/result')
# def result():
#     bmi = session.get('bmi', 'N/A')
#     meal_plan = session.get('meal_plan', 'No meal plan generated.')
#     filename = session.get('pdf_filename', None)  

#     # Debugging output
#     print(f"🟢 Debug: session['pdf_filename'] = {filename}")

#     return render_template('result.html', bmi=bmi, meal_plan=meal_plan, filename=filename)

# @app.route('/result')
# def result():
#     food_preference = request.args.get('food_preference', 'vegetarian')
#     activity_level = request.args.get('activity_level', 'sedentary')
#     meal_plan = "Generated meal plan data"
    
#     return render_template('result.html', food_preference=food_preference, activity_level=activity_level, meal_plan=meal_plan)


@app.route('/generate_diet_pdf', methods=['POST'])
def generate_diet_pdf():
    """Generates a PDF from meal plan HTML and sends it as a buffer to the client."""
    try:
        data = request.get_json()
        meal_plan_html = data.get("meal_plan")
        bmi = data.get("bmi")

        if not meal_plan_html:
            print("❌ No meal plan provided")
            return jsonify({"success": False, "message": "No meal plan provided"}), 400

        # Extract table from HTML
        meal_plan_table = extract_table_from_html(meal_plan_html)
        if not meal_plan_table:
            print("❌ Invalid table format in meal plan")
            return jsonify({"success": False, "message": "Invalid table format"}), 400

        print("✅ Generating PDF in memory...")

        # Use BytesIO buffer instead of writing to disk
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=portrait(letter))
        elements = [
            Paragraph("Your Diet Plan", getSampleStyleSheet()["Title"]),
            Paragraph(f"BMI: {bmi}", getSampleStyleSheet()["Normal"]),
            Spacer(1, 12)
        ]
        table = Table(meal_plan_table)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]))
        elements.append(table)
        doc.build(elements)

        # Move buffer pointer to beginning
        buffer.seek(0)

        print("✅ Sending PDF buffer to client...")

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"diet_plan_{int(datetime.now().timestamp())}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print(f"❌ Exception in PDF generation: {e}")
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/download_diet_pdf/<filename>')
def download_diet_pdf(filename):
    """Handles the PDF download."""
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return "Error: File not found", 404

    return send_file(filepath, as_attachment=True)

@app.route('/diet_reports')
def diet_reports():
    """Fetches all diet reports from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, filename, upload_time FROM diet_reports ORDER BY upload_time DESC")
        reports = cursor.fetchall()
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
        return jsonify({"success": False, "message": "Database error"}), 500

    return jsonify({"success": True, "reports": reports})




#DOCTOR
@app.route('/find_doctor')
def doctor():
    return render_template('index3.html')

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="health_db"
)

# Fetch doctors from Google Places API
def fetch_doctors(city, specialty, api_key):
    query = f"{specialty} in {city}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [
            {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                # Return None if rating is missing or not a float
                "rating": float(place.get("rating")) if place.get("rating") is not None else None,
            }
            for place in data.get("results", [])
        ]
    return None

# Save selected doctors
# @app.route('/save_selected', methods=['POST'])
# def save_selected():
#     selected_ids = request.form.getlist('selected_doctors')
#     if not selected_ids:
#         return redirect(url_for('find_doctors'))

#     try:
#         cursor = db.cursor(dictionary=True)
#         for doctor_id in selected_ids:
#             name = request.form.get(f"name_{doctor_id}")
#             address = request.form.get(f"address_{doctor_id}")
#             rating = request.form.get(f"rating_{doctor_id}")
#             try:
#                 rating = float(rating)
#             except (TypeError, ValueError):
#                 rating = None

#             cursor.execute(''' 
#                 INSERT INTO selected_doctors (name, address, rating)
#                 VALUES (%s, %s, %s)
#             ''', (name, address, rating))
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         # Log the error or print for debugging
#         print(f"Error saving selected doctors: {e}")
#     finally:
#         cursor.close()

#     return redirect('/homepage')

# Configure MySQL connection (Update with your credentials)
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="1234",
    db="health_db",
    charset="utf8"
)
cursor = db.cursor()

@app.route('/save_selected', methods=['POST'])
def save_selected():
    if 'user_id' not in session:
        return "User not logged in", 403  # Ensure user is logged in

    user_id = session['user_id']
    selected_doctors = request.form.getlist('selected_doctors')

    if not selected_doctors:
        return "No doctors selected", 400

    try:
        for doc_index in selected_doctors:
            name = request.form.get(f'name_{doc_index}')
            address = request.form.get(f'address_{doc_index}')
            rating = request.form.get(f'rating_{doc_index}')

            sql = "INSERT INTO selected_doctors (user_id, name, address, rating) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user_id, name, address, rating))

        db.commit()
        return "Doctors saved successfully", 200

    except MySQLdb.Error as e:
        db.rollback()
        return f"Error saving data: {str(e)}", 500



# Find doctors route
@app.route('/index2.html', methods=['GET'])
def find_doctors():
    city = request.args.get('city')
    specialty = request.args.get('specialty')
    api_key = "AIzaSyBSzQDWcv889gBErlt2QbjsNP-laF2aJ4E"  # Replace with your actual API key

    if not city or not specialty:
        return render_template('index2.html', error="City and Specialty are required", doctors=None)

    doctors = fetch_doctors(city, specialty, api_key)
    if doctors is None:
        return render_template('index2.html', error="Error fetching data from the Google API", doctors=None)

    return render_template('index2.html', city=city, specialty=specialty, doctors=doctors)



model = joblib.load("disease_prediction_model.pkl")
scaler = joblib.load("scaler.pkl")  # Ensure this is saved earlier
label_encoder = joblib.load("label_encoder.pkl")


# Define symptom list (ensure this matches dataset features)
symptom_list = ["weight loss", "jaundice", "allergic reactions", "frequent infections", "dark urine", "night sweats", "dry mouth", "joint pain", "memory problems", "prolonged bleeding", "excessive bleeding", "chest pain", "easy bruising", "extreme fatigue", "fatigue", "tongue inflammation", "numbness", "headaches", "dizziness", "weakness", "swollen lymph nodes", "dry skin", "swelling in legs", "pain episodes", "pale skin", "unexplained bruising", "shortness of breath", "swelling", "fever"]


@app.route("/prediction")
def prediction():
    return render_template("prediction.html", symptoms=symptom_list)

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        user_symptoms = data.get("symptoms", [])

        # Convert input to model format
        input_data = pd.DataFrame([[1 if symptom in user_symptoms else 0 for symptom in symptom_list]], columns=symptom_list)
        input_data = scaler.transform(input_data)

        # Predict disease
        prediction = model.predict(input_data)
        predicted_disease = label_encoder.inverse_transform(prediction)[0]

        return jsonify({"predicted_disease": predicted_disease})
    
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/feedback')
def homepage():
    """Render the home page."""
    return render_template('feedback.html')


if __name__ == '__main__':
    app.run(debug=True)
