import pickle
import time
import numpy as np
import base64
import cv2
import face_recognition

# -----------------------------
# LOAD STUDENT ENCODINGS
# -----------------------------
with open("student_encodings.pkl", "rb") as f:
    student_encodings = pickle.load(f)

# -----------------------------
# FACE VERIFICATION STATUS
# -----------------------------
face_verified_status = {}  # username -> expiry timestamp


# -----------------------------
# BASE64 IMAGE → NUMPY IMAGE
# -----------------------------
def decode_base64_image(base64_string):

    try:

        header, encoded = base64_string.split(",", 1)

        image_bytes = base64.b64decode(encoded)

        np_arr = np.frombuffer(image_bytes, np.uint8)

        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        return rgb

    except:
        return None


# -----------------------------
# COMPARE FACE ENCODINGS
# -----------------------------
def compare_encodings(known, unknown, tolerance=0.55):

    dist = np.linalg.norm(np.array(known) - np.array(unknown))

    return dist < tolerance


# -----------------------------
# VERIFY FACE
# -----------------------------
def verify_face(username, image_base64):

    if username not in student_encodings:
        return False

    img = decode_base64_image(image_base64)

    if img is None:
        return False

    # Detect faces
    face_locations = face_recognition.face_locations(img)

    if len(face_locations) == 0:
        return False

    # Generate encoding
    encodings = face_recognition.face_encodings(img, face_locations)

    if len(encodings) == 0:
        return False

    new_encoding = encodings[0]

    # Stored encoding
    known_encoding = student_encodings[username]["front"]

    match = compare_encodings(known_encoding, new_encoding)

    if match:

        # Valid for 10 seconds
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