from camera_session import CameraSession


def main():

    session = CameraSession(
        camera_index=1,
        max_duration=10.0,
        window_name="Face Authentication Test",
    )

    try:

        session.start()

        print("Camera session started.")
        print("You have 10 seconds.")
        print("Press Q to cancel.")

        while not session.timed_out():

            frame = session.get_frame()

            if frame is None:
                print("Failed to read camera frame.")
                break

            session.show(
                frame,
                status="Position your face inside the frame",
            )

            if session.key_pressed():
                print("Session cancelled by user.")
                break

        else:
            print("Session timed out.")

    finally:

        session.stop()

        print("Camera session closed.")


if __name__ == "__main__":
    main()