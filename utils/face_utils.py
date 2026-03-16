import face_recognition
import base64
import io
import time
import requests
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------

GITHUB_BASE = "https://raw.githubusercontent.com/Vergil6769/student-images/main/students"

# Store encodings
face_db = {}

# Temporary verification
face_verified_status = {}


# -----------------------------
# LOAD IMAGE FROM URL
# -----------------------------

def load_image_from_url(url):

    r = requests.get(url)

    if r.status_code != 200:
        return None

    img = face_recognition.load_image_file(io.BytesIO(r.content))

    enc = face_recognition.face_encodings(img)

    if len(enc) == 0:
        return None

    return enc[0]


# -----------------------------
# LOAD STUDENT FACES
# -----------------------------

def load_student_faces(username):

    if username in face_db:
        return

    division = username[0]

    angles = ["front", "left", "right"]

    face_db[username] = {}

    for angle in angles:

        url = f"{GITHUB_BASE}/{division}/{username}/{angle}.jpg"

        encoding = load_image_from_url(url)

        if encoding is not None:
            face_db[username][angle] = encoding


# -----------------------------
# ENCODE CAMERA IMAGE
# -----------------------------

def encode_image(base64_str):

    img_data = base64.b64decode(base64_str.split(",")[1])

    img = face_recognition.load_image_file(io.BytesIO(img_data))

    encodings = face_recognition.face_encodings(img)

    return encodings[0] if encodings else None


# -----------------------------
# VERIFY FACE
# -----------------------------

def verify_face(username, angle, image_base64):

    load_student_faces(username)

    if username not in face_db:
        return False

    new_encoding = encode_image(image_base64)

    if new_encoding is None:
        return False

    known_encoding = face_db[username].get(angle)

    if known_encoding is None:
        return False

    match = face_recognition.compare_faces([known_encoding], new_encoding)[0]

    if match:
        face_verified_status[username] = time.time() + 10

    return match


# -----------------------------
# CHECK VERIFIED STATUS
# -----------------------------

def is_face_verified(username):

    expiry = face_verified_status.get(username, 0)

    return time.time() < expiry


# -----------------------------
# RESET STATUS
# -----------------------------

def reset_face_verification(username):

    face_verified_status[username] = 0