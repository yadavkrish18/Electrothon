# GuardianEye --- AI Women Safety Surveillance Dashboard

GuardianEye is a real-time AI-powered surveillance system designed to
detect potential safety risks involving women using computer vision. It
combines live video processing, gender detection, behavioral risk
analysis, SOS gesture detection, alert logging, and a professional web
dashboard.

The system is built with **Python + OpenCV + Flask**, and includes
automated evidence capture, manual override alerts, and  Twilio
SMS emergency notifications.

------------------------------------------------------------------------

## ✨ Features

### 🎥 Real-Time Vision Intelligence

-   Face detection using OpenCV DNN
-   Gender classification (Male/Female)
-   Multi-person tracking with centroid analysis

### ⚠ Safety Risk Detection

-   Lone woman detection (night context)
-   Group proximity harassment risk
-   Panic/erratic movement detection
-   SOS gesture recognition

### 🚨 Alert System

-   Automatic CRITICAL/WARNING status escalation
-   Manual emergency trigger
-   Evidence snapshot capture
-   Twilio SMS SOS alerts 

### 📊 Professional Dashboard UI

-   Live video monitoring panel
-   Risk level visualization
-   Event logging console
-   Map location view
-   Incident reports table

### 🧾 Logging & Evidence

-   CSV audit trail logging
-   Auto-saved image evidence during incidents
-   Real-time dashboard logs

------------------------------------------------------------------------

## 🏗 Architecture Overview

    Camera Feed
         ↓
    OpenCV Processing Pipeline
         ↓
    Risk Detection Engine
         ↓
    Dashboard + Alerts + Logging

------------------------------------------------------------------------

## 📦 Requirements

Python 3.9+

Install dependencies:

    pip install opencv-python numpy flask requests

    https://github.com/eveningglow/age-and-gender-classification/blob/master/model/gender_net.caffemodel  #download it and store it in same folder
    

------------------------------------------------------------------------

## 📁 Project Structure

    GuardianEye/
    │
    ├── app.py                  # Main application
    ├── evidence/               # Saved incident snapshots
    ├── security_events.csv      # Event audit log
    │
    ├── models/
    │   ├── opencv_face_detector_uint8.pb
    │   ├── opencv_face_detector.pbtxt
    │   ├── gender_net.caffemodel
    │   └── gender_deploy.prototxt
    │
    └── README.md

------------------------------------------------------------------------

## 🧠 Model Setup

Download required pretrained models:

Face detector: - opencv_face_detector_uint8.pb -
opencv_face_detector.pbtxt

Gender classifier: - gender_net.caffemodel - gender_deploy.prototxt


------------------------------------------------------------------------

## ▶ Running the System

Start the server:

    python app.py

Open browser:

    http://localhost:5000

------------------------------------------------------------------------

## 📷 Camera Support

### USB Webcam

    set USB_CAMERA_INDEX=0

### DroidCam (IP Camera)

    set DROIDCAM_URL=http://<ip>:4747/video
    set CAMERA_PRIORITY=droid

Linux/macOS:

    export VARIABLE=value

------------------------------------------------------------------------

## 🚨 Twilio SOS Integration

Set environment variables:

    TWILIO_ACCOUNT_SID=xxxx
    TWILIO_AUTH_TOKEN=xxxx
    TWILIO_FROM_NUMBER=+1xxxx
    SOS_TO_NUMBER=+91xxxx

When harassment risk is detected, an SOS message is sent automatically.

------------------------------------------------------------------------


## 🧪 Detection Logic Summary

-   Lone woman at night → WARNING
-   Surrounded by multiple men → CRITICAL
-   SOS gesture → CRITICAL
-   Panic movement → CRITICAL
-   Manual trigger → CRITICAL

------------------------------------------------------------------------

## 📸 Evidence Capture

During CRITICAL events:

-   Frame snapshots saved automatically
-   Stored in `/evidence`
-   Logged in CSV audit trail

------------------------------------------------------------------------



## 🔧 Troubleshooting

Camera not detected:

-   Ensure no other app is using the camera
-   Try different USB index
-   Check DroidCam URL
-   Run with administrator privileges

Model load errors:

-   Verify files exist
-   Check paths


