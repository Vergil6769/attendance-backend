import pickle
import time
import numpy as np

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
# COMPARE FACE ENCODINGS
# -----------------------------
def compare_encodings(known, unknown, tolerance=0.6):

    dist = np.linalg.norm(np.array(known) - np.array(unknown))

    return dist < tolerance


# -----------------------------
# VERIFY FACE
# -----------------------------
def verify_face(username, encoding):

    if username not in student_encodings:
        return False

    try:
        new_encoding = np.array(encoding)
    except:
        return False

    known_encoding = student_encodings[username]["front"]

    match = compare_encodings(known_encoding, new_encoding)

    if match:
        # valid for 10 seconds
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