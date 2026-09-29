// Use the same origin in deployment.
// During local development on port 5500, point to the FastAPI server.
const IS_LOCAL_FRONTEND =
    ["localhost", "127.0.0.1"].includes(
        window.location.hostname
    ) &&
    window.location.port === "5500";

const API_BASE_URL =
    IS_LOCAL_FRONTEND
        ? `http://${window.location.hostname}:8000`
        : "";

const FETCH_CREDENTIALS =
    API_BASE_URL
        ? "include"
        : "same-origin";

const ENROLL_API_URL = `${API_BASE_URL}/enroll`;
const IDENTIFY_API_URL = `${API_BASE_URL}/identify`;

const CUSTOMER_ID = "DEMO_COMPANY";

const REQUIRED_SAMPLES = 5;
const CAPTURE_INTERVAL = 800;

let enrollStream = null;
let identifyStream = null;

let enrollmentRunning = false;
let identificationRunning = false;


/* ============================================================
   MODE ELEMENTS
   ============================================================ */

const enrollTab =
    document.getElementById("enrollTab");

const verifyTab =
    document.getElementById("verifyTab");

const enrollMode =
    document.getElementById("enrollMode");

const verifyMode =
    document.getElementById("verifyMode");


/* ============================================================
   MODE SWITCHING
   ============================================================ */

function showMode(mode) {

    if (mode === "enroll") {

        enrollMode.classList.remove("hidden");
        verifyMode.classList.add("hidden");

        enrollTab.classList.add("active");
        verifyTab.classList.remove("active");

        stopIdentifyCamera();

        startEnrollmentCamera();
    }

    if (mode === "verify") {

        enrollMode.classList.add("hidden");
        verifyMode.classList.remove("hidden");

        enrollTab.classList.remove("active");
        verifyTab.classList.add("active");

        stopEnrollmentCamera();

        startIdentificationCamera();
    }
}


/* ============================================================
   CAMERA
   ============================================================ */

async function startCamera(videoElement) {

    try {

        const stream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user",
                    width: {
                        ideal: 1280
                    },
                    height: {
                        ideal: 720
                    }
                },
                audio: false
            });

        videoElement.srcObject = stream;

        await videoElement.play();

        return stream;

    } catch (error) {

        console.error(
            "Camera error:",
            error
        );

        alert(
            "Unable to access the camera.\n\n" +
            "Please allow camera permission and try again."
        );

        return null;
    }
}


function stopStream(stream) {

    if (!stream) {
        return;
    }

    stream
        .getTracks()
        .forEach(track => {
            track.stop();
        });
}


/* ============================================================
   ENROLLMENT CAMERA
   ============================================================ */

async function startEnrollmentCamera() {

    const video =
        document.getElementById(
            "enrollCamera"
        );

    if (!video) {
        return;
    }

    if (enrollStream) {
        return;
    }

    enrollStream =
        await startCamera(video);

    const status =
        document.getElementById(
            "enrollCameraStatus"
        );

    if (enrollStream) {

        status.textContent =
            "CAMERA READY";

    } else {

        status.textContent =
            "CAMERA UNAVAILABLE";
    }
}


function stopEnrollmentCamera() {

    stopStream(enrollStream);

    enrollStream = null;

    const video =
        document.getElementById(
            "enrollCamera"
        );

    if (video) {
        video.srcObject = null;
    }
}


/* ============================================================
   IDENTIFICATION CAMERA
   ============================================================ */

async function startIdentificationCamera() {

    const video =
        document.getElementById(
            "verifyCamera"
        );

    if (!video) {
        return;
    }

    if (identifyStream) {
        return;
    }

    identifyStream =
        await startCamera(video);

    const status =
        document.getElementById(
            "verifyCameraStatus"
        );

    if (identifyStream) {

        status.textContent =
            "CAMERA READY";

    } else {

        status.textContent =
            "CAMERA UNAVAILABLE";
    }
}


function stopIdentifyCamera() {

    stopStream(identifyStream);

    identifyStream = null;

    const video =
        document.getElementById(
            "verifyCamera"
        );

    if (video) {
        video.srcObject = null;
    }
}


