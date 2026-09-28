import cv2
import os
import sys
import time
import requests


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )


# ============================================================
# LOCAL ENGINES
# ============================================================

from app.face_engine import FaceEngine
from app.pad_engine import PAD


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = (
    "http://127.0.0.1:8000/identify"
)

API_KEY = os.getenv(
    "FACE_AUTH_API_KEY",
    "faceauth-dev-2026-rithvik-9f7k2x"
)

CAMERA_INDEX = 1

REQUIRED_SAMPLES = 5

CAPTURE_INTERVAL = 0.8

JPEG_QUALITY = 90

WINDOW_NAME = "Face Identification"


# ============================================================
# CAMERA IDENTIFICATION
# ============================================================

def identify_from_camera(
    customer_id: str
):

    print()
    print("=" * 60)
    print("CAMERA FACE IDENTIFICATION")
    print("=" * 60)

    print(
        f"Customer ID : {customer_id}"
    )

    print()
    print(
        "Look at the camera."
    )

    print(
        f"Collecting {REQUIRED_SAMPLES} "
        "live samples."
    )

    print(
        "Press Q to cancel."
    )

    print("=" * 60)


    # ========================================================
    # INITIALIZE ENGINES
    # ========================================================

    print()
    print("Loading face engine...")

    face_engine = FaceEngine()

    print("Loading PAD engine...")

    pad_engine = PAD()

    # --------------------------------------------------------
    # IMPORTANT:
    # Use the exact same Haar Cascade detector used by the
    # proven standalone MiniFASNet PAD webcam test.
    #
    # This keeps the PAD face crop consistent with the working
    # spoof-detection pipeline.
    # --------------------------------------------------------

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    pad_face_detector = cv2.CascadeClassifier(
        cascade_path
    )

    if pad_face_detector.empty():

        print()
        print(
            "❌ Could not load Haar Cascade for PAD."
        )

        return

    print("Haar Cascade PAD detector ready.")
    print("Engines ready.")


    # ========================================================
    # OPEN CAMERA
    # ========================================================

    cap = cv2.VideoCapture(
        CAMERA_INDEX
    )

    if not cap.isOpened():

        print()
        print(
            "❌ Could not open camera."
        )

        return


    # ========================================================
    # STATE
    # ========================================================

    sample_count = 0

    last_capture_time = 0.0

    results = []

    final_status = (
        "LOOK AT CAMERA"
    )

    status_color = (
        0,
        255,
        255
    )

    current_pad_label = "UNKNOWN"

    current_pad_confidence = 0.0

    current_similarity = 0.0

    current_user = None

    session_failed = False

    spoof_detected = False


    # ========================================================
    # CAMERA LOOP
    # ========================================================

    try:

        while True:

            # ------------------------------------------------
            # READ CAMERA
            # ------------------------------------------------

            ret, frame = cap.read()

            if not ret:

                print()
                print(
                    "❌ Failed to read camera frame."
                )

                session_failed = True

                break


            # ------------------------------------------------
            # PAD FACE DETECTION
            # ------------------------------------------------
            #
            # IMPORTANT:
            #
            # The proven standalone webcam_pad.py uses:
            #
            # Haar Cascade
            #       ↓
            # [x, y, width, height]
            #       ↓
            # MiniFASNet PAD
            #
            # We intentionally use that same pipeline here.
            #
            # InsightFace is still initialized above and remains
            # available for the identity/embedding architecture.
            #
            # ------------------------------------------------

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            pad_faces = (
                pad_face_detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(80, 80)
                )
            )


            # =================================================
            # NO FACE
            # =================================================

            if len(pad_faces) == 0:

                final_status = (
                    "NO FACE"
                )

                status_color = (
                    0,
                    255,
                    255
                )

                current_pad_label = (
                    "UNKNOWN"
                )

                current_pad_confidence = 0.0


            # =================================================
            # MULTIPLE FACES
            # =================================================

            elif len(pad_faces) > 1:

                final_status = (
                    "ONLY ONE FACE ALLOWED"
                )

                status_color = (
                    0,
                    0,
                    255
                )

                current_pad_label = (
                    "UNKNOWN"
                )

                current_pad_confidence = 0.0


            # =================================================
            # EXACTLY ONE FACE
            # =================================================

            else:

                # ------------------------------------------------
                # EXACT SAME BBOX FORMAT AS THE WORKING
                # STANDALONE PAD TEST:
                #
                # [x, y, width, height]
                # ------------------------------------------------

                x, y, w, h = pad_faces[0]

                x1 = int(x)

                y1 = int(y)

                x2 = int(x + w)

                y2 = int(y + h)

                pad_bbox = [
                    int(x),
                    int(y),
                    int(w),
                    int(h)
                ]


                # --------------------------------------------
                # ACTUAL PAD ENGINE
                # --------------------------------------------

                pad_result = (
                    pad_engine.check(
                        frame,
                        pad_bbox
                    )
                )

                current_pad_label = (
                    pad_result["label"]
                )

                current_pad_confidence = float(
                    pad_result["confidence"]
                )


                # =================================================
                # SPOOF
                # =================================================

                if current_pad_label == "SPOOF":

                    final_status = (
                        "SPOOF DETECTED - REJECTED"
                    )

                    status_color = (
                        0,
                        0,
                        255
                    )

                    spoof_detected = True


                    # Draw face box

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        status_color,
                        3
                    )


                    # ------------------------------------------------
                    # DISPLAY
                    # ------------------------------------------------

                    cv2.putText(
                        frame,
                        (
                            f"PAD: SPOOF "
                            f"{current_pad_confidence * 100:.1f}%"
                        ),
                        (30, 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        status_color,
                        2
                    )

                    cv2.putText(
                        frame,
                        (
                            "PRESENTATION ATTACK"
                        ),
                        (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        status_color,
                        2
                    )

                    cv2.putText(
                        frame,
                        (
                            "ACCESS REJECTED"
                        ),
                        (30, 115),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        status_color,
                        2
                    )

                    cv2.putText(
                        frame,
                        "Q = CANCEL",
                        (30, 150),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

                    cv2.imshow(
                        WINDOW_NAME,
                        frame
                    )

                    cv2.waitKey(1500)

                    print()
                    print(
                        "🚨 PRESENTATION ATTACK DETECTED"
                    )

                    print(
                        "❌ IDENTIFICATION REJECTED"
                    )

                    break


                # =================================================
                # PAD UNKNOWN
                # =================================================

                elif current_pad_label != "REAL":

                    final_status = (
                        "PAD CHECKING"
                    )

                    status_color = (
                        0,
                        255,
                        255
                    )


                # =================================================
                # PAD REAL
                # =================================================

                else:

                    final_status = (
                        f"PAD REAL "
                        f"{current_pad_confidence * 100:.1f}%"
                    )

                    status_color = (
                        0,
                        255,
                        0
                    )


                    # =================================================
                    # CAPTURE SAMPLE
                    # =================================================

                    current_time = time.time()

                    if (
                        current_time
                        - last_capture_time
                        >= CAPTURE_INTERVAL
                        and sample_count
                        < REQUIRED_SAMPLES
                    ):

                        # --------------------------------------------
                        # ENCODE FRAME
                        # --------------------------------------------

                        success, encoded = (
                            cv2.imencode(
                                ".jpg",
                                frame,
                                [
                                    cv2.IMWRITE_JPEG_QUALITY,
                                    JPEG_QUALITY,
                                ],
                            )
                        )

                        if success:

                            image_bytes = (
                                encoded.tobytes()
                            )


                            # ----------------------------------------
                            # SERVER API
                            # ----------------------------------------

                            print()

                            print(
                                f"Sending sample "
                                f"{sample_count + 1}/"
                                f"{REQUIRED_SAMPLES}"
                                f" to authentication API..."
                            )

                            try:

                                response = (
                                    requests.post(
                                        API_URL,
                                        headers={
                                            "X-API-Key":
                                                API_KEY
                                        },
                                        data={
                                            "customer_id":
                                                customer_id
                                        },
                                        files={
                                            "image": (
                                                "frame.jpg",
                                                image_bytes,
                                                "image/jpeg",
                                            )
                                        },
                                        timeout=30,
                                    )
                                )

                            except requests.RequestException as exc:

                                print()
                                print(
                                    "❌ API connection failed."
                                )

                                print(exc)

                                session_failed = True

                                break


                            # ----------------------------------------
                            # API ERROR
                            # ----------------------------------------

                            if response.status_code != 200:

                                print()
                                print(
                                    f"❌ API ERROR "
                                    f"{response.status_code}"
                                )

                                print(
                                    response.text
                                )

                                session_failed = True

                                break


                            # ----------------------------------------
                            # API RESPONSE
                            # ----------------------------------------

                            try:

                                result = (
                                    response.json()
                                )

                            except ValueError:

                                print()
                                print(
                                    "❌ Invalid API response."
                                )

                                session_failed = True

                                break


                            # ----------------------------------------
                            # SERVER PAD
                            # ----------------------------------------

                            server_pad = (
                                result.get(
                                    "pad",
                                    {}
                                )
                            )

                            server_pad_label = (
                                server_pad.get(
                                    "label",
                                    "UNKNOWN"
                                )
                            )

                            server_pad_confidence = float(
                                server_pad.get(
                                    "confidence",
                                    0.0
                                )
                            )

                            identity = (
                                result.get(
                                    "external_user_id"
                                )
                            )

                            identified = bool(
                                result.get(
                                    "identified",
                                    False
                                )
                            )

                            similarity = float(
                                result.get(
                                    "similarity",
                                    0.0
                                )
                            )


                            # ----------------------------------------
                            # PRINT RESULT
                            # ----------------------------------------

                            print(
                                f"Sample "
                                f"{sample_count + 1}/"
                                f"{REQUIRED_SAMPLES}"
                                f" → "
                                f"{identity if identified else 'NO MATCH'}"
                                f" | Similarity: "
                                f"{similarity:.4f}"
                                f" | SERVER PAD: "
                                f"{server_pad_label} "
                                f"{server_pad_confidence:.4f}"
                            )


                            # =================================================
                            # SERVER PAD SPOOF
                            # =================================================

                            if (
                                server_pad_label
                                == "SPOOF"
                            ):

                                print()
                                print(
                                    "🚨 SERVER PAD DETECTED "
                                    "A SPOOF"
                                )

                                print(
                                    "❌ IDENTIFICATION REJECTED"
                                )

                                spoof_detected = True

                                results.append(
                                    result
                                )

                                break


                            # =================================================
                            # SERVER PAD UNKNOWN
                            # =================================================

                            if (
                                server_pad_label
                                != "REAL"
                            ):

                                print()
                                print(
                                    "❌ SERVER PAD "
                                    "DID NOT CONFIRM REAL"
                                )

                                session_failed = True

                                break


                            # =================================================
                            # ACCEPT SAMPLE
                            # =================================================

                            results.append(
                                result
                            )

                            sample_count += 1

                            last_capture_time = (
                                current_time
                            )

                            current_similarity = (
                                similarity
                            )

                            if identified:

                                current_user = (
                                    identity
                                )


                    # =================================================
                    # DRAW FACE BOX
                    # =================================================

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        status_color,
                        2
                    )


            # =================================================
            # LIVE UI
            # =================================================

            cv2.putText(
                frame,
                final_status,
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                status_color,
                2
            )

            cv2.putText(
                frame,
                (
                    f"PAD: "
                    f"{current_pad_label} "
                    f"{current_pad_confidence * 100:.1f}%"
                ),
                (30, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                status_color,
                2
            )

            cv2.putText(
                frame,
                (
                    f"SAMPLES: "
                    f"{sample_count}/"
                    f"{REQUIRED_SAMPLES}"
                ),
                (30, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                (
                    f"SIMILARITY: "
                    f"{current_similarity:.3f}"
                ),
                (30, 145),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Q = CANCEL",
                (30, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )


            # =================================================
            # SHOW PREVIEW
            # =================================================

            cv2.imshow(
                WINDOW_NAME,
                frame
            )


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
                    "Identification cancelled."
                )

                return


            # =================================================
            # FINISHED
            # =================================================

            if (
                sample_count
                >= REQUIRED_SAMPLES
            ):

                break


    finally:

        cap.release()

        cv2.destroyAllWindows()


    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("=" * 60)
    print("FINAL IDENTIFICATION RESULT")
    print("=" * 60)


    # --------------------------------------------------------
    # SPOOF
    # --------------------------------------------------------

    if spoof_detected:

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : SPOOF_DETECTED"
        )

        print(
            "❌ PRESENTATION ATTACK REJECTED"
        )

        print("=" * 60)

        return


    # --------------------------------------------------------
    # SESSION FAILURE
    # --------------------------------------------------------

    if session_failed:

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : SESSION_FAILED"
        )

        print("=" * 60)

        return


    # --------------------------------------------------------
    # SAMPLE COUNT
    # --------------------------------------------------------

    if (
        len(results)
        < REQUIRED_SAMPLES
    ):

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : INCOMPLETE_SESSION"
        )

        print(
            f"Samples    : "
            f"{len(results)}/"
            f"{REQUIRED_SAMPLES}"
        )

        print("=" * 60)

        return


    # ========================================================
    # VERIFY SERVER PAD FOR EVERY SAMPLE
    # ========================================================

    pad_results = []

    for result in results:

        pad = result.get(
            "pad",
            {}
        )

        label = pad.get(
            "label",
            "UNKNOWN"
        )

        pad_results.append(
            label
        )


    if any(
        label != "REAL"
        for label in pad_results
    ):

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : PAD_FAILED"
        )

        print(
            f"PAD RESULTS: "
            f"{pad_results}"
        )

        print("=" * 60)

        return


    # ========================================================
    # IDENTITY VOTING
    # ========================================================

    identity_counts = {}

    identity_similarities = {}


    for result in results:

        if not result.get(
            "identified",
            False
        ):

            continue


        identity = result.get(
            "external_user_id"
        )

        similarity = float(
            result.get(
                "similarity",
                0.0
            )
        )


        if not identity:

            continue


        identity_counts[
            identity
        ] = (
            identity_counts.get(
                identity,
                0
            )
            + 1
        )


        identity_similarities.setdefault(
            identity,
            []
        ).append(
            similarity
        )


    # ========================================================
    # NO MATCH
    # ========================================================

    if not identity_counts:

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : NO_MATCH"
        )

        print(
            "PAD        : ALL REAL"
        )

        print("=" * 60)

        return


    # ========================================================
    # BEST IDENTITY
    # ========================================================

    best_identity = max(
        identity_counts,
        key=identity_counts.get
    )

    best_count = identity_counts[
        best_identity
    ]

    similarities = (
        identity_similarities[
            best_identity
        ]
    )

    average_similarity = (
        sum(similarities)
        /
        len(similarities)
    )


    # ========================================================
    # CONSISTENCY
    # ========================================================

    REQUIRED_CONSISTENT_SAMPLES = 3

    if (
        best_count
        < REQUIRED_CONSISTENT_SAMPLES
    ):

        print()
        print(
            "IDENTIFIED : FALSE"
        )

        print(
            "REASON     : "
            "IDENTITY_NOT_STABLE"
        )

        print(
            f"Best candidate : "
            f"{best_identity}"
        )

        print(
            f"Consistent samples : "
            f"{best_count}/"
            f"{REQUIRED_SAMPLES}"
        )

        print(
            f"Average similarity : "
            f"{average_similarity:.4f}"
        )

        print(
            "PAD        : ALL REAL"
        )

        print("=" * 60)

        return


    # ========================================================
    # SUCCESS
    # ========================================================

    print()
    print(
        "IDENTIFIED : TRUE"
    )

    print(
        f"USER       : "
        f"{best_identity}"
    )

    print(
        f"Samples    : "
        f"{best_count}/"
        f"{REQUIRED_SAMPLES}"
    )

    print(
        f"Average similarity : "
        f"{average_similarity:.4f}"
    )

    print(
        "PAD        : ALL REAL"
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("FACE IDENTIFICATION CLIENT")
    print("=" * 60)

    customer_id = input(
        "Customer ID: "
    ).strip()

    if not customer_id:

        print(
            "❌ Customer ID cannot be empty."
        )

        sys.exit(1)

    identify_from_camera(
        customer_id
    )