import cv2
import time
import threading
import autopilot
import definitions as vars
import logger

# Object detection configuration (loaded from definitions)
OBJECT_DETECTION_THRESHOLD = vars.object_detection_threshold
OBJECT_DETECTED_THROTTLE = vars.object_detected_throttle
OBJECT_DETECTION_DURATION = vars.object_detection_duration

log = logger.bee_logger

def object_detector_process(stop_command):
    """
    Main object detection process that runs in a separate thread.
    Captures video frames, detects objects based on intensity threshold,
    and updates autopilot state with detection status and throttle changes.
    """
    log.info("Object detector process started")
    
    # Initialize camera
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("Failed to open camera")
            return
        
        log.info("Camera initialized successfully")
        
        last_detection_time = 0
        detection_active = False
        
        while not stop_command.is_set():
            ret, frame = cap.read()
            
            if not ret:
                log.warning("Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            # Convert to grayscale and calculate average intensity
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg_intensity = gray.mean()
            
            current_time = time.time()
            
            # Check if object is detected (intensity below threshold) // this is a super crude algorithm for testing
            if avg_intensity < OBJECT_DETECTION_THRESHOLD:
                if not detection_active:
                    log.info(f"Object detected! Intensity: {avg_intensity:.2f}")
                    autopilot.state['object_detected'] = True
                    autopilot.state['throttle'] = OBJECT_DETECTED_THROTTLE
                    detection_active = True
                    last_detection_time = current_time
            else:
                # Check if detection duration has elapsed
                if detection_active and (current_time - last_detection_time) >= OBJECT_DETECTION_DURATION:
                    log.info(f"No object detected. Intensity: {avg_intensity:.2f}")
                    autopilot.state['object_detected'] = False
                    autopilot.state['throttle'] = vars.default_throttle
                    detection_active = False
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)
    
    except Exception as e:
        log.error(f"Error in object detector process: {e}")
    
    finally:
        if cap is not None:
            cap.release()
        log.info("Object detector process stopped")
