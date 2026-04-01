import cv2
import numpy as np
from ultralytics import YOLO
import pandas as pd

class BallDetector:
    """Encapsula detección y visualización de la pelota."""

    def __init__(self, model_path: str, conf: float = 0.35, imgsz: int = 240):
        self.model = YOLO(model_path)
        self.conf  = conf
        self.imgsz = imgsz

    #  Inferencia 
    def detect(self, frame, device, frame_idx: int) -> tuple[dict, object]:
        """
        Ejecuta detección sobre un frame.
        Retorna (fila_para_dataframe, resultado_yolo).
        """
        result = self.model.predict(
            frame,
            conf=self.conf,
            imgsz=self.imgsz,
            device=device,
            verbose=False,
        )[0]

        row = self._parse(result, frame_idx)
        return row, result

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
    def draw(self, frame: np.ndarray, r) -> None:
        """Dibuja bbox de la pelota en amarillo (in-place)."""
        if r.boxes is None or len(r.boxes) == 0:
            return

        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()
        best   = int(pd.Series(confs).idxmax())
        x1, y1, x2, y2 = [int(v) for v in bboxes[best]]

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(
            frame, f"ball {confs[best]:.2f}",
            (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
        )

    #  Helpers 
    def _empty_row(self, frame_idx: int) -> dict:
        nan = float("nan")
        return {
            "frame"          : frame_idx,
            "ball_detected"  : False,
            "conf"           : nan,
            "x1": nan, "y1": nan,
            "x2": nan, "y2": nan,
            "cx": nan, "cy": nan,
            "width": nan, "height": nan,
            "multi_detection": False,
        }