import cv2
import sys
import os

# ============================================================
# PATH SETUP
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.pad_engine import PAD


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = 1

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("❌ Could not open camera.")
    sys.exit(1)


# ============================================================
# PAD ENGINE
# ============================================================

pad = PAD()


# ============================================================
# FACE DETECTOR
# ============================================================

cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

face_detector = cv2.CascadeClassifier(cascade_path)

if face_detector.empty():
    print("❌ Could not load Haar Cascade.")
    cap.release()
    sys.exit(1)


print()
print("=" * 60)
print("MINIFASNET WEBCAM PAD TEST")
print("=" * 60)
print("Press Q to quit.")
print("=" * 60)
print()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("❌ Failed to read camera frame.")
        break

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    if len(faces) == 0:

        cv2.putText(
            frame,
            "NO FACE",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

    elif len(faces) > 1:

        cv2.putText(
            frame,
            "ONLY ONE FACE ALLOWED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        for (x, y, w, h) in faces:

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                2
            )

    else:

        x, y, w, h = faces[0]

        bbox = [
            int(x),
            int(y),
            int(w),
            int(h)
        ]

        result = pad.check(
            frame,
            bbox
        )

        label = result["label"]
        confidence = result["confidence"]

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        if label == "REAL":

            box_color = (0, 255, 0)

        elif label == "SPOOF":

            box_color = (0, 0, 255)

        else:

            box_color = (0, 255, 255)

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            box_color,
            2
        )

        cv2.putText(
            frame,
            f"{label} {confidence * 100:.2f}%",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            box_color,
            2
        )

        # ----------------------------------------------------
        # CLASS PROBABILITIES
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"C0: {result['class_0'] * 100:.2f}%",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"C1 REAL: {result['class_1'] * 100:.2f}%",
            (30, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"C2: {result['class_2'] * 100:.2f}%",
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )


    # ========================================================
    # SHOW
    # ========================================================

    cv2.imshow(
        "MiniFASNet PAD",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()

print()
print("PAD webcam test stopped.")