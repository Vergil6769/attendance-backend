import pickle
import time
import numpy as np

# ---------------------------------
# LOAD STUDENT ENCODINGS
# ---------------------------------
try:
    with open("student_encodings.pkl", "rb") as f:
        student_encodings = pickle.load(f)
except Exception as e:
    print("ERROR loading student_encodings.pkl:", e)
    student_encodings = {}

# ---------------------------------
# FACE VERIFICATION STATUS
# username -> expiry timestamp
# ---------------------------------
face_verified_status = {}

# ---------------------------------
# COMPARE FACE ENCODINGS
# ---------------------------------
def compare_encodings(known, unknown, tolerance=0.6):
    try:
        known = np.array(known)
        unknown = np.array(unknown)
        if known.shape != unknown.shape:
            return False
        distance = np.linalg.norm(known - unknown)
        return distance < tolerance
    except Exception as e:
        print("ERROR in compare_encodings:", e)
        return False

# ---------------------------------
# VERIFY FACE
# ---------------------------------
def verify_face(username, encoding):
    if username not in student_encodings:
        print(f"Username {username} not found in encodings")
        return False
    try:
        new_encoding = np.array(encoding, dtype=float)
        if new_encoding.shape[0] != 128:
            print(f"Encoding length invalid for {username}, got {new_encoding.shape[0]}")
            return False
    except Exception as e:
        print(f"Error converting encoding to np.array for {username}:", e)
        return False

    known_encoding = student_encodings[username]["front"]
    match = compare_encodings(known_encoding, new_encoding)

    if match:
        # Face verification valid for 10 seconds
        face_verified_status[username] = time.time() + 10

    return match

# ---------------------------------
# CHECK FACE VERIFIED
# ---------------------------------
def is_face_verified(username):
    expiry = face_verified_status.get(username, 0)
    return time.time() < expiry

# ---------------------------------
# RESET VERIFICATION
# ---------------------------------
def reset_face_verification(username):
    face_verified_status[username] = 0