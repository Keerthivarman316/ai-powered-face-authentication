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


from app.face_engine import FaceEngine
from app.pad_engine import PAD


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = (
    "http://127.0.0.1:8000/enroll"
)

API_KEY = os.getenv(
    "FACE_AUTH_API_KEY",
    "faceauth-dev-2026-rithvik-9f7k2x"
)

CAMERA_INDEX = 1

REQUIRED_SAMPLES = 5

CAPTURE_INTERVAL = 0.8


# ============================================================
# CAMERA ENROLLMENT
# ============================================================

def enroll_from_camera(
    customer_id: str,
    external_user_id: str,
):

    face_engine = FaceEngine()

    pad = PAD()

    cap = cv2.VideoCapture(
        CAMERA_INDEX
    )

    if not cap.isOpened():

        print(
            "❌ Could not open camera."
        )

        return


    samples = []

    last_capture = 0.0


    print()
    print("=" * 60)
    print("CAMERA FACE ENROLLMENT")
    print("=" * 60)

    print(
        f"Customer ID : "
        f"{customer_id}"
    )

    print(
        f"User ID     : "
        f"{external_user_id}"
    )

    print()
    print(
        "Look at the camera."
    )

    print(
        "Move your head slightly "
        "between captures."
    )

    print(
        "Press Q to cancel."
    )

    print("=" * 60)


    try:

        while (
            len(samples)
            <
            REQUIRED_SAMPLES
        ):

            ret, frame = cap.read()

            if not ret:

                print(
                    "❌ Camera read failed."
                )

                break


            # =================================================
            # FACE DETECTION
            # =================================================

            faces = (
                face_engine
                .detect_faces(frame)
            )


            status = "NO FACE"

            status_color = (
                0,
                255,
                255
            )


            # =================================================
            # MULTIPLE FACES
            # =================================================

            if len(faces) > 1:

                status = (
                    "ONLY ONE FACE ALLOWED"
                )

                status_color = (
                    0,
                    0,
                    255
                )


            # =================================================
            # ONE FACE
            # =================================================

            elif len(faces) == 1:

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
                    int(y2 - y1),
                ]


                # ---------------------------------------------
                # PAD
                # ---------------------------------------------

                pad_result = pad.check(
                    frame,
                    pad_bbox
                )


                pad_label = (
                    pad_result["label"]
                )

                pad_confidence = float(
                    pad_result["confidence"]
                )


                # ---------------------------------------------
                # SPOOF
                # ---------------------------------------------

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


                # ---------------------------------------------
                # PAD UNKNOWN
                # ---------------------------------------------

                elif pad_label != "REAL":

                    status = (
                        "PAD CHECKING"
                    )

                    status_color = (
                        0,
                        255,
                        255
                    )


                # ---------------------------------------------
                # REAL
                # ---------------------------------------------

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


                    now = time.time()


                    # -----------------------------------------
                    # CAPTURE SAMPLE
                    # -----------------------------------------

                    if (
                        now - last_capture
                        >= CAPTURE_INTERVAL
                    ):

                        embedding = (
                            face_engine
                            .get_embedding(face)
                        )


                        if embedding is not None:

                            success, encoded = (
                                cv2.imencode(
                                    ".jpg",
                                    frame,
                                    [
                                        cv2.IMWRITE_JPEG_QUALITY,
                                        95,
                                    ],
                                )
                            )


                            if success:

                                samples.append(
                                    encoded.tobytes()
                                )

                                last_capture = now

                                print(
                                    f"Captured sample "
                                    f"{len(samples)}/"
                                    f"{REQUIRED_SAMPLES}"
                                )


                # -----------------------------------------
                # FACE BOX
                # -----------------------------------------

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    status_color,
                    2
                )


            # =================================================
            # UI
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


            cv2.putText(
                frame,
                (
                    f"SAMPLES: "
                    f"{len(samples)}/"
                    f"{REQUIRED_SAMPLES}"
                ),
                (30, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


            cv2.putText(
                frame,
                "Q = CANCEL",
                (30, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


            cv2.imshow(
                "Face Enrollment",
                frame
            )


            # =================================================
            # CANCEL
            # =================================================

            if (
                cv2.waitKey(1) & 0xFF
                == ord("q")
            ):

                print(
                    "Enrollment cancelled."
                )

                return


    finally:

        cap.release()

        cv2.destroyAllWindows()


    # ========================================================
    # SAMPLE CHECK
    # ========================================================

    if len(samples) != REQUIRED_SAMPLES:

        print(
            "❌ Enrollment cancelled."
        )

        return


    # ========================================================
    # SEND TO API
    # ========================================================

    print()

    print(
        "Sending samples "
        "to authentication API..."
    )


    files = []

    for index, image_bytes in enumerate(
        samples,
        start=1
    ):

        files.append(
            (
                "images",
                (
                    f"sample_{index}.jpg",
                    image_bytes,
                    "image/jpeg",
                ),
            )
        )


    data = {
        "customer_id": customer_id,
        "external_user_id": external_user_id,
    }


    try:

        response = requests.post(
            API_URL,
            headers={
                "X-API-Key": API_KEY,
            },
            data=data,
            files=files,
            timeout=120,
        )


        print()

        print(
            "HTTP:",
            response.status_code
        )

        print(
            response.text
        )


    except requests.RequestException as exc:

        print()

        print(
            "❌ Could not reach "
            "authentication API."
        )

        print(exc)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    customer_id = input(
        "Customer ID: "
    ).strip()


    external_user_id = input(
        "External User ID: "
    ).strip()


    enroll_from_camera(
        customer_id,
        external_user_id
    )