from app import app
from app.camera import VideoCamera
from flask import render_template, Response, jsonify

# Create a single instance of the camera
camera = VideoCamera()

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

def gen(camera):
    """A generator function that yields frames from the camera."""
    while True:
        frame, data = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    """Route for the video streaming."""
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data')
def data():
    """Route to get the latest analysis data as JSON."""
    frame, data = camera.get_frame(get_data_only=True)
    return jsonify(data)