import pickle
import time
import numpy as np
import os

# Load encodings relative to backend folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKLE_PATH = os.path.join(BASE_DIR, "student_encodings.pkl")

try:
    with open(PICKLE_PATH, "rb") as f:
        student_encodings = pickle.load(f)
except Exception as e:
    print("Error loading student_encodings.pkl:", e)
    student_encodings = {}

face_verified_status = {}

def compare_encodings(known, unknown, tolerance=0.6):
    try:
        known = np.array(known)
        unknown = np.array(unknown)
        if known.shape[0] != 128 or unknown.shape[0] != 128:
            return False
        distance = np.linalg.norm(known - unknown)
        return distance < tolerance
    except Exception as e:
        print("Compare encoding error:", e)
        return False

def verify_face(username, encoding):
    if username not in student_encodings:
        print(f"Username {username} not found in encodings")
        return False
    try:
        new_encoding = np.array(encoding)
        if new_encoding.shape[0] != 128:
            print("Incoming encoding wrong length:", new_encoding.shape[0])
            return False
    except Exception as e:
        print("Error converting encoding:", e)
        return False

    known_encoding = student_encodings[username]["front"]
    match = compare_encodings(known_encoding, new_encoding)
    if match:
        face_verified_status[username] = time.time() + 10
    return match

def is_face_verified(username):
    expiry = face_verified_status.get(username, 0)
    return time.time() < expiry

def reset_face_verification(username):
    face_verified_status[username] = 0