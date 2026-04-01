import uuid
import tempfile
import os
from app.config import settings
from app.services.storage import upload_file, get_presigned_url
import cv2
import numpy as np
from ultralytics import YOLO
import torch
import pandas as pd
from torchvision import models, transforms
import math
from tqdm import tqdm

#==========================================================================
# Perception layer: tennis ball detection, players tracking, and court keypoints detection each frame
#==========================================================================
def perception_layer(
    ball_model_path: str,
    players_model_path: str,
    kps_model_path: str,
    video_path: str,
    output_path: str = "output_perception.mp4",
    conf: float = 0.35,
    imgsz: int = 240,
    device: int | str = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    # Load keypoints model
    kps_model = models.resnet50()
    kps_model.fc = torch.nn.Linear(kps_model.fc.in_features, 14 * 2)
    load_best_model_tennis_court_detector(kps_model_path, kps_model)
    kps_model = kps_model.to(device)

    ball_model    = YOLO(ball_model_path)
    players_model = YOLO(players_model_path)

    transforms_pipeline = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)    

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    print(f"--- Iniciando perception layer: {video_path} ---")

    ball_rows   = []
    player_rows = []
    frame_idx   = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    kps_model.eval()
    with torch.no_grad():
        with tqdm(total=total_frames, desc="Analizando video", unit="frame") as pbar:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1

                ball_result = ball_model.predict(
                    frame, conf=conf, imgsz=imgsz, device=device, verbose=False
                )[0]
                players_result = players_model.track(
                    frame, conf=conf, imgsz=imgsz, device=device, verbose=False, persist=True, classes=[0]
                )[0]

                frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                input_tensor = transforms_pipeline(frame_rgb).unsqueeze(0).to(device)
                kps          = kps_model(input_tensor).squeeze().cpu().numpy()
                kps[::2]  *= width  / 224.0
                kps[1::2] *= height / 224.0

                ball_rows.append(_parse_ball_result(ball_result, frame_idx))
                player_rows.extend(_parse_player_result(players_result, frame_idx))

                annotated = _draw_frame(frame, ball_result, players_result)
                for i in range(0, len(kps), 2):
                    x, y = int(kps[i]), int(kps[i + 1])
                    cv2.circle(annotated, (x, y), radius=5, color=(0, 255, 0), thickness=-1)

                writer.write(annotated)
                # update loading bar
                pbar.update(1)

    cap.release()
    writer.release()

    print(f"  Video guardado en : {output_path}")
    print(f"  Total frames      : {frame_idx}\n")

    return pd.DataFrame(ball_rows), pd.DataFrame(player_rows)


#==========================================================================
#  best model tennis court key points detector 
#==========================================================================
def load_best_model_tennis_court_detector(path, model, optimizer=None):
    ckpt = torch.load(path, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    if optimizer:
        optimizer.load_state_dict(ckpt["optimizer"])
    return ckpt["epoch"], ckpt["metrics"]

#==========================================================================
#  Parsers 
#==========================================================================
def _parse_ball_result(r, frame_idx: int) -> dict:
    """Extrae datos de pelota de un resultado YOLO (un frame)."""
    no_det = r.boxes is None or len(r.boxes) == 0

    if no_det:
        return _empty_ball_row(frame_idx)

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


def _parse_player_result(r, frame_idx: int) -> list[dict]:
    """Extrae datos de jugadores de un resultado YOLO tracking (un frame)."""
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

#==========================================================================
# Drawing functions for annotated video output
#========================================================================== 
# Paleta de colores por player_id (BGR)
_PLAYER_COLORS = [
    (255, 100, 0), (0, 200, 255), (0, 255, 100),
    (200, 0, 255), (255, 200, 0), (0, 100, 255),
]

def _draw_frame(
    frame: np.ndarray,
    ball_result,
    players_result,
) -> np.ndarray:
    """Dibuja detecciones de pelota y jugadores sobre el frame."""
    out = frame.copy()
    _draw_ball(out, ball_result)
    _draw_players(out, players_result)
    return out


def _draw_ball(frame: np.ndarray, r) -> None:
    """Dibuja bbox de la pelota (amarillo)."""
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


def _draw_players(frame: np.ndarray, r) -> None:
    """Dibuja bbox y player_id por jugador (color único por ID)."""
    if r.boxes is None or r.boxes.id is None:
        return

    ids    = r.boxes.id.int().tolist()
    confs  = r.boxes.conf.tolist()
    bboxes = r.boxes.xyxy.tolist()

    for pid, conf, (x1, y1, x2, y2) in zip(ids, confs, bboxes):
        color = _PLAYER_COLORS[pid % len(_PLAYER_COLORS)]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, f"P{pid} {conf:.2f}",
            (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2,
        )

def _empty_ball_row(frame_idx: int) -> dict:
    """Fila vacía para frames sin detección."""
    nan = float("nan")
    return {
        "frame"          : frame_idx,
        "ball_detected"  : False,
        "conf"           : nan,
        "x1"             : nan, "y1": nan,
        "x2"             : nan, "y2": nan,
        "cx"             : nan, "cy": nan,
        "width"          : nan, "height": nan,
        "multi_detection": False,
    }


#==========================================================================
# Read video
#========================================================================== 
def read_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret: #not more frames to read
            break
        frames.append(frame)
    cap.release()
    return frames    

#==========================================================================
# Save video
#========================================================================== 
def save_video(output_video_frames, output_video_path):
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_video_path, fourcc, 30.0, (output_video_frames[0].shape[1], output_video_frames[0].shape[0])) 
    for frame in output_video_frames:
        out.write(frame)
    out.release()
    print(f'Saved output video to {output_video_path}')

#==========================================================================
# Run perception pipeline and return results
#==========================================================================
def run_perception(video_path: str) -> dict:
    output_filename = f"{uuid.uuid4()}.mp4"
    output_path     = os.path.join(tempfile.gettempdir(), output_filename)

    device = settings.device if settings.device != "0" else 0

    ball_df, players_df = perception_layer(
        ball_model_path    = settings.ball_model_path,
        players_model_path = settings.players_model_path,
        kps_model_path     = settings.kps_model_path,
        video_path         = video_path,
        output_path        = output_path,
        conf               = 0.25,
        imgsz              = 640,
        device             = device,
    )

    # Upload to MinIO
    upload_file(output_path, output_filename)
    video_url = get_presigned_url(output_filename)

    os.remove(output_path)

    return {
        "video_url":   video_url,
        "ball_data":   ball_df.to_dict(orient="records"),
        "player_data": players_df.to_dict(orient="records"),
    }



#==========================================================================
# Clean data function to replace NaN and Infinity with None recursively
#========================================================================== 
def clean_data(obj):
    """Reemplaza NaN e Infinity por None recursivamente."""
    if isinstance(obj, list):
        return [clean_data(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: clean_data(v) for k, v in obj.items()} 
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj