from flask import Flask, render_template, jsonify
import pandas as pd
import schedule
import time
import threading
import os
import requests
from datetime import datetime


# --------------------
# --- Data Storage ---
# --------------------

# Directory to store the fetched XLSX files
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# These global variables will hold your processed data
processed_incident_data = []
incident_chart_data = {'labels': [], 'values': []}

def get_latest_excel_file_path():
    """
    Identifies the most recently modified .xlsx file in the DATA_DIR.
    """
    excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
    if not excel_files:
        return None

    # Sort files by modification time (most recent first)
    excel_files.sort(key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)), reverse=True)
    return os.path.join(DATA_DIR, excel_files[0])


# -----------------------
# --- Data Processing ---
# -----------------------

def get_path(source):
    if not source:
        return 'Other'

    # Define Man Check East prefixes
    man_check_east_prefixes = [
        'U161260', 'U162250', 'U163250',
        'U4083', 'U4020'
    ]

    # Define Man Check West prefixes
    man_check_west_prefixes = [
        'U153280', 'U152280', 'U151280',
        'U4082', 'U4021'
    ]

    # Check Man Check East
    if any(source.startswith(prefix) for prefix in man_check_east_prefixes):
        return 'Man Check East'

    # Check Man Check West
    if any(source.startswith(prefix) for prefix in man_check_west_prefixes):
        return 'Man Check West'

    import re
    match = re.match(r'U(\d{6})', source, re.IGNORECASE)
    digits = match.group(1) if match else None
    if not digits:
        return 'Other'

    # PID specific logic
    if digits.startswith('1632'): return 'PID 6 Man Check'
    if digits.startswith('1631'): return 'PID 6 Sort'
    if digits.startswith('1630'): return 'PID 6 Main'

    if digits.startswith('1622'): return 'PID 5 Man Check'
    if digits.startswith('1621'): return 'PID 5 Sort'
    if digits.startswith('1620'): return 'PID 5 Main'

    if digits.startswith('1612'): return 'PID 4 Man Check'
    if digits.startswith('1611'): return 'PID 4 Sort'
    if digits.startswith('1610'): return 'PID 4 Main'

    if digits.startswith('1532'): return 'PID 3 Man Check'
    if digits.startswith('1531'): return 'PID 3 Sort'
    if digits.startswith('1530'): return 'PID 3 Main'

    if digits.startswith('1522'): return 'PID 2 Man Check'
    if digits.startswith('1521'): return 'PID 2 Sort'
    if digits.startswith('1520'): return 'PID 2 Main'

    if digits.startswith('1512'): return 'PID 1 Man Check'
    if digits.startswith('1511'): return 'PID 1 Sort'
    if digits.startswith('1510'): return 'PID 1 Main'

    if digits.startswith('4050'): return 'NPC Line'
    if digits.startswith('4051'): return 'NPC Stations'
    if digits.startswith('4081'): return 'NPC Trash Line'

    return 'Other'

def process_dataframe(df):
    global processed_incident_data, incident_chart_data

    parsed_data = []
    for _, row in df.iterrows():
        source = str(row.get('Source', '')).strip()
        raw_message = str(row.get('message', '')).strip()
        incidents = int(row.get('Incidents', 0))
        downtime = float(row.get('Downtime_Hours', 0))
        path = get_path(source)

        msg_upper = raw_message.upper()
        message = "Other" # Default value

        # Logic for mapping raw messages to categorized messages
        if "DETECTED" in msg_upper or "RESTART" in msg_upper:
            message = "Jammed"
        elif "VOLTAGE" in msg_upper or "CURRENT" in msg_upper or "NODE" in msg_upper or "MANUAL" in msg_upper:
            message = "Mechanical Error"
        elif "FAULT" in msg_upper or "ERROR" in msg_upper or "BLOCKED" in msg_upper or "WAITING" in msg_upper:
            message = "Full"
        elif "E-STOP" in msg_upper:
            message = "E-stop"
        elif len(raw_message) > 0: # If there's a message but it doesn't match known patterns
            message = raw_message

        parsed_data.append({
            'source': source,
            'message': message,
            'incidents': incidents,
            'downtime': downtime,
            'path': path
        })

    # Prepare data for the chart based on incidents by message
    error_map = {}
    for row in parsed_data:
        key = row['message'].lower()
        error_map[key] = error_map.get(key, 0) + row['incidents']

    incident_chart_data['labels'] = list(error_map.keys())
    incident_chart_data['values'] = list(error_map.values())
    processed_incident_data = parsed_data # Update the global processed data

    print("Data processed successfully.")


# ----------------------
# --- Data Retrieval ---
# ----------------------

# TODO: change the URL from which to fetch the XLSX file (this has to be provided by Amazon)
EXTERNAL_EXCEL_URL = 'http://your-external-data-source.com/your_data.xlsx'

# --- Scheduled Task: Fetch, Store, and Process Excel ---
# TODO: adjust this if necessary to authenticate with Amazon to get the excel file
# As of now, it is set up to use REST API (the most common one) to fetch the file via GET Request.
def fetch_store_and_process_excel():
    print(f"Attempting to fetch Excel file from {EXTERNAL_EXCEL_URL}...")
    try:
        response = requests.get(EXTERNAL_EXCEL_URL)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Generate a timestamped filename to store the new file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conveyor_data_{timestamp}.xlsx"
        filepath = os.path.join(DATA_DIR, filename)

        # Save the fetched content to the data directory
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Successfully fetched and saved new Excel file to {filepath}")

        # Now, process the latest file in the data directory
        load_and_process_latest_excel()

    except requests.exceptions.RequestException as req_err:
        print(f"Network or request error fetching Excel file from URL: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred during fetch, store, or process: {e}")

def load_and_process_latest_excel():
    """
    Loads and processes the latest XLSX file found in the data directory.
    """
    latest_file_path = get_latest_excel_file_path()
    if latest_file_path:
        print(f"Loading data from latest Excel file: {latest_file_path}")
        try:
            df = pd.read_excel(latest_file_path)
            process_dataframe(df)
        except Exception as e:
            print(f"Error processing {latest_file_path}: {e}")
    else:
        print(f"No Excel files found in '{DATA_DIR}'. Cannot process data.")


# Function to run schedule in a separate thread
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60) # Check schedule every minute


# --- Flask Routes ---

app = Flask(__name__)

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """Returns the processed incident data and chart data as JSON."""
    return jsonify({
        'chartData': incident_chart_data,
        'tableData': processed_incident_data
    })


# -------------------------------
# --- Application Entry Point ---
# -------------------------------

if __name__ == '__main__':
    # 1. On startup, try to fetch the latest data from the URL
    #    This also saves it and processes it.
    fetch_store_and_process_excel()

    # 2. If the initial fetch failed (e.g., network issue),
    #    try to load and process any existing file from the data directory
    if not processed_incident_data: # If no data was processed from the initial fetch
        print("Initial fetch failed or no data. Attempting to load from existing files...")
        load_and_process_latest_excel()


    # Schedule the task to run daily at midnight
    schedule.every().second.do(fetch_store_and_process_excel)

    # Start the scheduler in a separate daemon thread
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Run the Flask app
    app.run(debug=True)
