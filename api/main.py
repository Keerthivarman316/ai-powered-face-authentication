from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware

from services.authentication_service import (
    AuthenticationService,
    MATCH_THRESHOLD,
)

from storage.database import (
    get_connection,
    get_face_templates,
)

from api.security import (
    validate_api_key,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Face Authentication API",
    version="1.0.0",
    description=(
        "Biometric face authentication service "
        "with presentation attack detection."
    ),
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTHENTICATION SERVICE
# ============================================================

auth_service = AuthenticationService()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "service": "face-authentication",
    }


# ============================================================
# FACE ENROLLMENT
# ============================================================

@app.post("/enroll")
async def enroll_face(
    customer_id: str = Form(...),
    external_user_id: str = Form(...),
    images: list[UploadFile] = File(...),
    _: bool = Depends(validate_api_key),
):
    """
    Enroll a new user using multiple face images.

    Expected:
        images = sample_1.jpg
                 sample_2.jpg
                 sample_3.jpg
                 sample_4.jpg
                 sample_5.jpg

    The authentication service performs:
        - image decoding
        - face detection
        - single-face validation
        - PAD
        - embedding extraction
        - atomic database storage
    """

    # --------------------------------------------------------
    # Read all uploaded images
    # --------------------------------------------------------

    image_bytes_list = []

    for image in images:

        image_bytes = await image.read()

        image_bytes_list.append(
            image_bytes
        )

    # --------------------------------------------------------
    # Enroll all samples
    # --------------------------------------------------------

    result = auth_service.enroll_images(
        customer_id=customer_id,
        external_user_id=external_user_id,
        images_bytes=image_bytes_list,
    )

    return result


# ============================================================
# FACE VERIFICATION
# ============================================================

@app.post("/verify")
async def verify_face(
    customer_id: str = Form(...),
    external_user_id: str = Form(...),
    image: UploadFile = File(...),
    _: bool = Depends(validate_api_key),
):
    """
    Verify an uploaded face against
    one specific enrolled user.
    """

    image_bytes = await image.read()

    result = auth_service.verify_image(
        customer_id=customer_id,
        external_user_id=external_user_id,
        image_bytes=image_bytes,
    )

    return result


# ============================================================
# FACE IDENTIFICATION
# ============================================================

@app.post("/identify")
async def identify_face(
    customer_id: str = Form(...),
    image: UploadFile = File(...),
    _: bool = Depends(validate_api_key),
):
    """
    Identify an unknown face among all active
    users belonging to the specified customer.

    Flow:

        image
          ↓
        decode
          ↓
        face detection
          ↓
        exactly one face
          ↓
        PAD
          ↓
        REAL
          ↓
        embedding
          ↓
        compare against all enrolled users
          ↓
        best match
          ↓
        identified / no match
    """

    # ========================================================
    # READ IMAGE
    # ========================================================

    image_bytes = await image.read()

    if not image_bytes:

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


    # ========================================================
    # DECODE IMAGE
    # ========================================================

    frame = auth_service.decode_image(
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


    # ========================================================
    # FACE DETECTION
    # ========================================================

    faces = (
        auth_service
        .face_engine
        .detect_faces(frame)
    )


    # ========================================================
    # NO FACE
    # ========================================================

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


    # ========================================================
    # MULTIPLE FACES
    # ========================================================

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


    # ========================================================
    # SINGLE FACE
    # ========================================================

    face = faces[0]


    # ========================================================
    # FACE BOUNDING BOX
    # ========================================================

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


    # ========================================================
    # PRESENTATION ATTACK DETECTION
    # ========================================================

    pad_result = (
        auth_service
        .pad
        .check(
            frame,
            pad_bbox
        )
    )


    pad_label = (
        pad_result["label"]
    )

    pad_confidence = float(
        pad_result["confidence"]
    )


    pad_response = {
        "label": pad_label,
        "confidence": pad_confidence,
    }


    # ========================================================
    # SPOOF
    # ========================================================

    if pad_label == "SPOOF":

        return {
            "identified": False,
            "reason": "SPOOF_DETECTED",
            "external_user_id": None,
            "similarity": 0.0,
            "pad": pad_response,
        }


    # ========================================================
    # PAD UNKNOWN
    # ========================================================

    if pad_label != "REAL":

        return {
            "identified": False,
            "reason": "PAD_UNKNOWN",
            "external_user_id": None,
            "similarity": 0.0,
            "pad": pad_response,
        }


    # ========================================================
    # GET LIVE EMBEDDING
    # ========================================================

    embedding = (
        auth_service
        .face_engine
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


    # ========================================================
    # GET ALL ACTIVE USERS
    # ========================================================

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

    users = cursor.fetchall()

    connection.close()


    # ========================================================
    # NO USERS
    # ========================================================

    if not users:

        return {
            "identified": False,
            "reason": "NO_ENROLLED_USERS",
            "external_user_id": None,
            "similarity": 0.0,
            "pad": pad_response,
        }


    # ========================================================
    # FIND BEST MATCH
    # ========================================================

    best_user_id = None

    best_similarity = -1.0


    for user_id, external_user_id in users:

        templates = (
            get_face_templates(
                customer_id,
                external_user_id
            )
        )


        if not templates:
            continue


        similarity = (
            auth_service
            .compare_with_templates(
                embedding,
                templates
            )
        )


        if similarity > best_similarity:

            best_similarity = similarity

            best_user_id = (
                external_user_id
            )


    # ========================================================
    # NO TEMPLATES
    # ========================================================

    if best_user_id is None:

        return {
            "identified": False,
            "reason": "NO_FACE_TEMPLATES",
            "external_user_id": None,
            "similarity": 0.0,
            "pad": pad_response,
        }


    # ========================================================
    # CHECK MATCH THRESHOLD
    # ========================================================

    identified = (
        best_similarity
        >= MATCH_THRESHOLD
    )


    # ========================================================
    # IDENTIFIED
    # ========================================================

    if identified:

        return {
            "identified": True,
            "reason": "IDENTIFICATION_SUCCESS",
            "external_user_id": best_user_id,
            "similarity": float(
                best_similarity
            ),
            "pad": pad_response,
        }


    # ========================================================
    # NO MATCH
    # ========================================================

    return {
        "identified": False,
        "reason": "NO_MATCH",
        "external_user_id": None,
        "similarity": float(
            best_similarity
        ),
        "pad": pad_response,
    }