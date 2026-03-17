from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import os
import uuid
import time
import gspread
from google.oauth2.service_account import Credentials
import json

from utils.face_utils import verify_face, reset_face_verification, is_face_verified

app = Flask(__name__)
CORS(app)

students_file = "data/students.xlsx"
teachers_file = "data/teachers.xlsx"
SESSION = {}
QR_TOKEN = None
QR_EXPIRY = None

# Google Sheets
SHEET_ID = "1MDQUccq8OXRAArfcjVuKI_GJH0GEQNr-jabAvlMcRws"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]

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
    username = str(data.get("username")).strip()
    password = str(data.get("password")).strip()
    df = pd.read_excel(teachers_file, dtype=str)
    df["username"] = df["username"].str.strip()
    df["password"] = df["password"].str.strip()
    user = df[(df["username"] == username) & (df["password"] == password)]
    if not user.empty:
        SESSION["teacher"] = username
        return jsonify({"status": "success"})
    return jsonify({"status": "invalid"})

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
# FACE VERIFY
# -------------------------
@app.route("/verify_face", methods=["POST"])
def api_verify_face():
    try:
        data = request.json
        username = data.get("username")
        encoding = data.get("encoding")
        if not username or not encoding or len(encoding) != 128:
            return jsonify({"error": "invalid data"}), 400
        encoding = [float(x) for x in encoding]
        match = verify_face(username, encoding)
        return jsonify({"match": match})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -------------------------
# RESET FACE
# -------------------------
@app.route("/reset_face_verification", methods=["POST"])
def api_reset_face():
    data = request.json
    username = data.get("username")
    reset_face_verification(username)
    return jsonify({"status": "reset"})

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)