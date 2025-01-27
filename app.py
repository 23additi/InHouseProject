from flask import Flask, render_template,request,redirect, url_for
import requests
import logging
import sqlite3
import google.generativeai as genai
import os

app = Flask(__name__)

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

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/')
def register():
    return render_template('register.html')

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
    

basic_prompt="I need it completely in html with styling.The data should be in white font color with quantity how much needs to be consumed should be written. Don't show any background color.There should be no suggestions and other information. Also don't include note or any extra information.The food nutrients should be displayed in a table format without background color and heading should be in white font color and bold in the left of the meal plan.The food nutrients should be in another table." 

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

def generate_meal_plan(bmi, food_preference, region):
    # Create a prompt based on user data
    if bmi < 18.5:
        prompt = f"Create a weekly meal plan featuring high-calorie Indian dishes for a {food_preference} person from {region} who is underweight. Include breakfast, lunch, and dinner options.{basic_prompt}"
    elif 18.5 <= bmi < 24.9:
        prompt = f"Generate a balanced weekly meal plan featuring traditional Indian dishes for a {food_preference} person from {region} with a normal weight. Include healthy recipes for breakfast, lunch, and dinner.{basic_prompt}"
    elif 25 <= bmi < 29.9:
        prompt = f"Suggest a weekly meal plan for a {food_preference} person from {region} who is overweight. Include low-calorie Indian dishes for breakfast, lunch, and dinner.{basic_prompt}"
    else:
        prompt = f"Outline a weekly meal plan for a {food_preference} person from {region} who is obese. Include low-sugar and low-calorie Indian recipes for breakfast, lunch, and dinner.{basic_prompt}"

    # Call the Gemini API to generate the meal plan
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text.replace("```html","").replace("```","")

@app.route('/calculate', methods=['POST'])
def calculate():
    weight = float(request.form['weight'])
    height = float(request.form['height'])
    food_preference = request.form['food_preference']
    region = request.form['region']
    activity_level = request.form['activity_level']

    bmi = calculate_bmi(weight, height)
    meal_plan= generate_meal_plan(bmi, food_preference, region)
    
    # Render the result template with BMI and meal plan
    return render_template('result.html', bmi=bmi, meal_plan=meal_plan)


if __name__ == '__main__':
    app.run(debug=True)

