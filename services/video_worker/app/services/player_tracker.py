from ultralytics import YOLO
import cv2
import numpy as np
from collections import defaultdict


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

    def identify_players(
        self,
        frames: list,
        court_poly: np.ndarray,
        device,
        n_frames: int = 10,
    ) -> tuple[set, dict]:
        """
        Analiza los primeros n_frames para identificar los 2 player_ids
        que corresponden a los jugadores reales dentro del court.

        Retorna:
            player_ids : set con los 2 ids seleccionados
            avg_positions : dict {player_id: (cx, cy)} posición promedio
        """
        positions  = defaultdict(list)   # {id: [(cx, cy), ...]}
        bbox_areas = defaultdict(list)   # {id: [area, ...]}

        for frame in frames[:n_frames]:
            result = self.model.track(
                frame,
                conf=self.conf,
                imgsz=self.imgsz,
                device=device,
                verbose=False,
                persist=True,
                classes=[0],
            )[0]

            if result.boxes is None or result.boxes.id is None:
                continue

            ids    = result.boxes.id.int().tolist()
            bboxes = result.boxes.xyxy.tolist()

            for pid, (x1, y1, x2, y2) in zip(ids, bboxes):
                cx   = (x1 + x2) / 2
                cy   = (y1 + y2) / 2
                area = (x2 - x1) * (y2 - y1)
                positions[pid].append((cx, cy))
                bbox_areas[pid].append(area)

        # Promediar posición y área por id
        avg_positions = {
            pid: (
                round(float(np.mean([p[0] for p in pts])), 2),
                round(float(np.mean([p[1] for p in pts])), 2),
            )
            for pid, pts in positions.items()
        }
        avg_areas = {
            pid: float(np.mean(areas))
            for pid, areas in bbox_areas.items()
        }

        # Filtrar ids dentro del court
        inside = {
            pid: pos
            for pid, pos in avg_positions.items()
            if cv2.pointPolygonTest(court_poly, pos, measureDist=False) >= 0
        }

        # Si hay más de 2, tomar los 2 con mayor bbox promedio
        candidates = inside if len(inside) >= 2 else avg_positions  # fallback
        top2 = sorted(candidates, key=lambda pid: avg_areas[pid], reverse=True)[:2]

        player_ids    = set(top2)
        avg_positions = {pid: avg_positions[pid] for pid in top2}

        print(f"  Jugadores identificados: {player_ids}")
        print(f"  Posiciones promedio    : {avg_positions}")

        return player_ids, avg_positions


    def _parse(self, r, frame_idx: int, player_ids: set | None = None) -> list[dict]:
        if r.boxes is None or r.boxes.id is None:
            return []

        ids    = r.boxes.id.int().tolist()
        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()

        rows = []
        for pid, conf, (x1, y1, x2, y2) in zip(ids, confs, bboxes):
            if player_ids is not None and pid not in player_ids:
                continue
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

    def track(self, frame, device, frame_idx: int, player_ids: set | None = None) -> tuple[list[dict], object]:
        result = self.model.track(
            frame,
            conf=self.conf,
            imgsz=self.imgsz,
            device=device,
            verbose=False,
            persist=True,
            classes=[0],
        )[0]

        rows = self._parse(result, frame_idx, player_ids=player_ids)
        return rows, result


    def draw(self, frame: np.ndarray, r, player_ids: set | None = None) -> None:
        if r.boxes is None or r.boxes.id is None:
            return

        ids    = r.boxes.id.int().tolist()
        confs  = r.boxes.conf.tolist()
        bboxes = r.boxes.xyxy.tolist()

        for pid, conf, (x1, y1, x2, y2) in zip(ids, confs, bboxes):
            if player_ids is not None and pid not in player_ids:
                continue
            color = self._COLORS[pid % len(self._COLORS)]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame, f"P{pid} {conf:.2f}",
                (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2,
            )