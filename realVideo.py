import cv2
import numpy as np
import os
import time
from PIL import Image, ImageDraw
import io

try:
    from utils import process_frame
except Exception as exc:
    process_frame = None
    print(f"[WARN] realVideo.py could not import process_frame: {exc}")

# ── Config ─────────────────────────────────────────────────────────────────
FRAME_WIDTH  = 640
FRAME_HEIGHT = 480
RECONNECT_INTERVAL_SEC = 5   # how often to retry opening the camera if it's down


def open_camera(src=0):
    """
    Opens a camera source. Returns None (not a half-open object) on failure
    so callers can do a simple `if cap is None` check everywhere.
    """
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"[WARN] Camera source '{src}' could not be opened. "
              "Live video will not work until it reconnects.")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


# Module-level camera — opened once at Flask startup.
# NOTE: this is intentionally mutable at module scope (see _ensure_camera below)
# so a dropped USB camera can be recovered without restarting the Flask process.
cap = open_camera(0)
_last_reconnect_attempt = 0.0


def _ensure_camera():
    """
    Returns a working VideoCapture or None.
    If the current `cap` is dead, retries opening it at most once per
    RECONNECT_INTERVAL_SEC, instead of hammering the device every frame.
    """
    global cap, _last_reconnect_attempt

    if cap is not None and cap.isOpened():
        return cap

    now = time.time()
    if now - _last_reconnect_attempt < RECONNECT_INTERVAL_SEC:
        return None  # too soon to retry again

    _last_reconnect_attempt = now
    print("[INFO] Attempting camera reconnect...")
    cap = open_camera(0)
    return cap


def _make_placeholder_frame(message="Camera Unavailable", sub="Check device connection"):
    """Generates a dark placeholder JPEG when the camera is offline."""
    img = Image.new('RGB', (FRAME_WIDTH, FRAME_HEIGHT), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)

    # Simple camera icon (rectangle + lens circle)
    draw.rectangle([255, 170, 385, 250], outline=(255, 100, 100), width=3)
    draw.ellipse([295, 185, 345, 235], outline=(255, 100, 100), width=2)
    draw.rectangle([265, 165, 285, 175], fill=(255, 100, 100))

    # Centered text (PIL default font is ~6-7px wide per char — rough centering)
    x1 = (FRAME_WIDTH - len(message) * 7) // 2
    x2 = (FRAME_WIDTH - len(sub) * 6) // 2
    draw.text((x1, 265), message, fill=(255, 100, 100))
    draw.text((x2, 295), sub,     fill=(150, 150, 180))

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


# Pre-built once so it's ready instantly — no per-frame PIL cost when offline.
_PLACEHOLDER = _make_placeholder_frame()

# In-memory cart state keyed by trolley/session id.
# The Flask app uses this as the server-side source of truth for detected items.
CART_STORE = {}


def _normalize_trolley_id(trolley_id) -> str:
    return str(trolley_id or "default")


def set_cart_items(trolley_id, items) -> list:
    key = _normalize_trolley_id(trolley_id)
    normalized = []
    for item in items or []:
        if isinstance(item, str):
            item = item.strip()
            if item:
                normalized.append(item)
    CART_STORE[key] = normalized
    return normalized


def get_cart_items(trolley_id) -> list:
    return list(CART_STORE.get(_normalize_trolley_id(trolley_id), []))


def append_cart_items(trolley_id, items) -> list:
    """
    Adds items to the existing cart instead of replacing it.
    Used by the auto-scan polling loop, where every detection pass
    should accumulate onto what's already in the trolley — unlike
    set_cart_items(), which the manual /video single-shot flow uses
    to fully replace the cart with one frame's detections.
    """
    key = _normalize_trolley_id(trolley_id)
    existing = CART_STORE.get(key, [])
    new_valid = [item.strip() for item in (items or []) if isinstance(item, str) and item.strip()]
    CART_STORE[key] = existing + new_valid
    return new_valid


def detect_and_store_items(image_path: str, trolley_id=None) -> list:
    """Runs detection on an image if the model is available and stores results."""
    if process_frame is None:
        return get_cart_items(trolley_id)

    try:
        detected_items = process_frame(image_path)
    except Exception as exc:
        print(f"[WARN] detect_and_store_items failed: {exc}")
        detected_items = []

    return set_cart_items(trolley_id, detected_items)


