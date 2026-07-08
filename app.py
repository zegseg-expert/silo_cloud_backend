from flask import Flask, request, jsonify, redirect, url_for
import csv
import os
from datetime import datetime
import requests

app = Flask(__name__)
DATA_FILE = "silo_data_log.csv"
SILO_LATITUDE = "7.3775"   
SILO_LONGITUDE = "3.9470"  

# =========================================================
# YOUR NEW HUGGING FACE TOKEN
# =========================================================
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Create CSV headers if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Latitude", "Longitude", "Temp(C)", "Humidity(%)", "Gas(ppm)", "Image", "Command_Issued", "AI_Detection"])

# =========================================================
# HOMEPAGE REDIRECT (Fixes the 404 error)
# =========================================================
@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/detect', methods=['POST'])
def detect():
    print("--- NEW DATA RECEIVED ---")
    image_file = request.files['image']
    image_name = image_file.filename
    print(f"Image: {image_name}")

    sensor_data = request.form.get('sensor_data')
    temp, humidity, gas = 0, 0, 0
    if sensor_data:
        data = json.loads(sensor_data)
        temp = data.get('temp')
        humidity = data.get('humidity')
        gas = data.get('gas')

    # =========================================================
    # THE LOW-MEMORY CLOUD AI (Sends image to Hugging Face)
    # =========================================================
    ai_detection = "None"
    try:
        img_bytes = image_file.read()
        api_url = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(api_url, headers=headers, data=img_bytes)
        
        if response.status_code == 200:
            result = response.json()
            if len(result) > 0:
                best = max(result, key=lambda x: x['score'])
                label = best['label']
                confidence = best['score'] * 100
                ai_detection = f"Detected {label} ({confidence:.1f}% confidence)"
                print(f"🤖 CLOUD AI sees: {ai_detection}")
        else:
            print(f"⚠️ HF API Error: {response.status_code}")
            ai_detection = "Cloud AI Error"
    except Exception as e:
        print(f"❌ Cloud AI Error: {e}")

    # DECISION ENGINE
    command = "IDLE"
    alert_message = "Grain conditions are safe."

    if ai_detection != "None" and "Error" not in ai_detection:
        command = "FUMIGATE"
        alert_message = f"🚨 {ai_detection}! Sealing silo!"
    elif float(humidity) > 14 and float(gas) > 400:
        command = "FUMIGATE"
        alert_message = "CRITICAL: High mold/pest risk."
    elif float(humidity) > 14 or float(gas) > 400:
        command = "VENT_OPEN"
        alert_message = "WARNING: High humidity/gas detected."
    
    # SAVE TO CSV
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, SILO_LATITUDE, SILO_LONGITUDE, temp, humidity, gas, image_name, command, ai_detection])
    
    return jsonify({"command": command, "alert": alert_message, "ai_detected": ai_detection})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
