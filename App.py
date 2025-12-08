from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np
import time
import threading
import pyautogui
import sounddevice as sd
import random

app = Flask(__name__)

# Global variables
face_detector = None
exam_in_progress = False
no_face_start_time = None
multiple_face_start_time = None
exam_termination_event = threading.Event()
exam_window = ""
current_window = ""
noise_level = 0
NOISE_THRESHOLD = 30
NOISE_SIMULATION_THRESHOLD = 20
warning_issued = False
warning_time = None


def get_face_detector():
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    detector = cv2.CascadeClassifier(face_cascade_path)
    return detector


def detect_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, 1.1, 5)
    return faces


def draw_faces(frame, faces):
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    return frame


def detect_noise():
    return random.randint(0, 100)


def audio_callback(indata, frames, time, status):
    global noise_level
    volume_norm = np.linalg.norm(indata) * 10
    noise_level = int(volume_norm)


def generate_frames():
    global face_detector, no_face_start_time, multiple_face_start_time
    global exam_in_progress, exam_window, current_window
    global noise_level, warning_issued, warning_time

    if face_detector is None:
        face_detector = get_face_detector()

    cap = cv2.VideoCapture(0)

    while not exam_termination_event.is_set():
        success, frame = cap.read()
        if not success:
            break

        faces = detect_faces(frame)
        face_count = len(faces)
        frame = draw_faces(frame, faces)

        if face_count == 0:
            if no_face_start_time is None:
                no_face_start_time = time.time()
            elif time.time() - no_face_start_time > 5:
                cv2.putText(frame, "No Face → Exam Terminated", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                exam_termination_event.set()
        elif face_count > 1:
            if multiple_face_start_time is None:
                multiple_face_start_time = time.time()
            elif time.time() - multiple_face_start_time > 5:
                cv2.putText(frame, "Multiple Faces → Terminated", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                exam_termination_event.set()
        else:
            no_face_start_time = None
            multiple_face_start_time = None

        noise_level = detect_noise()
        if noise_level > NOISE_SIMULATION_THRESHOLD:
            cv2.putText(frame, "⚠ Noise Warning!", (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if exam_in_progress and current_window != exam_window:
            cv2.putText(frame, "⚠ Tab Switch Detected!", (10, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            exam_termination_event.set()

        cv2.putText(frame, f"Faces: {face_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
               frame + b'\r\n')

    cap.release()


def monitor_screen():
    global exam_window, current_window

    while not exam_in_progress:
        time.sleep(1)

    time.sleep(5)
    exam_window = pyautogui.getActiveWindowTitle()

    while not exam_termination_event.is_set():
        current_window = pyautogui.getActiveWindowTitle()
        time.sleep(1)


def monitor_audio():
    with sd.InputStream(callback=audio_callback):
        sd.sleep(1000000)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start_exam')
def start_exam():
    global exam_in_progress
    exam_in_progress = True
    exam_termination_event.clear()
    threading.Thread(target=monitor_screen, daemon=True).start()
    threading.Thread(target=monitor_audio, daemon=True).start()
    return jsonify({"status": "🟢 Exam Started"})


@app.route('/end_exam')
def end_exam():
    global exam_in_progress
    exam_in_progress = False
    exam_termination_event.set()
    return jsonify({"status": "🔴 Exam Ended"})


@app.route('/check_status')
def check_status():
    status = {
        "exam_in_progress": exam_in_progress,
        "exam_terminated": exam_termination_event.is_set(),
        "current_window": current_window,
        "noise_level": noise_level
    }
    return jsonify(status)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