def detect_live_frame(trolley_id=None) -> dict:
    """
    Grabs the current frame straight from the live camera (no disk write)
    and runs detection on it, appending any detected items to the cart.

    Used by the /auto_scan polling loop while the camera feed is live —
    distinct from capture_frame(), which is for the manual single-shot
    /video POST flow and writes to disk + replaces the cart via
    detect_and_store_items()/set_cart_items().

    Returns {"status": "ok"|"error", "new_items": [...], "all_items": [...]}
    so the Flask route can hand it straight back as JSON.
    """
    active_cap = _ensure_camera()
    if active_cap is None:
        return {"status": "error", "message": "Camera not available",
                "new_items": [], "all_items": get_cart_items(trolley_id)}

    try:
        ret, img = active_cap.read()
    except cv2.error as e:
        return {"status": "error", "message": f"Camera read failed: {e}",
                "new_items": [], "all_items": get_cart_items(trolley_id)}

    if not ret or img is None:
        return {"status": "error", "message": "Empty frame from camera",
                "new_items": [], "all_items": get_cart_items(trolley_id)}

    if process_frame is None:
        return {"status": "error", "message": "Detection model unavailable",
                "new_items": [], "all_items": get_cart_items(trolley_id)}

    # process_frame() (utils.py) reads from a file path, so write the
    # in-memory frame to the same path the manual flow already uses.
    # This keeps both flows visually consistent in static/img/processed.jpg.
    save_path = 'static/img/test.jpg'
    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    try:
        cv2.imwrite(save_path, img)
    except cv2.error as e:
        return {"status": "error", "message": f"Failed to write frame: {e}",
                "new_items": [], "all_items": get_cart_items(trolley_id)}

    try:
        detected_items = process_frame(save_path)
    except Exception as exc:
        print(f"[WARN] detect_live_frame: process_frame failed: {exc}")
        detected_items = []

    new_items = append_cart_items(trolley_id, detected_items)

    return {
        "status": "ok",
        "new_items": new_items,
        "all_items": get_cart_items(trolley_id),
    }


def capture_frame(save_path: str = 'static/img/test.jpg', trolley_id=None) -> bool:
    """
    Captures a single frame and saves it to disk.
    Returns True on success, False on failure (camera unavailable or bad frame).
    Called by the /video POST route.
    """
    active_cap = _ensure_camera()
    if active_cap is None:
        print("[ERROR] capture_frame: camera not available.")
        return False

    try:
        ret, img = active_cap.read()
    except cv2.error as e:
        print(f"[ERROR] capture_frame: cv2 read exception: {e}")
        return False

    if not ret or img is None:
        print("[ERROR] capture_frame: cap.read() returned empty frame.")
        return False

    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    try:
        cv2.imwrite(save_path, img)
    except cv2.error as e:
        print(f"[ERROR] capture_frame: failed to write frame to disk: {e}")
        return False

    detect_and_store_items(save_path, trolley_id=trolley_id)
    return True


def video_feed(src=0):
    """
    MJPEG generator for the /video_stream route.

    Behavior:
      - If the camera is unavailable, streams a placeholder frame every
        2 seconds (low CPU) instead of returning an empty generator.
        An empty generator just shows a broken-image icon forever in the
        browser; a placeholder frame at least shows a clear error state.
      - If the camera drops mid-stream, attempts a reconnect every
        RECONNECT_INTERVAL_SEC instead of looping forever on a dead handle.
      - Never raises out of the generator — any cv2 exception is caught
        and converted into a placeholder frame so the MJPEG stream itself
        never dies (which would otherwise kill the whole HTTP response).
    """
    while True:
        active_cap = _ensure_camera()

        if active_cap is None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + _PLACEHOLDER + b'\r\n'
            )
            time.sleep(2)
            continue

        try:
            ret, img = active_cap.read()
        except cv2.error as e:
            print(f"[ERROR] video_feed: cv2 read exception: {e}")
            ret, img = False, None

        if not ret or img is None:
            print("[WARN] video_feed: dropped frame — sending placeholder.")
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + _PLACEHOLDER + b'\r\n'
            )
            continue

        try:
            success, buffer = cv2.imencode('.jpg', img)
        except cv2.error as e:
            print(f"[ERROR] video_feed: imencode exception: {e}")
            success = False

        if not success:
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )