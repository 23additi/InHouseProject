
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

app = Flask(__name__) 
app.secret_key = "your_secret_key_here"  # Required for flash messages & sessions
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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




# Initialize SQLite Database (Run once)
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        full_name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                      )''')
    conn.commit()
    conn.close()

init_db()  # Ensure DB is set up

# Home (Register) Route
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)",
                           (full_name, email, hashed_password))
            conn.commit()
            conn.close()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))  # Redirect instead of render_template

        except sqlite3.IntegrityError:
            flash("Email already exists! Try another one.", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for('index'))  # Redirect to homepage
        else:
            flash("Invalid email or password. Try again!", "danger")

    return render_template('login.html')


# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Function to fetch doctors using Google Places API

def fetch_doctors(city, specialty, api_key):
    query = f"{specialty} in {city}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()  # Use .json() instead of .get_json()
        return [
            {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": place.get("rating", "N/A"),
            }
            for place in data.get("results", [])
        ]
    return None


# Home route
# @app.route('/register')
# def register():
#     return render_template('register.html')

# @app.route('/login')
# def login():
#     return render_template('login.html')


# @app.route('/')
# def register():
#     return render_template('register.html')

@app.route('/homepage')
def index():
    return render_template('index.html')

@app.route('/find_doctor')
def doctor():
    return render_template('index3.html')

@app.route('/diet')
def diet():
    return render_template('diet.html')



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
    

basic_prompt="I need it completely in html with styling.The data should be in white font color with quantity how much needs to be consumed should be written. Don't show any background color.There should be no suggestions and other information. Also don't include note or any extra information.The food nutrients should be displayed in a table format without background color and heading should be in white font color and bold in the left of the meal plan.The food nutrients should be in another table. Don't include tofu and provide diet according to age given. Provide one table only for all the days." 

# Directly set your API key here
my_api_key_gemini = "AIzaSyBWO2wo3W8jmaZ3ajUKAt8LOnYxxkldtso"  # Replace with your actual API key
genai.configure(api_key=my_api_key_gemini)



@app.route('/')
def index2():
    return render_template('index3.html')

@app.route('/calculate')
def cal():
    return render_template('result.html')

@app.route('/form')
def back():
    return render_template('diet.html')

def calculate_bmi(weight, height):
    # Calculate BMI
    height_m = height / 100  # Convert cm to meters
    bmi = weight / (height_m ** 2)
    return bmi

def generate_meal_plan(bmi, food_preference, region,age):
    # Create a prompt based on user data
    if bmi < 18.5:
        prompt = f"Create a weekly meal plan featuring high-calorie Indian dishes for a {food_preference} person of {age} from {region} who is underweight. Include breakfast, lunch, and dinner options.{basic_prompt}"
    elif 18.5 <= bmi < 24.9:
        prompt = f"Generate a balanced weekly meal plan featuring traditional Indian dishes for a {food_preference} person of {age} from {region} with a normal weight. Include healthy recipes for breakfast, lunch, and dinner.{basic_prompt}"
    elif 25 <= bmi < 29.9:
        prompt = f"Suggest a weekly meal plan for a {food_preference} person of {age} from {region} who is overweight. Include low-calorie Indian dishes for breakfast, lunch, and dinner.{basic_prompt}"
    else:
        prompt = f"Outline a weekly meal plan for a {food_preference} person of {age} from {region} who is obese. Include low-sugar and low-calorie Indian recipes for breakfast, lunch, and dinner.{basic_prompt}"

    # Call the Gemini API to generate the meal plan
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text.replace("```html","").replace("```","")

@app.route('/calculate', methods=['POST'])
def calculate():
    age = int(request.form['age'])
    weight = float(request.form['weight'])
    height = float(request.form['height'])
    food_preference = request.form['food_preference']
    region = request.form['region']
    activity_level = request.form['activity_level']

    bmi = calculate_bmi(weight, height)
    meal_plan= generate_meal_plan(bmi, food_preference, region,age)
    
    # Render the result template with BMI and meal plan
    return render_template('result.html', bmi=bmi, meal_plan=meal_plan)

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

def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diet_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Ensure DB is set up on startup

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

@app.route('/download_diet_pdf/<filename>')
def download_diet_pdf(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/diet_reports')
def diet_reports():
    """Fetch and display saved diet reports from the database."""
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, upload_time FROM diet_reports ORDER BY upload_time DESC")
    reports = cursor.fetchall()
    conn.close()
    return jsonify({"success": True, "reports": reports})

if __name__ == '__main__':
    app.run(debug=True)

