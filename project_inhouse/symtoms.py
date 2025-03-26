import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

def load_data(file_path):
    df = pd.read_csv(file_path)
    X = df.iloc[:, 1:30]  # Symptoms
    y = df.iloc[:, 0]  # Disease
    
    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    return X, y_encoded, label_encoder

def train_model(X, y):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    stratify_option = y if pd.Series(y).value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=stratify_option)
    
    model = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    print(f'Model Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%')
    
    return model, scaler

def predict_disease(model, scaler, label_encoder, user_symptoms, symptom_list):
    input_data = pd.DataFrame([[1 if symptom in user_symptoms else 0 for symptom in symptom_list]], columns=symptom_list)
    input_data_scaled = scaler.transform(input_data)
    
    prediction = model.predict(input_data_scaled)
    predicted_disease = label_encoder.inverse_transform([prediction[0]])[0]
    
    return predicted_disease

# Load and train the model
file_path = "Dataset.csv"
X, y, label_encoder = load_data(file_path)
model, scaler = train_model(X, y)

# Save the model, scaler, and label encoder
joblib.dump(model, "disease_prediction_model.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(label_encoder, "label_encoder.pkl")

# Example user input
user_symptoms = ['joint pain', 'headaches', 'dizziness']
predicted_disease = predict_disease(model, scaler, label_encoder, user_symptoms, X.columns.tolist())
print(f'Predicted Disease: {predicted_disease}')
