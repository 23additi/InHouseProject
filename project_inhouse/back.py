from flask import Flask, render_template,request,redirect, url_for,session,flash, jsonify, send_file
from flask import send_from_directory
import requests,os
import logging
import sqlite3
import google.generativeai as genai
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter, portrait
# from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB



#Registeration,Login and Profile

app.secret_key = "your_secret_key"  # Change this to a secure key


# Initialize Database
def init_db():
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS registration (
                        user_id TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        dob TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile (
                        user_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        gender TEXT NOT NULL,
                        height REAL,
                        weight REAL,
                        city TEXT,
                        state TEXT,
                        FOREIGN KEY(user_id) REFERENCES registration(user_id)
                      )''')
    conn.commit()
    conn.close()



init_db()  # Ensure DB is set up

# Function to generate user_id from full_name and dob
def generate_user_id(full_name, dob):
    name_part = full_name[:4].upper()
    dob_part = dob.replace('-', '')  # Remove dashes from YYYY-MM-DD
    return f"{name_part}{dob_part}"

def calculate_age(dob):
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def authenticate_user(email, password):
    """Verify user credentials."""
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM registration WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

# Home (Register) Route
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        dob = request.form['dob']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user_id = generate_user_id(full_name, dob)

        try:
            conn = sqlite3.connect('health.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO registration (user_id, full_name, dob, email, password) VALUES (?, ?, ?, ?, ?)",
                           (user_id, full_name, dob, email, hashed_password))
            conn.commit()
            conn.close()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists! Try another one.", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('health.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM registration WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]  # Store user_id in session
            return redirect(url_for('profile'))  # Redirect to profile page
        else:
            return "Invalid credentials. Try again."  # Change this to render a login page with an error message
        
        return render_template('login.html')


# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))



@app.route('/homepage', methods=['GET', 'POST'])
def homepage():
    return render_template('index.html')  # Ensure index.html exists


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if not logged in

    user_id = session['user_id']
    
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, dob, email FROM registration WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        age = calculate_age(user[0])
    else:
        age = None
    
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        height = request.form.get('height')
        weight = request.form.get('weight')
        city = request.form.get('city')
        state = request.form.get('state')

        if not (name and gender):
            flash("Please fill all required fields!", "danger")
            return redirect(url_for('profile'))

        try:
            conn = sqlite3.connect('health.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO profile (user_id, name, age, gender, height, weight, city, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (user_id, name, age, gender, height, weight, city, state))
            conn.commit()
            conn.close()
            flash("Profile created successfully!", "success")
            return redirect(url_for('homepage'))
        except sqlite3.IntegrityError:
            flash("Profile already exists!", "danger")
            return redirect(url_for('profile'))

    return render_template('profile.html', age=age)






#EHR
app.secret_key = "your_secret_key_here"  # Required for flash messages & sessions
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ensure diet_records directory exists
if not os.path.exists("static/diet_records"):
    os.makedirs("static/diet_records")


# # Database Initialization
def init_db():
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/ehr')
def ehr():
    return render_template('ehr.html')


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

        # Save file info to database
        conn = sqlite3.connect("health.db")
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO reports (filename, upload_time) VALUES (?, ?)", (filename, datetime.now()))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "File uploaded successfully"})
        except sqlite3.Error as e:
            conn.close()
            return jsonify({"success": False, "message": f"Database error: {str(e)}"})


@app.route('/uploads')
def uploaded_files():
    conn = sqlite3.connect('health.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, upload_time FROM reports")
    files = c.fetchall()
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


def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile (
                        user_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        dob TEXT NOT NULL,
                        gender TEXT NOT NULL,
                        height REAL,
                        weight REAL,
                        city TEXT,
                        state TEXT,
                        FOREIGN KEY(user_id) REFERENCES registration(user_id)
                      )''')
    conn.commit()
    conn.close()

init_db()  # Ensure DB is set up on startup

@app.route('/diet')
def diet():
    return render_template('diet.html')

@app.route('/calculate')
def cal():
    return render_template('result.html')

@app.route('/form')
def back():
    return render_template('diet.html')


