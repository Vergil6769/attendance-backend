from flask_cors import CORS
from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime
import os
import gspread
from google.oauth2.service_account import Credentials
import json
import uuid
import time

from utils.face_utils import verify_face, reset_face_verification, is_face_verified

app = Flask(__name__)
CORS(app)

# -------------------------
# FILES
# -------------------------
students_file = "data/students.xlsx"
teachers_file = "data/teachers.xlsx"

SESSION = {}
QR_TOKEN = None
QR_EXPIRY = None

# -------------------------
# GOOGLE SHEETS
# -------------------------
SHEET_ID = "1MDQUccq8OXRAArfcjVuKI_GJH0GEQNr-jabAvlMcRws"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

service_key = json.loads(os.environ["GOOGLE_SERVICE_KEY"])

creds = Credentials.from_service_account_info(service_key, scopes=SCOPES)

gc = gspread.authorize(creds)

sheet = gc.open_by_key(SHEET_ID).sheet1


# -------------------------
# TEACHER LOGIN
# -------------------------
@app.route("/teacher_login", methods=["POST"])
def teacher_login():

    data = request.json

    username = str(data.get("username"))
    password = str(data.get("password"))

    df = pd.read_excel(teachers_file)

    df["username"] = df["username"].astype(str)
    df["password"] = df["password"].astype(str)

    user = df[(df["username"] == username) & (df["password"] == password)]

    if not user.empty:

        SESSION["teacher"] = username

        return jsonify({"status": "success"})

    return jsonify({"status": "invalid"})


# -------------------------
# START SESSION
# -------------------------
@app.route("/start_session", methods=["POST"])
def start_session():

    data = request.json

    division = data["division"]
    lecture = int(data["lecture"])
    teacher = data["teacher"]

    timetable_file = f"data/timetable{division}.xlsx"

    if not os.path.exists(timetable_file):
        return jsonify({"status": "timetable_missing"})

    timetable = pd.read_excel(timetable_file)

    today = datetime.now().strftime("%A")

    lec = timetable[(timetable["Day"] == today) & (timetable["Lecture"] == lecture)]

    if lec.empty:
        return jsonify({"status": "no_lecture_today"})

    subject = lec.iloc[0]["Subject"]

    session_id = str(datetime.now().timestamp())

    SESSION.update({
        "session": session_id,
        "division": division,
        "lecture": lecture,
        "subject": subject,
        "teacher": teacher
    })

    return jsonify({
        "status": "session_started",
        "subject": subject,
        "session": session_id
    })


# -------------------------
# STOP SESSION
# -------------------------
@app.route("/stop_session", methods=["POST"])
def stop_session():

    SESSION.clear()

    return jsonify({"status": "stopped"})


# -------------------------
# STUDENT LOGIN
# -------------------------
@app.route("/student_login", methods=["POST"])
def student_login():

    data = request.json

    username = str(data.get("username")).strip()
    password = str(data.get("password")).strip()

    df = pd.read_excel(students_file, dtype=str)

    df["Username"] = df["Username"].str.strip()
    df["Password"] = df["Password"].str.strip()

    user = df[(df["Username"] == username) & (df["Password"] == password)]

    if user.empty:
        return jsonify({"status": "fail"})

    student = user.iloc[0]

    return jsonify({
        "status": "success",
        "name": student["Name"],
        "roll": student["Roll"],
        "division": student["Division"]
    })


# -------------------------
# GENERATE QR
# -------------------------
@app.route("/generate_qr")
def generate_qr():

    global QR_TOKEN, QR_EXPIRY

    session_id = SESSION.get("session")

    if not session_id:
        return jsonify({"error": "session_not_started"}), 400

    QR_TOKEN = str(uuid.uuid4())

    QR_EXPIRY = time.time() + 5

    return jsonify({
        "token": QR_TOKEN,
        "expiry": QR_EXPIRY,
        "session": session_id
    })


# -------------------------
# FACE VERIFY
# -------------------------
@app.route("/verify_face", methods=["POST"])
def api_verify_face():

    data = request.json

    username = data.get("username")
    encoding = data.get("encoding")

    match = verify_face(username, encoding)

    return jsonify({"match": match})


# -------------------------
# RESET FACE VERIFY
# -------------------------
@app.route("/reset_face_verification", methods=["POST"])
def api_reset_face():

    data = request.json

    username = data.get("username")

    reset_face_verification(username)

    return jsonify({"status": "reset"})


# -------------------------
# MARK ATTENDANCE
# -------------------------
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():

    global QR_TOKEN, QR_EXPIRY

    if "session" not in SESSION:
        return jsonify({"status": "attendance_closed"})

    data = request.json

    token = data.get("token")
    name = data.get("name")
    roll = data.get("roll")
    division = data.get("division")
    username = data.get("username")

    if not is_face_verified(username):
        return jsonify({"status": "face_verification_invalid"})

    if token != QR_TOKEN:
        return jsonify({"status": "invalid_qr"})

    if time.time() > QR_EXPIRY:
        return jsonify({"status": "qr_expired"})

    if division != SESSION["division"]:
        return jsonify({"status": "wrong_division"})

    today = str(datetime.now().date())
    time_now = datetime.now().strftime("%H:%M")

    records = sheet.get_all_records()

    for r in records:

        if str(r["Roll"]) == str(roll) and r["Date"] == today and str(r["Lecture"]) == str(SESSION["lecture"]):

            return jsonify({"status": "already_marked"})

    row = [
        today,
        time_now,
        name,
        roll,
        division,
        SESSION["subject"],
        SESSION["lecture"],
        SESSION["teacher"]
    ]

    sheet.append_row(row)

    return jsonify({"status": "present"})


# -------------------------
# VIEW ATTENDANCE
# -------------------------
@app.route("/attendance_by_division")
def attendance_by_division():

    division = request.args.get("division")

    records = sheet.get_all_records()

    filtered = [r for r in records if r["Division"] == division]

    return jsonify(filtered)


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)