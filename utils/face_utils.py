import pickle
import time
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------

# Load precomputed encodings
# Make sure student_encodings.pkl is in the backend folder
with open("student_encodings.pkl", "rb") as f:
    # Format: { "A01": {"front": [...], "left": [...], "right": [...]}, ... }
    student_encodings = pickle.load(f)

# Temporary verification storage
face_verified_status = {}  # username -> expiry timestamp

# -----------------------------
# SIMPLE FACE COMPARISON
# -----------------------------
def compare_encodings(known, unknown, tolerance=0.65):
    """
    Euclidean distance comparison between two 128-d vectors.
    Returns True if distance < tolerance
    """
    dist = np.linalg.norm(np.array(known) - np.array(unknown))
    return dist < tolerance

# -----------------------------
# VERIFY FACE
# -----------------------------
def verify_face(username, angle, encoding):
    """
    Checks if the frontend-provided 128-d vector matches the stored encoding for that angle
    """
    if username not in student_encodings:
        return False

    known_encoding = student_encodings[username].get(angle)
    if known_encoding is None:
        return False

    try:
        new_encoding = np.array(encoding)
    except:
        return False

    match = compare_encodings(known_encoding, new_encoding)

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