def generate_user_id(full_name, dob):
    name_part = full_name[:4].upper()  # First 4 letters of name in uppercase
    dob_part = dob.replace('-', '')  # Remove hyphens from DOB
    return f"{name_part}{dob_part}"  # Concatenate to form user_id

def calculate_age(dob):
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def fetch_user_profile(user_id):
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    
    # Only fetch columns that exist in the 'profile' table
    cursor.execute("SELECT dob, height, weight, state FROM profile WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    
    conn.close()
    if profile:
        dob, height, weight, state = profile
        age = calculate_age(dob)
        return age, height, weight, state  # Only returning valid columns
    return None


def calculate_bmi(weight, height):
    return weight / ((height / 100) ** 2)


# @app.route('/diet_plan/<user_id>', methods=['GET'])
# def get_diet_plan(user_id):
#     profile_data = fetch_user_profile(user_id)
#     if not profile_data:
#         return jsonify({"error": "User profile not found"}), 404
    
#     age, height, weight, state, food_preference, activity_level = profile_data
#     bmi = weight / ((height / 100) ** 2)
    
#     # Generate meal plan with additional preferences
#     meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)
    
#     return jsonify({"bmi": bmi, "meal_plan": meal_plan})

def generate_meal_plan(bmi, state, age, food_preference, activity_level):
    if bmi < 18.5:
        return f"High-calorie {food_preference} diet suitable for an underweight individual from {state}, age {age}, with {activity_level} activity level."
    elif 18.5 <= bmi < 24.9:
        return f"Balanced {food_preference} diet suitable for a healthy individual from {state}, age {age}, with {activity_level} activity level."
    elif 25 <= bmi < 29.9:
        return f"Low-calorie {food_preference} diet suitable for an overweight individual from {state}, age {age}, with {activity_level} activity level."
    else:
        return f"Low-sugar, low-calorie {food_preference} diet suitable for an obese individual from {state}, age {age}, with {activity_level} activity level."

@app.route('/diet_plan/<user_id>', methods=['GET'])
def get_diet_plan(user_id):
    profile_data = fetch_user_profile(user_id)
    if not profile_data:
        return jsonify({"error": "User profile not found"}), 404
    
    age, height, weight, state, food_preference, activity_level = profile_data
    bmi = calculate_bmi(weight, height)
    
    meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)
    
    return render_template('result.html', bmi=bmi, meal_plan=meal_plan)

@app.route('/calculate', methods=['POST'])
def calculate():
    user_id = request.form.get('user_id')
    food_preference = request.form.get('food_preference')  # Taken from diet.html form
    activity_level = request.form.get('activity_level')  # Taken from diet.html form
    
    profile_data = fetch_user_profile(user_id)
    if not profile_data:
        return jsonify({"error": "User profile not found"}), 404
    
    age, height, weight, state, _, _ = profile_data  # Ignoring food_preference and activity_level from DB
    bmi = calculate_bmi(weight, height)
    meal_plan = generate_meal_plan(bmi, state, age, food_preference, activity_level)

    return render_template('result.html', bmi=bmi, meal_plan=meal_plan)


@app.route('/download_diet_pdf/<user_id>', methods=['GET'])
def download_diet_pdf(user_id):
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    cursor.execute("SELECT diet_pdf FROM diet_recommendations WHERE user_id = ?", (user_id,))
    record = cursor.fetchone()
    conn.close()
    
    if record and record[0]:
        return send_file(record[0], as_attachment=True)
    else:
        return jsonify({"error": "No diet plan found for this user."}), 404


# @app.route('/calculate', methods=['POST'])
# def calculate():

#     food_preference = request.form['food_preference']
#     activity_level = request.form['activity_level']

#     bmi = calculate_bmi(weight, height)
#     meal_plan= generate_meal_plan(bmi, food_preference, state,age)
    
#     # Render the result template with BMI and meal plan
#     return render_template('result.html', bmi=bmi, meal_plan=meal_plan)

