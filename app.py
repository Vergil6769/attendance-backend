from flask_cors import CORS
from flask import Flask, request, jsonify, send_file
import pandas as pd
import qrcode
from datetime import datetime
from io import BytesIO
import os
import json
import uuid
import time
from math import sqrt

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# -------------------------
# FILES & SESSION
# -------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

students_file = os.path.join(data_dir, "students.xlsx")
teachers_file = os.path.join(data_dir, "teachers.xlsx")
face_data_file = os.path.join(data_dir, "face_descriptors.json")
attendance_file = os.path.join(data_dir, "attendance.xlsx")
frontend_url = os.environ.get(
    "FRONTEND_URL", "https://vergil6769.github.io/attendance-frontend"
)
attendance_columns = [
    "Date",
    "Time",
    "Name",
    "Roll",
    "Division",
    "Subject",
    "Lecture",
    "Teacher",
]

SESSION = {}

QR_TOKEN = None
QR_EXPIRY = None
FACE_DISTANCE_THRESHOLD = 0.6


# -------------------------
# GOOGLE SHEETS SETUP
# -------------------------

SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1MDQUccq8OXRAArfcjVuKI_GJH0GEQNr-jabAvlMcRws")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

sheet = None
sheet_error = None

service_key_raw = os.environ.get("GOOGLE_SERVICE_KEY")

if service_key_raw and gspread is not None and Credentials is not None:
    try:
        service_key = json.loads(service_key_raw)
        creds = Credentials.from_service_account_info(service_key, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SHEET_ID).sheet1
    except Exception as exc:
        sheet_error = str(exc)
elif service_key_raw and (gspread is None or Credentials is None):
    sheet_error = "Google Sheets dependencies are not installed"


