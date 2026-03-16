import pickle
import base64
import io
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
def compare_encodings(known, unknown, tolerance=0.6):
    """
    Simple Euclidean distance based comparison.
    Returns True if distance < tolerance
    """
    dist = np.linalg.norm(np.array(known) - np.array(unknown))
    return dist < tolerance


# -----------------------------
# DECODE CAMERA IMAGE
# -----------------------------
def decode_base64_image(base64_str):
    """
    Converts base64 webcam image to numpy array
    """
    try:
        img_data = base64.b64decode(base64_str.split(",")[1])
        return np.frombuffer(img_data, dtype=np.uint8)  # Just return raw bytes
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

    # In precomputed mode, image_base64 should already contain a 128-d vector
    # If you actually still want webcam capture, you need to encode it offline in Colab
    try:
        new_encoding = np.array(base64.b64decode(image_base64))  # Assuming frontend sends 128-d encoding
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