def insert_data(weight, height, food_preference, state, activity_level, diet_pdf):
    conn = sqlite3.connect('health_management.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO diet_recommendations (weight, height, food_preference, state, activity_level, diet_pdf)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (weight, height, food_preference, state, activity_level, diet_pdf))
    conn.commit()
    conn.close()

# Function to extract table data from HTML using BeautifulSoup
def extract_table_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    table_data = []

    for row in soup.find_all("tr"):
        cells = [Paragraph("\n".join(cell.get_text(" ", strip=True).split(", ")), getSampleStyleSheet()["BodyText"]) for cell in row.find_all(["th", "td"])]
        if cells:
            table_data.append(cells)

    return table_data

@app.route('/generate_diet_pdf', methods=['POST'])
def generate_diet_pdf():
    meal_plan_html = request.form.get('meal_plan')
    bmi = request.form.get('bmi')

    if not meal_plan_html:
        return jsonify({"success": False, "message": "No meal plan provided"})

    filename = f"diet_plan_{int(datetime.now().timestamp())}.pdf"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Extract structured table data from meal plan HTML
    meal_plan_table = extract_table_from_html(meal_plan_html)

    # Ensure valid table data
    if not meal_plan_table or len(meal_plan_table) < 2:
        return jsonify({"success": False, "message": "Invalid table format in meal plan"})

    # Create a PDF with ReportLab (Portrait Mode for better readability)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=portrait(letter),
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch
    )
    
    elements = []
    styles = getSampleStyleSheet()

    # Add Title
    elements.append(Paragraph("<b>Your Diet Plan</b>", styles["Title"]))
    elements.append(Paragraph(f"<b>BMI:</b> {bmi}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # **Adjust Column Widths (Better Text Wrapping)**
    col_widths = [2.5 * inch, 2.5 * inch, 2.5 * inch]  # Adjusted for better spacing

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for day in days:
        day_data = [["Breakfast", "Lunch", "Dinner"]]  # Table headers
        for row in meal_plan_table[1:]:
            if day in row[0].getPlainText():  # Check if row belongs to this day
                day_data.append([
                    Paragraph(row[1].getPlainText(), styles["BodyText"]),
                    Paragraph(row[2].getPlainText(), styles["BodyText"]),
                    Paragraph(row[3].getPlainText(), styles["BodyText"])
                ])

        if len(day_data) > 1:
            elements.append(Paragraph(f"<b>{day}</b>", styles["Heading2"]))  # Add Day Heading
            day_table = Table(day_data, colWidths=col_widths, repeatRows=1)
            day_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),  
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Adjusted padding for better visibility
                ('TOPPADDING', (0, 0), (-1, -1), 8),  
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  
                ('LEFTPADDING', (0, 0), (-1, -1), 10),  
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),  
            ]))
            elements.append(day_table)
            elements.append(Spacer(1, 12))  # Space after each table

    # Build the PDF
    doc.build(elements)

    # Store PDF info in the database
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO diet_reports (filename, upload_time) VALUES (?, ?)", (filename, datetime.now()))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "filename": filename})

# @app.route('/download_diet_pdf/<filename>')
# def download_diet_pdf(filename):
#     return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/diet_reports')
def diet_reports():
    """Fetch and display saved diet reports from the database."""
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, upload_time FROM diet_reports ORDER BY upload_time DESC")
    reports = cursor.fetchall()
    conn.close()
    return jsonify({"success": True, "reports": reports})




# basic_prompt="I need it completely in html with styling.The data should be in white font color with quantity how much needs to be consumed should be written. Don't show any background color.There should be no suggestions and other information. Also don't include note or any extra information.The food nutrients should be displayed in a table format without background color and heading should be in white font color and bold in the left of the meal plan.The food nutrients should be in another table. Don't include tofu and provide diet according to age given. Provide one table only for all the days." 

# # Directly set your API key here
# my_api_key_gemini = "AIzaSyBWO2wo3W8jmaZ3ajUKAt8LOnYxxkldtso"  # Replace with your actual API key
# genai.configure(api_key=my_api_key_gemini)






#Find Doctors
@app.route('/')
def index2():
    return render_template('index2.html')

@app.route('/find_doctor')
def doctor():
    return render_template('index2.html')