def load_face_descriptors():
    if not os.path.exists(face_data_file):
        return {}

    with open(face_data_file, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {}


def save_face_descriptors(data):
    with open(face_data_file, "w", encoding="utf-8") as file:
        json.dump(data, file)


def get_json_payload():
    return request.get_json(silent=True) or {}


def normalize_descriptor(raw_descriptor):
    if not isinstance(raw_descriptor, list) or len(raw_descriptor) != 128:
        return None

    normalized = []

    for value in raw_descriptor:
        try:
            normalized.append(float(value))
        except (TypeError, ValueError):
            return None

    return normalized


def descriptor_distance(descriptor_a, descriptor_b):
    return sqrt(sum((a - b) ** 2 for a, b in zip(descriptor_a, descriptor_b)))


def load_attendance_dataframe():
    if os.path.exists(attendance_file):
        return pd.read_excel(attendance_file, dtype=str).fillna("")

    return pd.DataFrame(columns=attendance_columns)


def get_attendance_records():
    if sheet is not None:
        try:
            return sheet.get_all_records()
        except Exception:
            pass

    return load_attendance_dataframe().to_dict(orient="records")


def append_attendance_record(row):
    if sheet is not None:
        try:
            sheet.append_row(row)
            return
        except Exception:
            pass

    df = load_attendance_dataframe()
    new_row = pd.DataFrame([dict(zip(attendance_columns, row))])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(attendance_file, index=False)


# -------------------------
# TEACHER LOGIN
# -------------------------
@app.route("/teacher_login", methods=["POST"])
def teacher_login():
    data = get_json_payload()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400

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
    data = get_json_payload()
    division = str(data.get("division", "")).strip().upper()
    teacher = str(data.get("teacher", "")).strip()

    try:
        lecture = int(data.get("lecture"))
    except (TypeError, ValueError):
        return jsonify({"status": "invalid_lecture"}), 400

    if division not in {"A", "B", "C"}:
        return jsonify({"status": "invalid_division"}), 400

    if not teacher:
        return jsonify({"status": "teacher_required"}), 400

    timetable_file = os.path.join(data_dir, f"timetable{division}.xlsx")

    if os.path.exists(timetable_file):
        timetable = pd.read_excel(timetable_file)
    else:
        return jsonify({"status": "timetable_missing"})

    today = datetime.now().strftime("%A")

    lec = timetable[(timetable["Day"] == today) & (timetable["Lecture"] == lecture)]

    if lec.empty:
        return jsonify({"status": "no_lecture_today"})

    subject = lec.iloc[0]["Subject"]
    session_id = str(datetime.now().timestamp())

    SESSION.clear()
    SESSION.update(
        {
            "session": session_id,
            "division": division,
            "lecture": lecture,
            "subject": subject,
            "teacher": teacher,
        }
    )

    return jsonify(
        {"status": "session_started", "subject": subject, "session": session_id}
    )


# -------------------------
# STOP SESSION
# -------------------------
@app.route("/stop_session", methods=["POST"])
def stop_session():
    global QR_TOKEN, QR_EXPIRY
    SESSION.clear()
    QR_TOKEN = None
    QR_EXPIRY = None
    return jsonify({"status": "stopped"})


# -------------------------
# STUDENT LOGIN
# -------------------------
@app.route("/student_login", methods=["POST"])
def student_login():
    data = get_json_payload()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400

    df = pd.read_excel(students_file, dtype=str)

    df["Username"] = df["Username"].str.strip()
    df["Password"] = df["Password"].str.strip()

    user = df[(df["Username"] == username) & (df["Password"] == password)]

    if user.empty:
        return jsonify({"status": "fail"})

    student = user.iloc[0]
    face_descriptors = load_face_descriptors()
    username_key = str(student["Username"])

    return jsonify(
        {
            "status": "success",
            "name": student["Name"],
            "roll": str(student["Roll"]),
            "division": student["Division"],
            "username": username_key,
            "face_enrolled": username_key in face_descriptors,
        }
    )


@app.route("/face_status", methods=["GET"])
def face_status():
    username = str(request.args.get("username", "")).strip()

    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400

    face_descriptors = load_face_descriptors()

    return jsonify(
        {
            "status": "success",
            "face_enrolled": username in face_descriptors,
        }
    )


@app.route("/enroll_face", methods=["POST"])
def enroll_face():
    data = get_json_payload()

    username = str(data.get("username", "")).strip()
    descriptor = normalize_descriptor(data.get("descriptor"))

    if not username or descriptor is None:
        return jsonify({"status": "error", "message": "Invalid enrollment payload"}), 400

    df = pd.read_excel(students_file, dtype=str)
    df["Username"] = df["Username"].str.strip()

    if df[df["Username"] == username].empty:
        return jsonify({"status": "student_not_found"}), 404

    face_descriptors = load_face_descriptors()
    face_descriptors[username] = descriptor
    save_face_descriptors(face_descriptors)

    return jsonify({"status": "enrolled"})


@app.route("/verify_face", methods=["POST"])
def verify_face():
    data = get_json_payload()

    username = str(data.get("username", "")).strip()
    descriptor = normalize_descriptor(data.get("descriptor"))

    if not username or descriptor is None:
        return jsonify({"status": "error", "message": "Invalid verification payload"}), 400

    face_descriptors = load_face_descriptors()
    saved_descriptor = face_descriptors.get(username)

    if not saved_descriptor:
        return jsonify({"status": "face_not_enrolled"})

    distance = descriptor_distance(saved_descriptor, descriptor)

    return jsonify(
        {
            "status": "matched" if distance <= FACE_DISTANCE_THRESHOLD else "face_mismatch",
            "distance": round(distance, 4),
            "threshold": FACE_DISTANCE_THRESHOLD,
        }
    )


# -------------------------
# GENERATE QR (7s token)
# -------------------------
@app.route("/generate_qr")
def generate_qr():

    global QR_TOKEN, QR_EXPIRY

    session_id = SESSION.get("session")

    if not session_id:
        return jsonify({"status": "session_not_started"}), 400

    QR_TOKEN = str(uuid.uuid4())
    QR_EXPIRY = time.time() + 7

    url = f"{frontend_url}/verify.html?session={session_id}&token={QR_TOKEN}"

    img = qrcode.make(url)

    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


# -------------------------
# MARK ATTENDANCE
# -------------------------
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():

    global QR_TOKEN, QR_EXPIRY

    if "session" not in SESSION:
        return jsonify({"status": "attendance_closed"})

    data = get_json_payload()

    token = data.get("token")
    session = data.get("session")

    if token != QR_TOKEN:
        return jsonify({"status": "invalid_qr"})

    if time.time() > QR_EXPIRY:
        return jsonify({"status": "qr_expired"})

    if session != SESSION.get("session"):
        return jsonify({"status": "invalid_session"})

    name = data.get("name")
    roll = data.get("roll")
    division = data.get("division")

    if not all([name, roll, division]):
        return jsonify({"status": "error", "message": "Incomplete data"})

    if division != SESSION["division"]:
        return jsonify({"status": "wrong_division"})

    today = str(datetime.now().date())
    time_now = datetime.now().strftime("%H:%M")

    records = get_attendance_records()

    for r in records:
        if (
            str(r["Roll"]) == str(roll)
            and r["Date"] == today
            and str(r["Lecture"]) == str(SESSION["lecture"])
        ):
            return jsonify({"status": "already_marked"})

    row = [
        today,
        time_now,
        name,
        roll,
        division,
        SESSION["subject"],
        SESSION["lecture"],
        SESSION["teacher"],
    ]

    append_attendance_record(row)

    return jsonify({"status": "present"})


# -------------------------
# VIEW ATTENDANCE BY DIVISION
# -------------------------
@app.route("/attendance_by_division")
def attendance_by_division():
    division = str(request.args.get("division", "")).strip().upper()
    records = get_attendance_records()

    filtered = [r for r in records if str(r.get("Division", "")).strip().upper() == division]

    return jsonify(filtered)


@app.route("/attendance_data")
def attendance_data():
    return jsonify(get_attendance_records())


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "storage": "google_sheets" if sheet is not None else "excel_file",
            "sheet_error": sheet_error,
        }
    )


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
