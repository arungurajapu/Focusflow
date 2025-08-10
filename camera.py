import cv2
import mediapipe as mp
import numpy as np
import time
from math import hypot

CONFIG = {
   "SLOUCH_THRESHOLD_VERTICAL": 0.28,
    # Your "Good" horizontal distance is ~0.02. We'll set the hunching threshold above that.
    "SLOUCH_THRESHOLD_HORIZONTAL": 0.07,

    "SMOOTHING_WINDOW": 10,
    "HEAD_TILT_THRESHOLD": 0.015,
    "DISTANCE_THRESHOLD_MAX": 0.2, 
    "EAR_THRESHOLD": 0.21,
    "BLINK_FRAME_COUNT": 2,
}

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        
        self.posture_tracker = []
        self.tilt_tracker = []
        self.distance_tracker = []
        self.blink_counter = 0
        self.closed_eye_frames = 0
        
        self.last_frame_data = None
        self.last_frame_time = 0

    def __del__(self):
        self.video.release()

    def _get_smoothed_status(self, tracker, good_threshold=0.7):
        if not tracker: return "Unknown"
        avg_status = sum(tracker) / len(tracker)
        if avg_status >= good_threshold: return "Good"
        return "Warning"

    def _calculate_ear(self, eye_landmarks):
        p1, p2, p3, p4, p5, p6 = eye_landmarks
        vertical_dist1 = hypot(p2.x - p6.x, p2.y - p6.y)
        vertical_dist2 = hypot(p3.x - p5.x, p3.y - p5.y)
        horizontal_dist = hypot(p1.x - p4.x, p1.y - p4.y)
        
        if horizontal_dist == 0:
            return 0
        
        ear = (vertical_dist1 + vertical_dist2) / (2.0 * horizontal_dist)
        return ear

    def get_frame(self, get_data_only=False):
        if get_data_only:
            return None, self.last_frame_data[1] if self.last_frame_data else {}

        current_time = time.time()
        if current_time - self.last_frame_time < 0.05 and self.last_frame_data:
             return self.last_frame_data

        success, image = self.video.read()
        if not success:
            return self.last_frame_data if self.last_frame_data else (None, {})

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        pose_results = self.pose.process(image_rgb)
        face_results = self.face_mesh.process(image_rgb)
        
        posture_status, tilt_status, distance_status = "Unknown", "Unknown", "Unknown"
        blink_status = f"{self.blink_counter}"

        if pose_results.pose_landmarks:
            lm_pose = pose_results.pose_landmarks.landmark
            l_shoulder = lm_pose[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            r_shoulder = lm_pose[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            nose = lm_pose[self.mp_pose.PoseLandmark.NOSE]
            
            if l_shoulder.visibility > 0.6 and r_shoulder.visibility > 0.6 and nose.visibility > 0.6:
                shoulder_center_x = (l_shoulder.x + r_shoulder.x) / 2
                shoulder_center_y = (l_shoulder.y + r_shoulder.y) / 2

                vertical_dist = abs(nose.y - shoulder_center_y)
                horizontal_dist = abs(nose.x - shoulder_center_x)

                is_bad_posture = (vertical_dist < CONFIG["SLOUCH_THRESHOLD_VERTICAL"]) or \
                                 (horizontal_dist > CONFIG["SLOUCH_THRESHOLD_HORIZONTAL"])
                
                # DEBUGGING: Print values to the terminal
                status_text = "GOOD" if not is_bad_posture else "BAD"
                print(f"DEBUG: V_Dist: {vertical_dist:.2f}, H_Dist: {horizontal_dist:.2f} -> Posture is {status_text}")

                self.posture_tracker.append(0 if is_bad_posture else 1)
                if len(self.posture_tracker) > CONFIG["SMOOTHING_WINDOW"]: self.posture_tracker.pop(0)
                posture_status = self._get_smoothed_status(self.posture_tracker)
        
        if face_results.multi_face_landmarks:
            all_face_lm = face_results.multi_face_landmarks[0].landmark
            LEFT_EYE_IDXS = [362, 385, 387, 263, 373, 380]; RIGHT_EYE_IDXS = [33, 160, 158, 133, 153, 144]
            left_eye_landmarks = [all_face_lm[i] for i in LEFT_EYE_IDXS]; right_eye_landmarks = [all_face_lm[i] for i in RIGHT_EYE_IDXS]
            
            left_ear_val = self._calculate_ear(left_eye_landmarks); right_ear_val = self._calculate_ear(right_eye_landmarks)
            avg_ear = (left_ear_val + right_ear_val) / 2.0

            if avg_ear < CONFIG["EAR_THRESHOLD"]: self.closed_eye_frames += 1
            else:
                if self.closed_eye_frames >= CONFIG["BLINK_FRAME_COUNT"]: self.blink_counter += 1
                self.closed_eye_frames = 0
            blink_status = f"{self.blink_counter}"

            l_eye_corner = all_face_lm[33]; r_eye_corner = all_face_lm[263]
            
            tilt_diff = abs(l_eye_corner.y - r_eye_corner.y)
            self.tilt_tracker.append(0 if tilt_diff > CONFIG["HEAD_TILT_THRESHOLD"] else 1)
            if len(self.tilt_tracker) > CONFIG["SMOOTHING_WINDOW"]: self.tilt_tracker.pop(0)
            tilt_status = self._get_smoothed_status(self.tilt_tracker)
            
            eye_dist_pixels = hypot(l_eye_corner.x - r_eye_corner.x, l_eye_corner.y - r_eye_corner.y)
            is_too_close = eye_dist_pixels > CONFIG["DISTANCE_THRESHOLD_MAX"]
            self.distance_tracker.append(0 if is_too_close else 1)
            if len(self.distance_tracker) > CONFIG["SMOOTHING_WINDOW"]: self.distance_tracker.pop(0)
            distance_status = self._get_smoothed_status(self.distance_tracker)
            
        data = {'posture': posture_status, 'blink': blink_status, 'tilt': tilt_status, 'distance': distance_status}
        ret, jpeg = cv2.imencode('.jpg', image)
        self.last_frame_data = (jpeg.tobytes(), data)
        self.last_frame_time = current_time
        return self.last_frame_data