def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS selected_doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT,
            address TEXT,
            rating REAL
             )
   ''')
    conn.commit()
    conn.close()

init_db()  # Ensure DB is set up on startup


# Function to fetch doctors using Google Places API

def fetch_doctors(city, specialty, api_key):
    query = f"{specialty} in {city}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()  # Use .json() instead of .get_json()

        doctors = [
            {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": float(place.get("rating", 0)),  # Ensure rating is a float
            }
            for place in data.get("results", [])
        ]

        # Sort doctors by rating in descending order
        doctors = sorted(doctors, key=lambda x: x["rating"], reverse=True)

        return doctors

    return None


@app.route('/save_selected', methods=['POST'])
def save_selected():
    selected_ids = request.form.getlist('selected_doctors')  # Get selected doctor IDs

    if not selected_ids:
        return redirect(url_for('find_doctors'))

    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()

    for doctor_id in selected_ids:
        name = request.form.get(f"name_{doctor_id}")
        address = request.form.get(f"address_{doctor_id}")
        rating = request.form.get(f"rating_{doctor_id}")

        # Insert into selected_doctors table
        cursor.execute(''' 
            INSERT INTO selected_doctors (name, address, rating)
            VALUES (?, ?, ?)
        ''', (name, address, rating))

    conn.commit()
    conn.close()

    return redirect(url_for('homepage'))  # Redirect to homepage


# Find doctors route
@app.route('/index2.html', methods=['GET'])
def find_doctors():
    city = request.args.get('city')
    specialty = request.args.get('specialty')
    api_key = "AIzaSyBSzQDWcv889gBErlt2QbjsNP-laF2aJ4E"  # Replace with your Google API key

    if not city or not specialty:
        return render_template('index2.html', error="City and Specialty are required", doctors=None)

    # Fetch doctors
    doctors = fetch_doctors(city, specialty, api_key)
    if doctors is None:
        return render_template('index2.html', error="Error fetching data from the Google API", doctors=None)

    return render_template('index2.html', city=city, specialty=specialty, doctors=doctors)




# # @app.route('/save_selected', methods=['POST'])
# # def save_selected():
# #     selected_ids = request.form.getlist('selected_doctors')  # Get selected doctor IDs

# #     if not selected_ids:
# #         return redirect(url_for('find_doctors'))

# #     conn = sqlite3.connect('health_management.db')
# #     cursor = conn.cursor()

# #     for doctor_id in selected_ids:
# #         name = request.form.get(f"name_{doctor_id}")
# #         address = request.form.get(f"address_{doctor_id}")
# #         rating = request.form.get(f"rating_{doctor_id}")

# #         # Insert into selected_doctors table
# #         cursor.execute(''' 
# #             INSERT INTO selected_doctors (name, address, rating)
# #             VALUES (?, ?, ?)
# #         ''', (name, address, rating))

# #     conn.commit()
# #     conn.close()

# #     return redirect(url_for('index'))  # Redirect to homepage after saving




