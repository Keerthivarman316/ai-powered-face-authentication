import cv2
import sys
import os


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from app.face_engine import FaceEngine


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("❌ Could not open camera.")

    sys.exit(1)


# ============================================================
# FACE ENGINE
# ============================================================

engine = FaceEngine()


print()
print("=" * 60)
print("FACE ENGINE CAMERA TEST")
print("=" * 60)
print("Show exactly one face to the camera.")
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


    # --------------------------------------------------------
    # Analyze frame
    # --------------------------------------------------------

    results = engine.analyze(frame)


    # --------------------------------------------------------
    # No face
    # --------------------------------------------------------

    if len(results) == 0:

        cv2.putText(
            frame,
            "NO FACE",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )


    # --------------------------------------------------------
    # Multiple faces
    # --------------------------------------------------------

    elif len(results) > 1:

        cv2.putText(
            frame,
            f"{len(results)} FACES DETECTED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        for result in results:

            face = result["face"]

            bbox = face.bbox.astype(int)

            x1, y1, x2, y2 = bbox

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2
            )


    # --------------------------------------------------------
    # Exactly one face
    # --------------------------------------------------------

    else:

        result = results[0]

        face = result["face"]

        embedding = result["embedding"]

        bbox = face.bbox.astype(int)

        x1, y1, x2, y2 = bbox


        # ----------------------------------------------------
        # Draw face
        # ----------------------------------------------------

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )


        # ----------------------------------------------------
        # Display embedding information
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "FACE DETECTED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Embedding: {embedding.shape[0]}D",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Norm: {((embedding ** 2).sum()) ** 0.5:.4f}",
            (30, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "Face Engine Test",
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
print("Face Engine test stopped.")