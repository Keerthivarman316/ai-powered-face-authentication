import cv2
import time


class CameraSession:
    """
    Handles the webcam session for face authentication.

    The session remains active until:
    - the caller finishes successfully,
    - the caller reports a failure,
    - the user presses Q,
    - or the maximum session duration is reached.
    """

    def __init__(
        self,
        camera_index=0,
        max_duration=10.0,
        window_name="Face Authentication",
    ):
        self.camera_index = camera_index
        self.max_duration = max_duration
        self.window_name = window_name

        self.cap = None
        self.start_time = None

    def start(self):
        """Open the camera and start the session."""

        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError("Unable to open camera.")

        self.start_time = time.monotonic()

    def get_frame(self):
        """Read and return the current camera frame."""

        if self.cap is None:
            raise RuntimeError("Camera session has not been started.")

        success, frame = self.cap.read()

        if not success:
            return None

        return frame

    def elapsed_time(self):
        """Return elapsed session time in seconds."""

        if self.start_time is None:
            return 0.0

        return time.monotonic() - self.start_time

    def remaining_time(self):
        """Return remaining session time."""

        remaining = self.max_duration - self.elapsed_time()

        return max(0.0, remaining)

    def timed_out(self):
        """Return True if the maximum session duration is reached."""

        return self.elapsed_time() >= self.max_duration

    def show(self, frame, status="Initializing..."):
        """
        Display the current frame with professional status information.
        """

        display = frame.copy()

        height, width = display.shape[:2]

        # Dark translucent-style top panel
        overlay = display.copy()

        cv2.rectangle(
            overlay,
            (0, 0),
            (width, 95),
            (0, 0, 0),
            -1,
        )

        display = cv2.addWeighted(
            overlay,
            0.65,
            display,
            0.35,
            0,
        )

        # Product title
        cv2.putText(
            display,
            "FACE AUTHENTICATION",
            (25, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Current status
        cv2.putText(
            display,
            status,
            (25, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Countdown
        remaining = self.remaining_time()

        timer_text = f"{remaining:.1f}s"

        cv2.putText(
            display,
            timer_text,
            (width - 100, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            display,
            "Press Q to cancel",
            (width - 190, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        cv2.imshow(self.window_name, display)

    def key_pressed(self):
        """Check whether the user pressed Q."""

        key = cv2.waitKey(1) & 0xFF

        return key == ord("q")

    def stop(self):
        """Cleanly close the camera session."""

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        cv2.destroyAllWindows()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()