import cv2
import time
import numpy as np

from app.face_engine import FaceEngine
from app.pad_engine import PAD

from storage.database import (
    initialize_database,
    get_user,
    create_user_with_templates,
)


# ============================================================
# CONFIGURATION
# ============================================================

REQUIRED_SAMPLES = 5

CAPTURE_INTERVAL = 0.8

CAMERA_INDEX = 1

MAX_SESSION_TIME = 20.0

# Starting development value.
# This must be evaluated on a representative dataset
# before being treated as a production security threshold.
MIN_SAMPLE_SIMILARITY = 0.75


# ============================================================
# ENROLLMENT ENGINE
# ============================================================

class EnrollmentEngine:

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING ENROLLMENT ENGINE")
        print("=" * 60)

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        initialize_database()

        # ----------------------------------------------------
        # Face Engine
        # ----------------------------------------------------

        self.face_engine = FaceEngine()

        # ----------------------------------------------------
        # PAD
        # ----------------------------------------------------

        self.pad = PAD()

        print("=" * 60)
        print("ENROLLMENT ENGINE READY")
        print("=" * 60)

    # ========================================================
    # SAMPLE CONSISTENCY
    # ========================================================

    def check_sample_consistency(self, embeddings):

        if len(embeddings) < 2:

            return False, 0.0

        similarities = []

        for i in range(len(embeddings)):

            for j in range(i + 1, len(embeddings)):

                a = embeddings[i]
                b = embeddings[j]

                denominator = (
                    np.linalg.norm(a)
                    * np.linalg.norm(b)
                )

                if denominator == 0:

                    return False, 0.0

                similarity = float(
                    np.dot(a, b)
                    / denominator
                )

                similarities.append(
                    similarity
                )

        min_similarity = min(
            similarities
        )

        return (
            min_similarity >= MIN_SAMPLE_SIMILARITY,
            min_similarity
        )

    # ========================================================
    # ENROLL
    # ========================================================

    def enroll(
        self,
        customer_id: str,
        external_user_id: str
    ):

        print()
        print("=" * 60)
        print("STARTING FACE ENROLLMENT")
        print("=" * 60)

        print(
            f"Customer ID : {customer_id}"
        )

        print(
            f"User ID     : {external_user_id}"
        )

        print("=" * 60)

        # ----------------------------------------------------
        # Check whether user already exists
        # ----------------------------------------------------

        existing_user = get_user(
            customer_id,
            external_user_id
        )

        if existing_user is not None:

            print()
            print("=" * 60)
            print("❌ USER ALREADY EXISTS")
            print("=" * 60)

            print(
                f"Internal User ID : "
                f"{existing_user['id']}"
            )

            return False

        # ----------------------------------------------------
        # Enrollment state
        # ----------------------------------------------------

        embeddings = []

        last_capture_time = 0.0

        start_time = time.time()

        # ----------------------------------------------------
        # Open camera
        # ----------------------------------------------------

        cap = cv2.VideoCapture(
            CAMERA_INDEX
        )

        if not cap.isOpened():

            print()
            print("❌ Could not open camera.")

            return False

        print()
        print("Look directly at the camera.")
        print("Press Q to cancel.")
        print()

        # ====================================================
        # CAMERA LOOP
        # ====================================================

        try:

            while True:

                # ------------------------------------------------
                # Timeout
                # ------------------------------------------------

                elapsed_time = (
                    time.time()
                    - start_time
                )

                if elapsed_time >= MAX_SESSION_TIME:

                    print()
                    print(
                        "Enrollment session timed out."
                    )

                    break

                # ------------------------------------------------
                # Read frame
                # ------------------------------------------------

                ret, frame = cap.read()

                if not ret:

                    print()
                    print(
                        "❌ Failed to read camera frame."
                    )

                    break

                # ------------------------------------------------
                # Default UI
                # ------------------------------------------------

                status = "LOOK AT CAMERA"

                status_color = (
                    255,
                    255,
                    255
                )

                # =================================================
                # FACE DETECTION
                # =================================================

                faces = (
                    self.face_engine
                    .detect_faces(frame)
                )

                # ------------------------------------------------
                # No face
                # ------------------------------------------------

                if len(faces) == 0:

                    status = "NO FACE"

                    status_color = (
                        0,
                        255,
                        255
                    )

                # ------------------------------------------------
                # Multiple faces
                # ------------------------------------------------

                elif len(faces) > 1:

                    status = (
                        "ONLY ONE FACE ALLOWED"
                    )

                    status_color = (
                        0,
                        0,
                        255
                    )

                # ------------------------------------------------
                # Exactly one face
                # ------------------------------------------------

                else:

                    face = faces[0]

                    bbox = (
                        face.bbox
                        .astype(int)
                    )

                    x1, y1, x2, y2 = bbox

                    # --------------------------------------------
                    # Convert InsightFace bbox
                    # to MiniFASNet PAD format
                    #
                    # [x, y, width, height]
                    # --------------------------------------------

                    pad_bbox = [
                        int(x1),
                        int(y1),
                        int(x2 - x1),
                        int(y2 - y1)
                    ]

                    # ============================================
                    # PAD CHECK
                    # ============================================

                    pad_result = self.pad.check(
                        frame,
                        pad_bbox
                    )

                    pad_label = (
                        pad_result["label"]
                    )

                    pad_confidence = (
                        pad_result["confidence"]
                    )

                    # --------------------------------------------
                    # SPOOF
                    # --------------------------------------------

                    if pad_label == "SPOOF":

                        status = (
                            f"SPOOF "
                            f"{pad_confidence * 100:.1f}%"
                        )

                        status_color = (
                            0,
                            0,
                            255
                        )

                    # --------------------------------------------
                    # PAD UNKNOWN
                    # --------------------------------------------

                    elif pad_label != "REAL":

                        status = (
                            "PAD CHECKING"
                        )

                        status_color = (
                            0,
                            255,
                            255
                        )

                    # --------------------------------------------
                    # REAL FACE
                    # --------------------------------------------

                    else:

                        status = (
                            f"REAL "
                            f"{pad_confidence * 100:.1f}%"
                        )

                        status_color = (
                            0,
                            255,
                            0
                        )

                        current_time = (
                            time.time()
                        )

                        # ========================================
                        # CAPTURE SAMPLE
                        # ========================================

                        if (
                            current_time
                            - last_capture_time
                            >= CAPTURE_INTERVAL
                        ):

                            embedding = (
                                self.face_engine
                                .get_embedding(face)
                            )

                            if embedding is not None:

                                embeddings.append(
                                    embedding
                                )

                                last_capture_time = (
                                    current_time
                                )

                                print(
                                    f"Captured sample "
                                    f"{len(embeddings)}/"
                                    f"{REQUIRED_SAMPLES}"
                                )

                                status = (
                                    f"CAPTURED "
                                    f"{len(embeddings)}/"
                                    f"{REQUIRED_SAMPLES}"
                                )

                        # ========================================
                        # FINISHED
                        # ========================================

                        if (
                            len(embeddings)
                            >= REQUIRED_SAMPLES
                        ):

                            status = (
                                "CAPTURE COMPLETE"
                            )

                # =================================================
                # DRAW FACE BOX
                # =================================================

                if len(faces) == 1:

                    face = faces[0]

                    bbox = (
                        face.bbox
                        .astype(int)
                    )

                    x1, y1, x2, y2 = bbox

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        status_color,
                        2
                    )

                    # PAD status

                    if "pad_result" in locals():

                        cv2.putText(
                            frame,
                            (
                                f"PAD: "
                                f"{pad_result['label']} "
                                f"{pad_result['confidence'] * 100:.1f}%"
                            ),
                            (30, 80),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            status_color,
                            2
                        )

                # =================================================
                # STATUS
                # =================================================

                cv2.putText(
                    frame,
                    status,
                    (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    status_color,
                    2
                )

                # =================================================
                # SAMPLE COUNT
                # =================================================

                cv2.putText(
                    frame,
                    (
                        f"SAMPLES: "
                        f"{len(embeddings)}/"
                        f"{REQUIRED_SAMPLES}"
                    ),
                    (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2
                )

                # =================================================
                # TIME REMAINING
                # =================================================

                remaining_time = max(
                    0,
                    int(
                        MAX_SESSION_TIME
                        - elapsed_time
                    )
                )

                cv2.putText(
                    frame,
                    (
                        f"TIME: "
                        f"{remaining_time}s"
                    ),
                    (30, 155),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                # =================================================
                # CANCEL
                # =================================================

                cv2.putText(
                    frame,
                    "Q = CANCEL",
                    (30, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                # =================================================
                # DISPLAY
                # =================================================

                cv2.imshow(
                    "Face Enrollment",
                    frame
                )

                # =================================================
                # COMPLETE
                # =================================================

                if (
                    len(embeddings)
                    >= REQUIRED_SAMPLES
                ):

                    cv2.waitKey(500)

                    break

                # =================================================
                # KEYBOARD
                # =================================================

                key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if key == ord("q"):

                    print()
                    print(
                        "Enrollment cancelled."
                    )

                    return False

        finally:

            cap.release()

            cv2.destroyAllWindows()

        # ========================================================
        # CAPTURE VALIDATION
        # ========================================================

        if len(embeddings) < REQUIRED_SAMPLES:

            print()
            print("=" * 60)
            print("❌ ENROLLMENT FAILED")
            print("=" * 60)

            print(
                f"Captured "
                f"{len(embeddings)}/"
                f"{REQUIRED_SAMPLES} samples."
            )

            return False

        # ========================================================
        # SAMPLE CONSISTENCY
        # ========================================================

        consistency_ok, min_similarity = (
            self.check_sample_consistency(
                embeddings
            )
        )

        print()
        print(
            f"Minimum sample similarity : "
            f"{min_similarity:.4f}"
        )

        if not consistency_ok:

            print()
            print("=" * 60)
            print("❌ ENROLLMENT FAILED")
            print("=" * 60)

            print(
                "Captured face samples "
                "were not sufficiently consistent."
            )

            print(
                "Please enroll again while "
                "keeping your face clearly visible."
            )

            return False

        # ========================================================
        # ATOMIC DATABASE STORAGE
        # ========================================================

        print()
        print(
            "Saving biometric templates..."
        )

        try:

            storage_result = (
                create_user_with_templates(
                    customer_id=customer_id,
                    external_user_id=external_user_id,
                    embeddings=embeddings
                )
            )

        except Exception as error:

            print()
            print("=" * 60)
            print("❌ DATABASE STORAGE FAILED")
            print("=" * 60)

            print(
                f"Error: {error}"
            )

            return False

        # ========================================================
        # SUCCESS
        # ========================================================

        print()
        print("=" * 60)
        print("✅ ENROLLMENT COMPLETE")
        print("=" * 60)

        print(
            f"Customer ID : "
            f"{customer_id}"
        )

        print(
            f"User ID     : "
            f"{external_user_id}"
        )

        print(
            f"Templates   : "
            f"{storage_result['template_count']}"
        )

        print(
            f"Min Similarity : "
            f"{min_similarity:.4f}"
        )

        print("=" * 60)

        return True


# ============================================================
# DEVELOPMENT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    engine = EnrollmentEngine()

    engine.enroll(
        customer_id="DEMO_COMPANY",
        external_user_id="USER_002"
    )