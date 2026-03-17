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
    print("Error loading student_encodings.pkl:", e)
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
        if known.shape[0] != 128 or unknown.shape[0] != 128:
            return False
        distance = np.linalg.norm(known - unknown)
        return distance < tolerance
    except Exception as e:
        print("Compare encoding error:", e)
        return False

# ---------------------------------
# VERIFY FACE
# ---------------------------------
@app.route("/verify_face", methods=["POST"])
def api_verify_face():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "no data received"}), 400

        username = data.get("username")
        encoding = data.get("encoding")

        if not username or not encoding:
            return jsonify({"error": "username or encoding missing"}), 400

        match = verify_face(username, encoding)
        return jsonify({"match": match})

    except Exception as e:
        print("ERROR in /verify_face:", e)  # This prints to your backend console
        return jsonify({"error": str(e)}), 500

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