/* ============================================================
   CAPTURE FRAME
   ============================================================ */

function captureFrame(
    videoElement,
    canvasElement
) {

    const width =
        videoElement.videoWidth;

    const height =
        videoElement.videoHeight;

    if (!width || !height) {
        return null;
    }

    canvasElement.width = width;
    canvasElement.height = height;

    const context =
        canvasElement.getContext("2d");

    context.drawImage(
        videoElement,
        0,
        0,
        width,
        height
    );

    return canvasElement.toDataURL(
        "image/jpeg",
        0.92
    );
}


function dataURLToBlob(dataURL) {

    const parts =
        dataURL.split(",");

    const mime =
        parts[0]
            .match(/:(.*?);/)[1];

    const binary =
        atob(parts[1]);

    const array =
        new Uint8Array(
            binary.length
        );

    for (
        let i = 0;
        i < binary.length;
        i++
    ) {

        array[i] =
            binary.charCodeAt(i);
    }

    return new Blob(
        [array],
        {
            type: mime
        }
    );
}


/* ============================================================
   STATUS
   ============================================================ */

function setStatus(
    elementId,
    text,
    type = ""
) {

    const element =
        document.getElementById(
            elementId
        );

    if (!element) {
        return;
    }

    element.textContent = text;

    element.classList.remove(
        "waiting",
        "ready",
        "success",
        "failure"
    );

    if (type) {
        element.classList.add(type);
    }
}


/* ============================================================
   ENROLLMENT
   ============================================================ */

async function startEnrollment() {

    if (enrollmentRunning) {
        return;
    }

    const customerId =
        document.getElementById(
            "customerId"
        ).value.trim();

    const externalUserId =
        document.getElementById(
            "externalUserId"
        ).value.trim();


    if (!customerId) {

        alert(
            "Enter Customer ID."
        );

        return;
    }


    if (!externalUserId) {

        alert(
            "Enter External User ID."
        );

        return;
    }


    if (!enrollStream) {

        alert(
            "Camera is not ready."
        );

        return;
    }


    enrollmentRunning = true;


    const startButton =
        document.getElementById(
            "startEnrollment"
        );

    const cancelButton =
        document.getElementById(
            "cancelEnrollment"
        );


    startButton.disabled = true;
    cancelButton.disabled = false;


    const resultPanel =
        document.getElementById(
            "enrollResult"
        );

    resultPanel.classList.add(
        "hidden"
    );


    const video =
        document.getElementById(
            "enrollCamera"
        );

    const canvas =
        document.getElementById(
            "enrollCanvas"
        );

    const progressFill =
        document.getElementById(
            "progressFill"
        );

    const sampleCounter =
        document.getElementById(
            "sampleCounter"
        );

    const sampleStatus =
        document.getElementById(
            "enrollSampleStatus"
        );


    const samples = [];


    progressFill.style.width = "0%";

    sampleCounter.textContent =
        `0 / ${REQUIRED_SAMPLES}`;

    sampleStatus.textContent =
        `0 / ${REQUIRED_SAMPLES}`;


    setStatus(
        "enrollCameraStatus",
        "CAPTURING...",
        "ready"
    );

    setStatus(
        "enrollFaceStatus",
        "Position your face in the frame",
        "ready"
    );

    setStatus(
        "enrollPadStatus",
        "Liveness checked by server",
        "ready"
    );


    for (
        let i = 0;
        i < REQUIRED_SAMPLES;
        i++
    ) {

        if (!enrollmentRunning) {
            break;
        }


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    CAPTURE_INTERVAL
                )
        );


        const frame =
            captureFrame(
                video,
                canvas
            );


        if (!frame) {
            continue;
        }


        samples.push(frame);


        const progress =
            (
                (i + 1) /
                REQUIRED_SAMPLES
            ) * 100;


        progressFill.style.width =
            `${progress}%`;


        sampleCounter.textContent =
            `${i + 1} / ${REQUIRED_SAMPLES}`;


        sampleStatus.textContent =
            `${i + 1} / ${REQUIRED_SAMPLES}`;


        setStatus(
            "enrollFaceStatus",
            `Sample ${i + 1} captured`,
            "success"
        );
    }


    if (
        samples.length !==
        REQUIRED_SAMPLES
    ) {

        enrollmentRunning = false;

        startButton.disabled = false;
        cancelButton.disabled = true;

        return;
    }


    /* ========================================================
       SEND TO BACKEND
    ======================================================== */

    setStatus(
        "enrollCameraStatus",
        "UPLOADING SAMPLES...",
        "ready"
    );

    setStatus(
        "enrollPadStatus",
        "RUNNING PAD CHECKS...",
        "ready"
    );


    const formData =
        new FormData();


    formData.append(
        "customer_id",
        customerId
    );

    formData.append(
        "external_user_id",
        externalUserId
    );


    samples.forEach(
        (sample, index) => {

            const blob =
                dataURLToBlob(sample);

            formData.append(
                "images",
                blob,
                `sample_${index + 1}.jpg`
            );
        }
    );


    try {

        const response =
            await fetch(
                ENROLL_API_URL,
                {
                    method: "POST",

                    credentials: FETCH_CREDENTIALS,

                    body: formData
                }
            );


        const result =
            await response.json();


        console.log(
            "Enrollment response:",
            result
        );


        if (!response.ok) {

            throw new Error(
                result.detail ||
                "Enrollment failed."
            );
        }


        if (
            result.enrolled === true
        ) {

            setStatus(
                "enrollPadStatus",
                "REAL FACE CONFIRMED",
                "success"
            );

            setStatus(
                "enrollFaceStatus",
                "ENROLLMENT SUCCESSFUL",
                "success"
            );

            setStatus(
                "enrollCameraStatus",
                "ENROLLMENT COMPLETE",
                "success"
            );


            showEnrollmentSuccess(
                externalUserId
            );

        } else {

            throw new Error(
                result.message ||
                "Enrollment was not completed."
            );
        }


    } catch (error) {

        console.error(
            "Enrollment error:",
            error
        );


        showEnrollmentFailure(
            error.message
        );


        setStatus(
            "enrollPadStatus",
            "ENROLLMENT FAILED",
            "failure"
        );

    } finally {

        enrollmentRunning = false;

        startButton.disabled = false;
        cancelButton.disabled = true;
    }
}


