import pickle
import base64
import io
import time
import face_recognition
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------

# Load precomputed encodings
# Make sure student_encodings.pkl is in the backend folder
with open("student_encodings.pkl", "rb") as f:
    student_encodings = pickle.load(f)  # Format: { "A01": {"front": [...], "left": [...], "right": [...]}, ... }

# Temporary verification storage
face_verified_status = {}  # username -> expiry timestamp


# -----------------------------
# ENCODE CAMERA IMAGE
# -----------------------------
def encode_image(base64_str):
    """
    Converts base64 webcam image to 128-d face encoding
    """
    try:
        img_data = base64.b64decode(base64_str.split(",")[1])
        img = face_recognition.load_image_file(io.BytesIO(img_data))
        encodings = face_recognition.face_encodings(img)
        return encodings[0] if encodings else None
    except:
        return None


# -----------------------------
# VERIFY FACE
# -----------------------------
def verify_face(username, angle, image_base64):
    """
    Checks if the captured face matches the known encoding for that angle
    """
    if username not in student_encodings:
        return False

    known_encoding = student_encodings[username].get(angle)
    if known_encoding is None:
        return False

    new_encoding = encode_image(image_base64)
    if new_encoding is None:
        return False

    match = face_recognition.compare_faces([np.array(known_encoding)], new_encoding)[0]

    if match:
        # Mark verified for 10 seconds
        face_verified_status[username] = time.time() + 10

    return match


# -----------------------------
# CHECK VERIFIED STATUS
# -----------------------------
def is_face_verified(username):
    """
    Returns True if the face verification is still valid
    """
    expiry = face_verified_status.get(username, 0)
    return time.time() < expiry


# -----------------------------
# RESET STATUS
# -----------------------------
def reset_face_verification(username):
    """
    Resets verification timer
    """
    face_verified_status[username] = 0