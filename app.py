from flask import Flask, request, jsonify, redirect, url_for
import csv
import json   # <--- THIS IS THE FIX
import os
from datetime import datetime
import requests
import joblib
import pandas as pd

app = Flask(__name__)
DATA_FILE = "silo_data_log.csv"
SILO_LATITUDE = "7.3775"   
SILO_LONGITUDE = "3.9470"  

# Load your trained Climate AI model
climate_model = joblib.load('climate_predictor.joblib')

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Latitude", "Longitude", "Temp(C)", "Humidity(%)", "Gas(ppm)", "Image", "Command_Issued", "AI_Detection"])

@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/detect', methods=['POST'])
def detect():
    print("--- NEW DATA RECEIVED ---")
    image_file = request.files['image']
    image_name = image_file.filename
    sensor_data = request.form.get('sensor_data')
    temp, humidity, gas = 0, 0, 0
    if sensor_data:
        data = json.loads(sensor_data)
        temp = data.get('temp')
        humidity = data.get('humidity')
        gas = data.get('gas')

    # Fake AI for the cloud (since Render cannot run YOLO)
    ai_detection = "Cloud Mode: AI disabled"
    command = "IDLE"
    alert_message = "Grain conditions are safe."

    if float(humidity) > 14 and float(gas) > 400:
        command = "FUMIGATE"
        alert_message = "CRITICAL: High mold/pest risk."
    elif float(humidity) > 14 or float(gas) > 400:
        command = "VENT_OPEN"
        alert_message = "WARNING: High humidity/gas detected."
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, SILO_LATITUDE, SILO_LONGITUDE, temp, humidity, gas, image_name, command, ai_detection])
    
    return jsonify({"command": command, "alert": alert_message})

@app.route('/dashboard')
def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Smart Silo Dashboard</title>
    <style>
        body { font-family: Arial; background: #f4f7f6; padding: 20px; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th { background: #2c3e50; color: white; padding: 12px; }
        td { border: 1px solid #ddd; padding: 10px; text-align: center; }
        .fumigate { color: red; font-weight: bold; }
        .idle { color: green; font-weight: bold; }
        .vent_open { color: orange; font-weight: bold; }
    </style>
    </head>
    <body>
    <h1>🌾 Smart Silo Monitoring Dashboard</h1>
    <table>
        <tr><th>Timestamp</th><th>Lat</th><th>Long</th><th>Temp</th><th>Hum</th><th>Gas</th><th>Image</th><th>AI Detection</th><th>Command</th></tr>
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, mode='r') as file:
            reader = csv.reader(file)
            rows = list(reader)
            if len(rows) > 1:
                for row in rows[1:]:
                    if len(row) < 9: continue
                    command_text = row[7]
                    cls = "idle"
                    if command_text == "FUMIGATE": cls = "fumigate"
                    elif command_text == "VENT_OPEN": cls = "vent_open"
                    html_content += f"""
                    <tr>
                        <td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td>
                        <td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td>
                        <td>{row[6]}</td><td>{row[8]}</td>
                        <td class="{cls}">{command_text}</td>
                    </tr>
                    """
            else:
                html_content += "<tr><td colspan='9'>No data yet.</td></tr>"
    else:
        html_content += "<tr><td colspan='9'>CSV file not found.</td></tr>"
    html_content += "</table></body></html>"
    return html_content

@app.route('/forecast')
def forecast():
    # Get the current month
    current_month = datetime.now().month
    # For demo, let's test with 35°C and Year 2025
    test_data = pd.DataFrame({
        'Year': [2025],
        'Month': [current_month],
        'Max_Temp_C': [35.0]
    })
    prediction = climate_model.predict(test_data)[0]
    probability = climate_model.predict_proba(test_data)[0][1]
    risk = "HIGH RISK (Fumigate!)" if prediction == 1 else "SAFE"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Climate Forecast</title></head>
    <body style="font-family: Arial; padding: 20px;">
    <h1>🌦️ Nigerian Climate Risk Forecast</h1>
    <p><strong>State:</strong> Lagos (Demo)</p>
    <p><strong>Month:</strong> {current_month}</p>
    <p><strong>Temperature:</strong> 35°C</p>
    <p><strong>Predicted Risk:</strong> <span style="color:red;">{risk}</span></p>
    <p><strong>AI Confidence:</strong> {probability*100:.2f}%</p>
    <p><a href="/dashboard">Back to Silo Dashboard</a></p>
    </body>
    </html>
    """
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