/* ============================================================
   CANCEL ENROLLMENT
   ============================================================ */

function cancelEnrollment() {

    enrollmentRunning = false;


    const startButton =
        document.getElementById(
            "startEnrollment"
        );

    const cancelButton =
        document.getElementById(
            "cancelEnrollment"
        );


    startButton.disabled = false;
    cancelButton.disabled = true;


    setStatus(
        "enrollCameraStatus",
        "ENROLLMENT CANCELLED",
        "failure"
    );
}


/* ============================================================
   ENROLLMENT RESULT
   ============================================================ */

function showEnrollmentSuccess(
    externalUserId
) {

    const panel =
        document.getElementById(
            "enrollResult"
        );


    panel.className =
        "result-panel result-success";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon success">
            ✓
        </div>

        <h3>
            Enrollment Successful
        </h3>

        <p>
            User
            <strong>
                ${escapeHTML(externalUserId)}
            </strong>
            has been enrolled successfully.
        </p>

    `;
}


function showEnrollmentFailure(
    message
) {

    const panel =
        document.getElementById(
            "enrollResult"
        );


    panel.className =
        "result-panel result-failure";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon failure">
            ✕
        </div>

        <h3>
            Enrollment Failed
        </h3>

        <p>
            ${escapeHTML(message)}
        </p>

    `;
}


/* ============================================================
   IDENTIFICATION
   ============================================================ */

