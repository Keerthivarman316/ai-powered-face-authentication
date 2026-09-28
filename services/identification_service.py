import cv2
import numpy as np

from app.face_engine import FaceEngine
from app.pad_engine import PAD

from storage.database import (
    initialize_database,
    get_connection,
    get_face_templates,
)


# ============================================================
# CONFIGURATION
# ============================================================

# DEVELOPMENT ONLY.
#
# This threshold has NOT been scientifically calibrated
# for production use yet.
IDENTIFICATION_THRESHOLD = 0.60


# ============================================================
# IDENTIFICATION SERVICE
# ============================================================

class IdentificationService:

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING IDENTIFICATION SERVICE")
        print("=" * 60)

        initialize_database()

        self.face_engine = FaceEngine()

        self.pad = PAD()

        print("=" * 60)
        print("IDENTIFICATION SERVICE READY")
        print("=" * 60)

    # ========================================================
    # COSINE SIMILARITY
    # ========================================================

    @staticmethod
    def cosine_similarity(
        embedding_a,
        embedding_b
    ):

        embedding_a = np.asarray(
            embedding_a,
            dtype=np.float32
        )

        embedding_b = np.asarray(
            embedding_b,
            dtype=np.float32
        )

        norm_a = np.linalg.norm(
            embedding_a
        )

        norm_b = np.linalg.norm(
            embedding_b
        )

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(
            np.dot(
                embedding_a,
                embedding_b
            )
            /
            (
                norm_a
                * norm_b
            )
        )

    # ========================================================
    # GET ALL ACTIVE USERS FOR CUSTOMER
    # ========================================================

    @staticmethod
    def get_active_users(
        customer_id: str
    ):

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                external_user_id
            FROM users
            WHERE customer_id = ?
              AND active = 1
            ORDER BY id
            """,
            (
                customer_id,
            )
        )

        rows = cursor.fetchall()

        connection.close()

        users = []

        for row in rows:

            users.append(
                {
                    "id": row[0],
                    "external_user_id": row[1],
                }
            )

        return users

    # ========================================================
    # COMPARE AGAINST ONE USER
    # ========================================================

    def compare_user(
        self,
        embedding,
        customer_id,
        external_user_id
    ):

        templates = get_face_templates(
            customer_id,
            external_user_id
        )

        if not templates:
            return None

        best_similarity = -1.0

        for template in templates:

            similarity = (
                self.cosine_similarity(
                    embedding,
                    template
                )
            )

            if similarity > best_similarity:

                best_similarity = similarity

        return float(
            best_similarity
        )

    # ========================================================
    # IMAGE DECODING
    # ========================================================

    @staticmethod
    def decode_image(
        image_bytes
    ):

        if not image_bytes:
            return None

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        return frame

    # ========================================================
    # IDENTIFY IMAGE
    # ========================================================

    def identify_image(
        self,
        customer_id: str,
        image_bytes: bytes
    ):

        # ====================================================
        # INPUT VALIDATION
        # ====================================================

        if not customer_id:

            return {
                "identified": False,
                "reason": "INVALID_CUSTOMER_ID",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }

        # ====================================================
        # CHECK CUSTOMER USERS
        # ====================================================

        users = self.get_active_users(
            customer_id
        )

        if not users:

            return {
                "identified": False,
                "reason": "NO_ENROLLED_USERS",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }

        # ====================================================
        # DECODE IMAGE
        # ====================================================

        frame = self.decode_image(
            image_bytes
        )

        if frame is None:

            return {
                "identified": False,
                "reason": "INVALID_IMAGE",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }

        # ====================================================
        # FACE DETECTION
        # ====================================================

        faces = self.face_engine.detect_faces(
            frame
        )

        if len(faces) == 0:

            return {
                "identified": False,
                "reason": "NO_FACE",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }

        if len(faces) > 1:

            return {
                "identified": False,
                "reason": "MULTIPLE_FACES",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }

        # ====================================================
        # SINGLE FACE
        # ====================================================

        face = faces[0]

        bbox = (
            face.bbox
            .astype(int)
        )

        x1, y1, x2, y2 = bbox

        pad_bbox = [
            int(x1),
            int(y1),
            int(x2 - x1),
            int(y2 - y1),
        ]

        # ====================================================
        # PAD
        # ====================================================

        pad_result = self.pad.check(
            frame,
            pad_bbox
        )

        pad_label = pad_result[
            "label"
        ]

        pad_confidence = float(
            pad_result["confidence"]
        )

        pad_response = {
            "label": pad_label,
            "confidence": pad_confidence,
        }

        if pad_label == "SPOOF":

            return {
                "identified": False,
                "reason": "SPOOF_DETECTED",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": pad_response,
            }

        if pad_label != "REAL":

            return {
                "identified": False,
                "reason": "PAD_UNKNOWN",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": pad_response,
            }

        # ====================================================
        # LIVE EMBEDDING
        # ====================================================

        embedding = (
            self.face_engine
            .get_embedding(face)
        )

        if embedding is None:

            return {
                "identified": False,
                "reason": "EMBEDDING_FAILED",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": pad_response,
            }

        # ====================================================
        # SEARCH ALL USERS
        # ====================================================

        best_user_id = None

        best_similarity = -1.0

        for user in users:

            external_user_id = (
                user["external_user_id"]
            )

            similarity = (
                self.compare_user(
                    embedding,
                    customer_id,
                    external_user_id
                )
            )

            if similarity is None:
                continue

            if similarity > best_similarity:

                best_similarity = similarity

                best_user_id = (
                    external_user_id
                )

        # ====================================================
        # NO USABLE MATCH
        # ====================================================

        if best_user_id is None:

            return {
                "identified": False,
                "reason": "NO_BIOMETRIC_TEMPLATES",
                "external_user_id": None,
                "similarity": 0.0,
                "pad": pad_response,
            }

        # ====================================================
        # THRESHOLD
        # ====================================================

        if best_similarity < IDENTIFICATION_THRESHOLD:

            return {
                "identified": False,
                "reason": "NO_MATCH",
                "external_user_id": None,
                "similarity": float(
                    best_similarity
                ),
                "pad": pad_response,
            }

        # ====================================================
        # SUCCESS
        # ====================================================

        return {
            "identified": True,
            "reason": "IDENTIFICATION_SUCCESS",
            "external_user_id": best_user_id,
            "similarity": float(
                best_similarity
            ),
            "pad": pad_response,
        }