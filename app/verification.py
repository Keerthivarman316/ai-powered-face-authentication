import sys
import os
import cv2
import numpy as np


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# IMPORTS
# ============================================================

from app.face_engine import FaceEngine
from app.pad_engine import PAD
from app.camera_session import CameraSession

from storage.database import (
    initialize_database,
    get_user,
    get_face_templates,
)


# ============================================================
# CONFIGURATION
# ============================================================

CAMERA_INDEX = 1

# Maximum duration of one verification session.
MAX_SESSION_TIME = 10.0

# Number of valid face samples required before
# making the final identity decision.
REQUIRED_SAMPLES = 5

# Current development threshold.
#
# IMPORTANT:
# This has NOT been selected as a production threshold yet.
# We will determine the appropriate threshold after collecting
# genuine and impostor verification results.
MATCH_THRESHOLD = 0.60


# ============================================================
# VERIFICATION ENGINE
# ============================================================

class VerificationEngine:

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING VERIFICATION ENGINE")
        print("=" * 60)

        initialize_database()

        self.face_engine = FaceEngine()

        self.pad = PAD()

        print("=" * 60)
        print("VERIFICATION ENGINE READY")
        print("=" * 60)

    # ========================================================
    # SIMILARITY
    # ========================================================

    @staticmethod
    def cosine_similarity(
        embedding_a,
        embedding_b
    ):
        """
        Calculate cosine similarity between
        two face embeddings.
        """

        dot_product = float(
            embedding_a @ embedding_b
        )

        norm_a = float(
            (embedding_a ** 2).sum() ** 0.5
        )

        norm_b = float(
            (embedding_b ** 2).sum() ** 0.5
        )

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return (
            dot_product
            / (norm_a * norm_b)
        )

    # ========================================================
    # BEST TEMPLATE MATCH
    # ========================================================

    def compare_with_templates(
        self,
        embedding,
        templates
    ):
        """
        Compare one live embedding against
        all enrolled templates.

        Returns the highest similarity.
        """

        if not templates:
            return 0.0

        similarities = []

        for template in templates:

            similarity = self.cosine_similarity(
                embedding,
                template
            )

            similarities.append(
                similarity
            )

        return max(similarities)

    # ========================================================
    # DRAW FACE BOX
    # ========================================================

    @staticmethod
    def draw_face_box(
        frame,
        bbox,
        color,
        label=None
    ):
        """
        Draw the detected face bounding box.
        """

        x1, y1, x2, y2 = bbox

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        if label:

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA
            )

    # ========================================================
    # VERIFY
    # ========================================================

    def verify(
        self,
        customer_id: str,
        external_user_id: str
    ):
        """
        Verify a live face against one
        specific enrolled user.

        Verification flow:

            1. Validate user
            2. Load biometric templates
            3. Start camera session
            4. Wait for exactly one face
            5. Run PAD
            6. Require REAL result
            7. Collect 5 valid samples
            8. Calculate similarity for each sample
            9. Use median similarity
            10. Make final verification decision

        Possible reasons:

            USER_NOT_FOUND
            USER_INACTIVE
            NO_BIOMETRIC_DATA
            CAMERA_ERROR
            CAMERA_READ_ERROR
            TIMEOUT
            CANCELLED
            SPOOF_DETECTED
            EMBEDDING_ERROR
            FACE_NOT_MATCHED
            MATCH
        """

        print()
        print("=" * 60)
        print("STARTING FACE VERIFICATION")
        print("=" * 60)

        print(
            f"Customer ID : {customer_id}"
        )

        print(
            f"User ID     : {external_user_id}"
        )

        print("=" * 60)

        # ====================================================
        # USER VALIDATION
        # ====================================================

        user = get_user(
            customer_id,
            external_user_id
        )

        if user is None:

            print()
            print("❌ USER NOT FOUND")

            return {
                "verified": False,
                "reason": "USER_NOT_FOUND",
                "similarity": 0.0,
                "pad_confidence": 0.0,
                "samples": 0,
            }

        # ====================================================
        # ACTIVE STATUS
        # ====================================================

        if not user["active"]:

            print()
            print("❌ USER INACTIVE")

            return {
                "verified": False,
                "reason": "USER_INACTIVE",
                "similarity": 0.0,
                "pad_confidence": 0.0,
                "samples": 0,
            }

        # ====================================================
        # LOAD FACE TEMPLATES
        # ====================================================

        templates = get_face_templates(
            customer_id,
            external_user_id
        )

        if not templates:

            print()
            print("❌ NO FACE TEMPLATES")

            return {
                "verified": False,
                "reason": "NO_BIOMETRIC_DATA",
                "similarity": 0.0,
                "pad_confidence": 0.0,
                "samples": 0,
            }

        print()
        print(
            f"Loaded {len(templates)} face templates."
        )

        # ====================================================
        # CAMERA SESSION
        # ====================================================

        session = CameraSession(
            camera_index=CAMERA_INDEX,
            max_duration=MAX_SESSION_TIME,
            window_name="Face Verification",
        )

        final_result = {
            "verified": False,
            "reason": "CANCELLED",
            "similarity": 0.0,
            "pad_confidence": 0.0,
            "samples": 0,
        }

        # ====================================================
        # TEMPORAL SAMPLE STORAGE
        # ====================================================

        similarity_scores = []

        pad_scores = []

        try:

            # ------------------------------------------------
            # START CAMERA
            # ------------------------------------------------

            try:

                session.start()

            except RuntimeError:

                print()
                print("❌ Could not open camera.")

                final_result = {
                    "verified": False,
                    "reason": "CAMERA_ERROR",
                    "similarity": 0.0,
                    "pad_confidence": 0.0,
                    "samples": 0,
                }

                return final_result

            print()
            print(
                f"Verification session started "
                f"({MAX_SESSION_TIME:.0f} second timeout)."
            )

            print(
                f"Collecting {REQUIRED_SAMPLES} "
                "valid face samples."
            )

            print("Look at the camera.")
            print("Press Q to cancel.")
            print()

            # =================================================
            # MAIN VERIFICATION LOOP
            # =================================================

            while not session.timed_out():

                # ---------------------------------------------
                # READ FRAME
                # ---------------------------------------------

                frame = session.get_frame()

                if frame is None:

                    final_result = {
                        "verified": False,
                        "reason": "CAMERA_READ_ERROR",
                        "similarity": 0.0,
                        "pad_confidence": 0.0,
                        "samples": len(similarity_scores),
                    }

                    break

                # ---------------------------------------------
                # DEFAULT UI STATE
                # ---------------------------------------------

                status = "POSITION YOUR FACE"

                status_color = (
                    255,
                    255,
                    255
                )

                current_similarity = None
                current_pad_confidence = 0.0

                # =================================================
                # FACE DETECTION
                # =================================================

                faces = self.face_engine.detect_faces(
                    frame
                )

                # =================================================
                # NO FACE
                # =================================================

                if len(faces) == 0:

                    status = "LOOKING FOR FACE"

                    status_color = (
                        0,
                        255,
                        255
                    )

                # =================================================
                # MULTIPLE FACES
                # =================================================

                elif len(faces) > 1:

                    status = "ONLY ONE FACE ALLOWED"

                    status_color = (
                        0,
                        0,
                        255
                    )

                    for detected_face in faces:

                        bbox = (
                            detected_face.bbox
                            .astype(int)
                        )

                        x1, y1, x2, y2 = bbox

                        self.draw_face_box(
                            frame,
                            (x1, y1, x2, y2),
                            (0, 0, 255),
                            "MULTIPLE FACES"
                        )

                # =================================================
                # EXACTLY ONE FACE
                # =================================================

                else:

                    face = faces[0]

                    bbox = (
                        face.bbox
                        .astype(int)
                    )

                    x1, y1, x2, y2 = bbox

                    # ---------------------------------------------
                    # PAD BOUNDING BOX
                    # ---------------------------------------------

                    pad_bbox = [
                        int(x1),
                        int(y1),
                        int(x2 - x1),
                        int(y2 - y1)
                    ]

                    # ---------------------------------------------
                    # PRESENTATION ATTACK DETECTION
                    # ---------------------------------------------

                    pad_result = self.pad.check(
                        frame,
                        pad_bbox
                    )

                    pad_label = pad_result[
                        "label"
                    ]

                    pad_confidence = pad_result[
                        "confidence"
                    ]

                    current_pad_confidence = (
                        pad_confidence
                    )

                    # =================================================
                    # SPOOF
                    # =================================================

                    if pad_label == "SPOOF":

                        status = (
                            f"SPOOF DETECTED "
                            f"{pad_confidence * 100:.1f}%"
                        )

                        status_color = (
                            0,
                            0,
                            255
                        )

                        self.draw_face_box(
                            frame,
                            (x1, y1, x2, y2),
                            status_color,
                            "SPOOF"
                        )

                        final_result = {
                            "verified": False,
                            "reason": "SPOOF_DETECTED",
                            "similarity": 0.0,
                            "pad_confidence": pad_confidence,
                            "samples": len(similarity_scores),
                        }

                    # =================================================
                    # PAD NOT YET REAL
                    # =================================================

                    elif pad_label != "REAL":

                        status = (
                            f"CHECKING LIVENESS "
                            f"{pad_confidence * 100:.1f}%"
                        )

                        status_color = (
                            0,
                            255,
                            255
                        )

                        self.draw_face_box(
                            frame,
                            (x1, y1, x2, y2),
                            status_color,
                            "CHECKING"
                        )

                    # =================================================
                    # REAL FACE
                    # =================================================

                    else:

                        status = "LIVENESS PASSED"

                        status_color = (
                            0,
                            255,
                            0
                        )

                        self.draw_face_box(
                            frame,
                            (x1, y1, x2, y2),
                            status_color,
                            "LIVE"
                        )

                        # ---------------------------------------------
                        # GENERATE LIVE EMBEDDING
                        # ---------------------------------------------

                        embedding = (
                            self.face_engine
                            .get_embedding(face)
                        )

                        if embedding is None:

                            status = "EMBEDDING ERROR"

                            status_color = (
                                0,
                                0,
                                255
                            )

                        else:

                            # -----------------------------------------
                            # COMPARE CURRENT FRAME
                            # -----------------------------------------

                            current_similarity = (
                                self.compare_with_templates(
                                    embedding,
                                    templates
                                )
                            )

                            # -----------------------------------------
                            # STORE SAMPLE
                            # -----------------------------------------

                            similarity_scores.append(
                                current_similarity
                            )

                            pad_scores.append(
                                current_pad_confidence
                            )

                            # -----------------------------------------
                            # SAMPLE STATUS
                            # -----------------------------------------

                            sample_count = len(
                                similarity_scores
                            )

                            status = (
                                f"VERIFYING IDENTITY "
                                f"{sample_count}/{REQUIRED_SAMPLES}"
                            )

                            status_color = (
                                0,
                                255,
                                255
                            )

                            # -----------------------------------------
                            # CURRENT SIMILARITY
                            # -----------------------------------------

                            cv2.putText(
                                frame,
                                (
                                    f"Similarity: "
                                    f"{current_similarity:.3f}"
                                ),
                                (25, 105),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.65,
                                (255, 255, 255),
                                2,
                                cv2.LINE_AA
                            )

                            # -----------------------------------------
                            # COLLECTED ENOUGH SAMPLES
                            # -----------------------------------------

                            if (
                                sample_count
                                >= REQUIRED_SAMPLES
                            ):

                                # =====================================
                                # MEDIAN SIMILARITY
                                # =====================================

                                median_similarity = float(
                                    np.median(
                                        similarity_scores
                                    )
                                )

                                # =====================================
                                # MEDIAN PAD CONFIDENCE
                                # =====================================

                                median_pad_confidence = float(
                                    np.median(
                                        pad_scores
                                    )
                                )

                                # =====================================
                                # FINAL DECISION
                                # =====================================

                                if (
                                    median_similarity
                                    >= MATCH_THRESHOLD
                                ):

                                    status = "VERIFIED"

                                    status_color = (
                                        0,
                                        255,
                                        0
                                    )

                                    final_result = {
                                        "verified": True,
                                        "reason": "MATCH",
                                        "similarity": median_similarity,
                                        "pad_confidence": median_pad_confidence,
                                        "samples": sample_count,
                                    }

                                else:

                                    status = "FACE NOT MATCHED"

                                    status_color = (
                                        0,
                                        0,
                                        255
                                    )

                                    final_result = {
                                        "verified": False,
                                        "reason": "FACE_NOT_MATCHED",
                                        "similarity": median_similarity,
                                        "pad_confidence": median_pad_confidence,
                                        "samples": sample_count,
                                    }

                # =================================================
                # PROFESSIONAL UI
                # =================================================

                overlay = frame.copy()

                cv2.rectangle(
                    overlay,
                    (0, 0),
                    (frame.shape[1], 145),
                    (0, 0, 0),
                    -1
                )

                frame = cv2.addWeighted(
                    overlay,
                    0.55,
                    frame,
                    0.45,
                    0
                )

                # ---------------------------------------------
                # PRODUCT TITLE
                # ---------------------------------------------

                cv2.putText(
                    frame,
                    "FACE AUTHENTICATION",
                    (25, 32),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

                # ---------------------------------------------
                # STATUS
                # ---------------------------------------------

                cv2.putText(
                    frame,
                    status,
                    (25, 68),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.68,
                    status_color,
                    2,
                    cv2.LINE_AA
                )

                # ---------------------------------------------
                # SAMPLE COUNTER
                # ---------------------------------------------

                sample_text = (
                    f"Samples: "
                    f"{len(similarity_scores)}/"
                    f"{REQUIRED_SAMPLES}"
                )

                cv2.putText(
                    frame,
                    sample_text,
                    (25, 102),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (230, 230, 230),
                    1,
                    cv2.LINE_AA
                )

                # ---------------------------------------------
                # TIMER
                # ---------------------------------------------

                remaining = session.remaining_time()

                timer_text = (
                    f"{remaining:.1f}s"
                )

                cv2.putText(
                    frame,
                    timer_text,
                    (
                        frame.shape[1] - 100,
                        35
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

                # ---------------------------------------------
                # INSTRUCTIONS
                # ---------------------------------------------

                cv2.putText(
                    frame,
                    "Look at the camera",
                    (
                        25,
                        frame.shape[0] - 45
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (230, 230, 230),
                    1,
                    cv2.LINE_AA
                )

                cv2.putText(
                    frame,
                    "Q = CANCEL",
                    (
                        frame.shape[1] - 150,
                        frame.shape[0] - 20
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (220, 220, 220),
                    1,
                    cv2.LINE_AA
                )

                # =================================================
                # DISPLAY
                # =================================================

                cv2.imshow(
                    "Face Verification",
                    frame
                )

                # =================================================
                # FINAL DECISION
                # =================================================

                if (
                    final_result["reason"]
                    in (
                        "MATCH",
                        "FACE_NOT_MATCHED",
                        "SPOOF_DETECTED"
                    )
                ):

                    cv2.waitKey(1200)

                    break

                # =================================================
                # CANCEL
                # =================================================

                if session.key_pressed():

                    final_result = {
                        "verified": False,
                        "reason": "CANCELLED",
                        "similarity": (
                            float(
                                np.median(
                                    similarity_scores
                                )
                            )
                            if similarity_scores
                            else 0.0
                        ),
                        "pad_confidence": (
                            float(
                                np.median(
                                    pad_scores
                                )
                            )
                            if pad_scores
                            else 0.0
                        ),
                        "samples": len(
                            similarity_scores
                        ),
                    }

                    break

            # =====================================================
            # TIMEOUT
            # =====================================================

            if (
                final_result["reason"] == "CANCELLED"
                and session.timed_out()
            ):

                final_result = {
                    "verified": False,
                    "reason": "TIMEOUT",
                    "similarity": (
                        float(
                            np.median(
                                similarity_scores
                            )
                        )
                        if similarity_scores
                        else 0.0
                    ),
                    "pad_confidence": (
                        float(
                            np.median(
                                pad_scores
                            )
                        )
                        if pad_scores
                        else 0.0
                    ),
                    "samples": len(
                        similarity_scores
                    ),
                }

                print()
                print(
                    "⏱️ Verification session timed out."
                )

        finally:

            # =================================================
            # ALWAYS CLOSE CAMERA
            # =================================================

            session.stop()

        # ========================================================
        # RESULT
        # ========================================================

        print()
        print("=" * 60)
        print("VERIFICATION RESULT")
        print("=" * 60)

        print(
            f"Verified       : "
            f"{final_result['verified']}"
        )

        print(
            f"Reason         : "
            f"{final_result['reason']}"
        )

        print(
            f"Similarity     : "
            f"{final_result['similarity']:.4f}"
        )

        print(
            f"PAD Confidence : "
            f"{final_result['pad_confidence']:.4f}"
        )

        print(
            f"Samples        : "
            f"{final_result['samples']}"
        )

        print("=" * 60)

        return final_result


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    verifier = VerificationEngine()

    result = verifier.verify(
        customer_id="DEMO_COMPANY",
        external_user_id="USER_001"
    )

    print()
    print("Returned result:")
    print(result)