async function identifyPerson() {

    if (identificationRunning) {
        return;
    }


    if (!identifyStream) {

        alert(
            "Camera is not ready."
        );

        return;
    }


    identificationRunning = true;


    const identifyButton =
        document.getElementById(
            "verifyButton"
        );

    const retryButton =
        document.getElementById(
            "retryButton"
        );


    identifyButton.disabled = true;


    if (retryButton) {
        retryButton.disabled = true;
    }


    const video =
        document.getElementById(
            "verifyCamera"
        );

    const canvas =
        document.getElementById(
            "verifyCanvas"
        );


    setStatus(
        "verifyCameraStatus",
        "SCANNING FACE...",
        "ready"
    );

    setStatus(
        "verifyFaceStatus",
        "DETECTING FACE...",
        "ready"
    );

    setStatus(
        "verifyPadStatus",
        "CHECKING LIVENESS...",
        "ready"
    );

    setStatus(
        "verifySystemStatus",
        "IDENTIFYING...",
        "ready"
    );


    hideIdentificationResults();


    const frame =
        captureFrame(
            video,
            canvas
        );


    if (!frame) {

        identificationRunning = false;

        identifyButton.disabled = false;

        return;
    }


    const blob =
        dataURLToBlob(frame);


    /*
     * IMPORTANT:
     *
     * The backend /identify endpoint requires
     * customer_id + image.
     *
     * For this development demo we use
     * DEMO_COMPANY.
     */

    const formData =
        new FormData();


    formData.append(
        "customer_id",
        CUSTOMER_ID
    );


    formData.append(
        "image",
        blob,
        "identification.jpg"
    );


    try {

        const response =
            await fetch(
                IDENTIFY_API_URL,
                {
                    method: "POST",

                    credentials: FETCH_CREDENTIALS,

                    body: formData
                }
            );


        const result =
            await response.json();


        console.log(
            "Identification response:",
            result
        );


        if (!response.ok) {

            const errorMessage =
                typeof result.detail === "string"
                    ? result.detail
                    : JSON.stringify(
                        result.detail ||
                        result
                    );

            throw new Error(
                errorMessage ||
                "Identification failed."
            );
        }


        /* ====================================================
           SPOOF
        ==================================================== */

        if (
            result.pad &&
            result.pad.label === "SPOOF"
        ) {

            setStatus(
                "verifyPadStatus",
                "SPOOF DETECTED",
                "failure"
            );

            setStatus(
                "verifyFaceStatus",
                "FACE REJECTED",
                "failure"
            );

            setStatus(
                "verifySystemStatus",
                "ACCESS DENIED",
                "failure"
            );


            showSpoofResult();

            return;
        }


        /* ====================================================
           REAL
        ==================================================== */

        if (
            result.pad &&
            result.pad.label === "REAL"
        ) {

            setStatus(
                "verifyPadStatus",
                "REAL",
                "success"
            );
        }


        setStatus(
            "verifyFaceStatus",
            "FACE DETECTED",
            "success"
        );


        /* ====================================================
           MATCH FOUND
        ==================================================== */

        if (
            result.identified === true
        ) {

            setStatus(
                "verifySystemStatus",
                "IDENTITY CONFIRMED",
                "success"
            );


            showIdentificationSuccess(
                result
            );

        } else {

            setStatus(
                "verifySystemStatus",
                "NO REGISTERED USER",
                "failure"
            );


            showIdentificationFailure(
                result
            );
        }


    } catch (error) {

        console.error(
            "Identification error:",
            error
        );


        setStatus(
            "verifySystemStatus",
            "SYSTEM ERROR",
            "failure"
        );


        showIdentificationError(
            error.message
        );


    } finally {

        identificationRunning = false;

        identifyButton.disabled = false;

        if (retryButton) {
            retryButton.disabled = false;
        }
    }
}


/* ============================================================
   IDENTIFICATION RESULTS
   ============================================================ */