#Feedback
@app.route("/feedback")
def feedback_form():
    """
    Render the feedback form (feedback.html).
    """
    return render_template("feedback.html")

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    """
    Handle feedback form submissions.
    Save ratings and feedback to the SQLite database.
    """
    return render_template("index.html")

    try:
        # Extract form data
        ehr_rating = request.form['ehr_rating']
        disease_rating = request.form['disease_rating']
        diet_rating = request.form['diet_rating']
        doctor_rating = request.form['doctor_rating']
        overall_feedback = request.form['overall_feedback']

        #Save feedback to database
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (ehr_rating, disease_rating, diet_rating, doctor_rating, overall_feedback)
            VALUES (?, ?, ?, ?, ?)
        ''', (ehr_rating, disease_rating, diet_rating, doctor_rating, overall_feedback))
        conn.commit()
        conn.close()

        logging.info("Feedback submitted successfully.")
        return redirect(url_for("home"))

    except Exception as e:
        logging.error(f"Error saving feedback: {e}")
        return "An error occurred while submitting your feedback. Please try again later.", 500






# def extract_table_from_html(html_content):
#     """Extract structured table data from HTML using BeautifulSoup."""
#     soup = BeautifulSoup(html_content, "html.parser")
#     table_data = []

#     for row in soup.find_all("tr"):
#         cells = [Paragraph("\n".join(cell.get_text(" ", strip=True).split(", ")), getSampleStyleSheet()["BodyText"]) for cell in row.find_all(["th", "td"])]
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

#     # Extract structured table data from meal plan HTML
#     meal_plan_table = extract_table_from_html(meal_plan_html)

#     # Ensure valid table data
#     if not meal_plan_table or len(meal_plan_table) < 2:
#         return jsonify({"success": False, "message": "Invalid table format in meal plan"})

#     # Create a PDF with ReportLab (LANDSCAPE MODE)
#     doc = SimpleDocTemplate(
#         filepath,
#         pagesize=portrait(letter),
#         leftMargin=0.7 * inch,
#         rightMargin=0.7 * inch,
#         topMargin=0.7 * inch,
#         bottomMargin=0.7 * inch
#     )
    
#     elements = []
#     styles = getSampleStyleSheet()

#     # Add Title
#     elements.append(Paragraph("<b>Your Diet Plan</b>", styles["Title"]))
#     elements.append(Paragraph(f"<b>BMI:</b> {bmi}", styles["Normal"]))
#     elements.append(Spacer(1, 12))

#     # **Adjust Column Widths (Better Text Wrapping)**
#     col_widths = [1 * inch, 1 * inch, 1 * inch]  # All columns equal width

#     days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
#     for day in days:
#         day_data = [["Breakfast", "Lunch", "Dinner"]]  # Table headers
#         for row in meal_plan_table[1:]:
#             if day in row[0].getPlainText():  # Check if row belongs to this day
#                 day_data.append([Paragraph(row[1].getPlainText(), styles["BodyText"]), 
#                                  Paragraph(row[2].getPlainText(), styles["BodyText"]), 
#                                  Paragraph(row[3].getPlainText(), styles["BodyText"])])

#         if len(day_data) > 1:
#             elements.append(Paragraph(f"<b>{day}</b>", styles["Heading2"]))  # Add Day Heading
#             day_table = Table(day_data, colWidths=col_widths, repeatRows=1)
#             day_table.setStyle(TableStyle([
#                 ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),  
#                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  
#                 ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
#                 ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
#                 ('BOTTOMPADDING', (0, 0), (-1, 0), 16),  # Increased padding
#                 ('TOPPADDING', (0, 0), (-1, -1), 10),  # Added extra spacing for rows
#                 ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  
#                 ('GRID', (0, 0), (-1, -1), 1, colors.black),  
#                 ('VALIGN', (0, 0), (-1, -1), 'TOP'),  
#                 ('LEFTPADDING', (0, 0), (-1, -1), 15),  
#                 ('RIGHTPADDING', (0, 0), (-1, -1), 15),  
#             ]))
#             elements.append(day_table)
#             elements.append(Spacer(1, 12))  # Space after each table

#     # Build the PDF
#     doc.build(elements)

#     return jsonify({"success": True, "filename": filename})

# @app.route('/download_diet_pdf/<filename>')
# def download_diet_pdf(filename):
#     return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)




# # Create database table
# def create_database():
#     conn = sqlite3.connect('health_management.db')
#     cursor = conn.cursor()

#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS diet_recommendations 
#             (
#             id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#             weight REAL,
#             height REAL,
#             food_preference TEXT,
#             region TEXT,
#             activity_level TEXT,
#             diet_pdf TEXT
#             )
#     ''')

#     
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS reports (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             filename TEXT NOT NULL,
#             upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     ''') 

#     conn.commit()
#     conn.close()

# create_database()


# # Home route
# # @app.route('/register')
# # def register():
# #     return render_template('register.html')

# @app.route('/login')
# def login():
#     return render_template('login.html')


# @app.route('/')
# def register():
#     return render_template('register.html')

# @app.route('/homepage')
# def index():
#     return render_template('index.html')

# @app.route('/prediction')
# def prediction():
#     return render_template('prediction.html')

# @app.route('/find_doctor')
# def doctor():
#     return render_template('index3.html')

# @app.route('/diet')
# def diet():
#     return render_template('diet.html')

# # @app.route('/form')
# # def index():
# #     return render_template('index.html')

# @app.route('/')
# def index2():
#     return render_template('index3.html')

# Home (Register) Route


if __name__ == '__main__':
    app.run(debug=True)

