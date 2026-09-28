import cv2
import numpy as np

from app.face_engine import FaceEngine
from app.pad_engine import PAD

from storage.database import (
    initialize_database,
    get_user,
    get_face_templates,
    create_user_with_templates,
)


# ============================================================
# CONFIGURATION
# ============================================================

# Development threshold.
#
# IMPORTANT:
# This is NOT a production security threshold yet.
# It must be evaluated on representative genuine/impostor
# data before production deployment.

MATCH_THRESHOLD = 0.60


# ============================================================
# AUTHENTICATION SERVICE
# ============================================================

class AuthenticationService:

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING AUTHENTICATION SERVICE")
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
        print("AUTHENTICATION SERVICE READY")
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
                *
                norm_b
            )
        )


    # ========================================================
    # BEST TEMPLATE MATCH
    # ========================================================

    def compare_with_templates(
        self,
        embedding,
        templates
    ):

        if not templates:

            return 0.0

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
    # MULTI-SAMPLE ENROLLMENT
    # ========================================================

    def enroll_images(
        self,
        customer_id: str,
        external_user_id: str,
        images_bytes: list[bytes]
    ):
        """
        Enroll a new user using multiple face images.

        Every image must contain exactly one REAL face.

        All embeddings are stored atomically only after
        every sample passes validation.
        """

        # ====================================================
        # INPUT VALIDATION
        # ====================================================

        if not customer_id:

            return {
                "enrolled": False,
                "reason": "INVALID_CUSTOMER_ID",
                "template_count": 0,
            }

        if not external_user_id:

            return {
                "enrolled": False,
                "reason": "INVALID_EXTERNAL_USER_ID",
                "template_count": 0,
            }

        if not images_bytes:

            return {
                "enrolled": False,
                "reason": "NO_ENROLLMENT_IMAGES",
                "template_count": 0,
            }


        # ====================================================
        # CHECK IF USER ALREADY EXISTS
        # ====================================================

        existing_user = get_user(
            customer_id,
            external_user_id
        )

        if existing_user is not None:

            return {
                "enrolled": False,
                "reason": "USER_ALREADY_EXISTS",
                "template_count": 0,
            }


        # ====================================================
        # PROCESS ALL SAMPLES
        # ====================================================

        embeddings = []

        pad_results = []


        for index, image_bytes in enumerate(
            images_bytes,
            start=1
        ):

            # ------------------------------------------------
            # Decode
            # ------------------------------------------------

            frame = self.decode_image(
                image_bytes
            )

            if frame is None:

                return {
                    "enrolled": False,
                    "reason": "INVALID_IMAGE",
                    "failed_sample": index,
                    "template_count": 0,
                }


            # ------------------------------------------------
            # Face detection
            # ------------------------------------------------

            faces = self.face_engine.detect_faces(
                frame
            )


            if len(faces) == 0:

                return {
                    "enrolled": False,
                    "reason": "NO_FACE",
                    "failed_sample": index,
                    "template_count": 0,
                }


            if len(faces) > 1:

                return {
                    "enrolled": False,
                    "reason": "MULTIPLE_FACES",
                    "failed_sample": index,
                    "template_count": 0,
                }


            # ------------------------------------------------
            # Single face
            # ------------------------------------------------

            face = faces[0]

            bbox = (
                face.bbox
                .astype(int)
            )

            x1, y1, x2, y2 = bbox


            # ------------------------------------------------
            # PAD
            # ------------------------------------------------

            pad_bbox = [
                int(x1),
                int(y1),
                int(x2 - x1),
                int(y2 - y1),
            ]

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

            pad_results.append(
                pad_response
            )


            # ------------------------------------------------
            # SPOOF
            # ------------------------------------------------

            if pad_label == "SPOOF":

                return {
                    "enrolled": False,
                    "reason": "SPOOF_DETECTED",
                    "failed_sample": index,
                    "pad": pad_response,
                    "template_count": 0,
                }


            # ------------------------------------------------
            # PAD UNKNOWN
            # ------------------------------------------------

            if pad_label != "REAL":

                return {
                    "enrolled": False,
                    "reason": "PAD_UNKNOWN",
                    "failed_sample": index,
                    "pad": pad_response,
                    "template_count": 0,
                }


            # ------------------------------------------------
            # Face embedding
            # ------------------------------------------------

            embedding = (
                self.face_engine
                .get_embedding(face)
            )


            if embedding is None:

                return {
                    "enrolled": False,
                    "reason": "EMBEDDING_FAILED",
                    "failed_sample": index,
                    "pad": pad_response,
                    "template_count": 0,
                }


            embeddings.append(
                embedding
            )


        # ====================================================
        # ATOMIC DATABASE ENROLLMENT
        # ====================================================

        try:

            storage_result = (
                create_user_with_templates(
                    customer_id=customer_id,
                    external_user_id=external_user_id,
                    embeddings=embeddings,
                )
            )

        except ValueError as exc:

            return {
                "enrolled": False,
                "reason": str(exc),
                "template_count": 0,
            }

        except Exception:

            return {
                "enrolled": False,
                "reason": "ENROLLMENT_STORAGE_FAILED",
                "template_count": 0,
            }


        # ====================================================
        # SUCCESS
        # ====================================================

        average_pad_confidence = float(
            np.mean([
                result["confidence"]
                for result in pad_results
            ])
        )

        return {
            "enrolled": True,
            "reason": "ENROLLMENT_SUCCESS",
            "user_id": storage_result["user_id"],
            "template_count": storage_result["template_count"],
            "samples": len(embeddings),
            "pad": {
                "label": "REAL",
                "confidence": average_pad_confidence,
            },
        }


    # ========================================================
    # VERIFY IMAGE
    # ========================================================

    def verify_image(
        self,
        customer_id: str,
        external_user_id: str,
        image_bytes: bytes
    ):
        """
        Verify a face image against one
        specific enrolled user.

        This method is API-ready and does not
        access a local camera.
        """

        # ====================================================
        # INPUT VALIDATION
        # ====================================================

        if not customer_id:

            return {
                "verified": False,
                "reason": "INVALID_CUSTOMER_ID",
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }


        if not external_user_id:

            return {
                "verified": False,
                "reason": "INVALID_EXTERNAL_USER_ID",
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }


        # ====================================================
        # CHECK USER
        # ====================================================

        user = get_user(
            customer_id,
            external_user_id
        )

        if user is None:

            return {
                "verified": False,
                "reason": "USER_NOT_FOUND",
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }


        # ====================================================
        # CHECK USER STATUS
        # ====================================================

        if not user["active"]:

            return {
                "verified": False,
                "reason": "USER_INACTIVE",
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }


        # ====================================================
        # GET STORED TEMPLATES
        # ====================================================

        templates = get_face_templates(
            customer_id,
            external_user_id
        )

        if not templates:

            return {
                "verified": False,
                "reason": "NO_FACE_TEMPLATES",
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
                "verified": False,
                "reason": "INVALID_IMAGE",
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
                "verified": False,
                "reason": "NO_FACE",
                "similarity": 0.0,
                "pad": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
            }


        if len(faces) > 1:

            return {
                "verified": False,
                "reason": "MULTIPLE_FACES",
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


        # ====================================================
        # PAD
        # ====================================================

        pad_bbox = [
            int(x1),
            int(y1),
            int(x2 - x1),
            int(y2 - y1),
        ]

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


        # ====================================================
        # SPOOF
        # ====================================================

        if pad_label == "SPOOF":

            return {
                "verified": False,
                "reason": "SPOOF_DETECTED",
                "similarity": 0.0,
                "pad": pad_response,
            }


        # ====================================================
        # PAD UNKNOWN
        # ====================================================

        if pad_label != "REAL":

            return {
                "verified": False,
                "reason": "PAD_UNKNOWN",
                "similarity": 0.0,
                "pad": pad_response,
            }


        # ====================================================
        # FACE EMBEDDING
        # ====================================================

        embedding = (
            self.face_engine
            .get_embedding(face)
        )

        if embedding is None:

            return {
                "verified": False,
                "reason": "EMBEDDING_FAILED",
                "similarity": 0.0,
                "pad": pad_response,
            }


        # ====================================================
        # TEMPLATE MATCHING
        # ====================================================

        similarity = (
            self.compare_with_templates(
                embedding,
                templates
            )
        )


        # ====================================================
        # MATCH
        # ====================================================

        if similarity >= MATCH_THRESHOLD:

            return {
                "verified": True,
                "reason": "MATCH",
                "similarity": similarity,
                "pad": pad_response,
            }


        # ====================================================
        # NO MATCH
        # ====================================================

        return {
            "verified": False,
            "reason": "FACE_NOT_MATCHED",
            "similarity": similarity,
            "pad": pad_response,
        }