function showIdentificationSuccess(
    result
) {

    const panel =
        document.getElementById(
            "verifyResult"
        );


    const userId =
        result.external_user_id ||
        "Unknown";


    const similarity =
        typeof result.similarity === "number"

            ? `${(
                result.similarity * 100
            ).toFixed(1)}%`

            : "N/A";


    panel.className =
        "result-panel result-success";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon success">
            ✓
        </div>

        <h3>
            VERIFIED
        </h3>

        <p>
            User
            <strong>
                ${escapeHTML(userId)}
            </strong>
        </p>

        <p>
            Face match:
            <strong>
                ${similarity}
            </strong>
        </p>

    `;
}


function showIdentificationFailure(
    result
) {

    const panel =
        document.getElementById(
            "verifyResult"
        );


    const reason =
        result.reason ||
        "No registered user matched this face.";


    panel.className =
        "result-panel result-failure";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon failure">
            ✕
        </div>

        <h3>
            NOT IDENTIFIED
        </h3>

        <p>
            ${escapeHTML(reason)}
        </p>

    `;
}


function showSpoofResult() {

    const panel =
        document.getElementById(
            "verifyResult"
        );


    panel.className =
        "result-panel result-spoof";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon spoof">
            ⚠
        </div>

        <h3>
            SPOOF DETECTED
        </h3>

        <p>
            Access denied.
            Please use a real face.
        </p>

    `;
}


function showIdentificationError(
    message
) {

    const panel =
        document.getElementById(
            "verifyResult"
        );


    panel.className =
        "result-panel result-failure";

    panel.classList.remove(
        "hidden"
    );


    panel.innerHTML = `

        <div class="result-icon failure">
            !
        </div>

        <h3>
            SYSTEM ERROR
        </h3>

        <p>
            ${escapeHTML(message)}
        </p>

    `;
}


function hideIdentificationResults() {

    const panel =
        document.getElementById(
            "verifyResult"
        );


    if (panel) {
        panel.classList.add(
            "hidden"
        );
    }
}


/* ============================================================
   RETRY
   ============================================================ */

function retryIdentification() {

    hideIdentificationResults();


    setStatus(
        "verifyCameraStatus",
        "CAMERA READY",
        "ready"
    );

    setStatus(
        "verifyFaceStatus",
        "WAITING FOR FACE",
        "waiting"
    );

    setStatus(
        "verifyPadStatus",
        "WAITING",
        "waiting"
    );

    setStatus(
        "verifySystemStatus",
        "READY",
        "ready"
    );
}


/* ============================================================
   SECURITY
   ============================================================ */

function escapeHTML(value) {

    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


/* ============================================================
   SERVER SESSION
   ============================================================ */

async function initializeSession() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/session`,
                {
                    method: "GET",
                    credentials: FETCH_CREDENTIALS,
                }
            );

        if (!response.ok) {

            console.warn(
                "Server session initialization failed:",
                response.status
            );
        }

    } catch (error) {

        console.warn(
            "Server session initialization failed:",
            error
        );
    }
}


/* ============================================================
   EVENT LISTENERS
   ============================================================ */

if (enrollTab) {

    enrollTab.addEventListener(
        "click",
        () => {
            showMode("enroll");
        }
    );
}


if (verifyTab) {

    verifyTab.addEventListener(
        "click",
        () => {
            showMode("verify");
        }
    );
}


const startEnrollmentButton =
    document.getElementById(
        "startEnrollment"
    );

if (startEnrollmentButton) {

    startEnrollmentButton.addEventListener(
        "click",
        startEnrollment
    );
}


const cancelEnrollmentButton =
    document.getElementById(
        "cancelEnrollment"
    );

if (cancelEnrollmentButton) {

    cancelEnrollmentButton.addEventListener(
        "click",
        cancelEnrollment
    );
}


const identifyButton =
    document.getElementById(
        "verifyButton"
    );

if (identifyButton) {

    identifyButton.addEventListener(
        "click",
        identifyPerson
    );
}


const retryButton =
    document.getElementById(
        "retryButton"
    );

if (retryButton) {

    retryButton.addEventListener(
        "click",
        retryIdentification
    );
}


/* ============================================================
   INITIAL STATE
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        await initializeSession();

        showMode("enroll");


        setStatus(
            "enrollCameraStatus",
            "STARTING CAMERA...",
            "waiting"
        );


        setStatus(
            "verifyCameraStatus",
            "CAMERA NOT STARTED",
            "waiting"
        );
    }
);