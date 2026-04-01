from ultralytics import YOLO
import cv2
import numpy as np

class PlayerTracker:
    """Encapsula detección, tracking y visualización de jugadores."""

    _COLORS = [
        (255, 100, 0), (0, 200, 255), (0, 255, 100),
        (200, 0, 255), (255, 200, 0), (0, 100, 255),
    ]

    def __init__(self, model_path: str, conf: float = 0.35, imgsz: int = 240):
        self.model = YOLO(model_path)
        self.conf  = conf
        self.imgsz = imgsz

    #  Inferencia 
    def track(self, frame, device, frame_idx: int) -> tuple[list[dict], object]:
        """
        Ejecuta tracking sobre un frame.
        Retorna (filas_para_dataframe, resultado_yolo).
        El resultado YOLO se devuelve para poder dibujarlo después.
        """
        result = self.model.track(
            frame,
            conf=self.conf,
            imgsz=self.imgsz,
            device=device,
            verbose=False,
            persist=True,
            classes=[0], #Person class only
        )[0]

        rows = self._parse(result, frame_idx)
        return rows, result

    #  Parser 
    def _parse(self, r, frame_idx: int) -> list[dict]:
        if r.boxes is None or r.boxes.id is None:
            return []

        ids    = r.boxes.id.int().tolist()
        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()

        rows = []
        for pid, conf, (x1, y1, x2, y2) in zip(ids, confs, bboxes):
            rows.append({
                "frame"    : frame_idx,
                "player_id": pid,
                "conf"     : round(conf, 4),
                "x1": round(x1, 2), "y1": round(y1, 2),
                "x2": round(x2, 2), "y2": round(y2, 2),
                "cx"       : round((x1 + x2) / 2, 2),
                "cy"       : round((y1 + y2) / 2, 2),
                "width"    : round(x2 - x1, 2),
                "height"   : round(y2 - y1, 2),
            })
        return rows

    #  Dibujo 
    def draw(self, frame: np.ndarray, r) -> None:
        """Dibuja bboxes con color único por player_id (in-place)."""
        if r.boxes is None or r.boxes.id is None:
            return

        ids    = r.boxes.id.int().tolist()
        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()

        for pid, conf, (x1, y1, x2, y2) in zip(ids, confs, bboxes):
            color = self._COLORS[pid % len(self._COLORS)]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame, f"P{pid} {conf:.2f}",
                (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2,
            )