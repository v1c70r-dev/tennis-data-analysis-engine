import cv2
import numpy as np
from ultralytics import YOLO
import pandas as pd
from collections import deque

class BallDetector:
    """Encapsula detección y visualización de la pelota."""

    def __init__(self, model_path: str, conf: float = 0.35, imgsz: int = 240, buffer_size: int = 7):
        self.model   = YOLO(model_path)
        self.conf    = conf
        self.imgsz   = imgsz
        self._buffer = deque(maxlen=buffer_size)

    #  Inferencia 
    def detect(self, frame, device, frame_idx: int) -> dict:
        result   = self.model.predict(
            frame, conf=self.conf, imgsz=self.imgsz, device=device, verbose=False,
        )[0]
        detected = result.boxes is not None and len(result.boxes) > 0

        if detected:
            row = self._parse(result, frame_idx)
            self._buffer.append((row["cx"], row["cy"]))
        else:
            row = self._interpolate_row(frame_idx)

        return row

    #  Parser 
    def _parse(self, r, frame_idx: int) -> dict:
        if r.boxes is None or len(r.boxes) == 0:
            return self._empty_row(frame_idx)

        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()
        best   = int(pd.Series(confs).idxmax())
        x1, y1, x2, y2 = bboxes[best]

        return {
            "frame"          : frame_idx,
            "ball_detected"  : True,
            "interpolated"   : False,
            "conf"           : round(confs[best], 4),
            "x1": round(x1, 2), "y1": round(y1, 2),
            "x2": round(x2, 2), "y2": round(y2, 2),
            "cx"             : round((x1 + x2) / 2, 2),
            "cy"             : round((y1 + y2) / 2, 2),
            "width"          : round(x2 - x1, 2),
            "height"         : round(y2 - y1, 2),
            "multi_detection": len(confs) > 1,
        }

    #  Dibujo 
    def draw(self, frame: np.ndarray, row: dict) -> None:
        """Dibuja bbox o círculo estimado según si fue detectado o interpolado."""
        if not row.get("ball_detected") and not row.get("interpolated"):
            return  # empty row, nothing to draw
        x1, y1 = int(row["x1"]), int(row["y1"])
        cx, cy = int(row["cx"]), int(row["cy"])
        cv2.circle(frame, (cx, cy), radius=10, color=(0, 180, 180), thickness=2)
        cv2.putText(
            frame, f"ball {row['conf']:.2f}",
            (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
        )
        
        # if row.get("interpolated"):
        #     cx, cy = int(row["cx"]), int(row["cy"])
        #     cv2.circle(frame, (cx, cy), radius=10, color=(0, 180, 180), thickness=2)
        # else:
        #     x2, y2 = int(row["x2"]), int(row["y2"])
        #     cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        #     cv2.putText(
        #         frame, f"ball {row['conf']:.2f}",
        #         (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
        #     )


    #  Helpers 
    def _empty_row(self, frame_idx: int) -> dict:
        nan = float("nan")
        return {
            "frame"          : frame_idx,
            "ball_detected"  : False,
            "interpolated"   : False,
            "conf"           : nan,
            "x1": nan, "y1": nan,
            "x2": nan, "y2": nan,
            "cx": nan, "cy": nan,
            "width": nan, "height": nan,
            "multi_detection": False,
        }

    def _interpolate_row(self, frame_idx: int) -> dict:
        """Estimates ball position from recent detections in buffer."""
        if len(self._buffer) == 0:
            return self._empty_row(frame_idx)

        if len(self._buffer) == 1:
            cx, cy = self._buffer[-1]
        else:
            cx0, cy0 = self._buffer[-2]
            cx1, cy1 = self._buffer[-1]
            cx = cx1 + (cx1 - cx0)
            cy = cy1 + (cy1 - cy0)

        half_w = 10
        return {
            "frame"          : frame_idx,
            "ball_detected"  : False,
            "interpolated"   : True,
            "conf"           : float("nan"),
            "cx": round(cx, 2), "cy": round(cy, 2),
            "x1": round(cx - half_w, 2), "y1": round(cy - half_w, 2),
            "x2": round(cx + half_w, 2), "y2": round(cy + half_w, 2),
            "width": half_w * 2, "height": half_w * 2,
            "multi_detection": False,
        }