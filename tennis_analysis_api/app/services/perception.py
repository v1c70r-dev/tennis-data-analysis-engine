import uuid
import tempfile
import os
from app.config import settings
from app.services.storage import upload_file, get_presigned_url
from app.services.player_tracker import PlayerTracker
from app.services.tennis_ball_detector import BallDetector
from app.services.court_key_points_detector import CourtKeypointDetector
import cv2
import torch
import pandas as pd
import math
from tqdm import tqdm
import numpy as np

#==========================================================================
# Perception layer: tennis ball detection, players tracking,
# and court keypoints detection each frame
#==========================================================================
def perception_layer(
    ball_model_path: str,
    players_model_path: str,
    kps_model_path: str,
    video_path: str,
    output_path: str = "output_perception.mp4",
    conf: float = 0.35,
    imgsz: int = 240,
    device: int | str = "cpu",
) -> tuple[pd.DataFrame, pd.DataFrame]:

    #  Inicializar detectores 
    ball_detector  = BallDetector(ball_model_path, conf=conf, imgsz=imgsz)
    player_tracker = PlayerTracker(players_model_path, conf=conf, imgsz=imgsz)

    #  Video I/O 
    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)

    kps_detector = CourtKeypointDetector(kps_model_path, device=device)
    kps_detector.set_frame_size(width, height)

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    # Leer primeros n_frames para identificar jugadores
    first_frames = []
    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        first_frames.append(frame)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # rebobinar al inicio

    # Detectar court y jugadores
    kps          = kps_detector.detect(first_frames[0])
    court_poly   = kps_detector.court_polygon(kps)
    player_ids, avg_positions = player_tracker.identify_players(
        first_frames, court_poly, device
    )

    print(f"--- Iniciando perception layer: {video_path} ---")

    #  Loop principal 
    ball_rows    = []
    player_rows  = []
    frame_idx    = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    with torch.inference_mode():
        with tqdm(total=total_frames, desc="Analizando video", unit="frame") as pbar:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                ball_row                          = ball_detector.detect(frame, device, frame_idx)
                player_rows_frame, players_result = player_tracker.track(frame, device, frame_idx, player_ids=player_ids)
                #ball_row                          = ball_detector.detect(frame, device, frame_idx)
                #player_rows_frame, players_result = player_tracker.track(frame, device, frame_idx)
                kps                               = kps_detector.detect(frame)

                ball_rows.append(ball_row)
                player_rows.extend(player_rows_frame)

                annotated = frame.copy()
                ball_detector.draw(annotated, ball_row)
                #player_tracker.draw(annotated, players_result)
                player_tracker.draw(annotated, players_result, player_ids=player_ids)
                kps_detector.draw(annotated, kps)

                _draw_frame_counter(annotated, frame_idx)

                writer.write(annotated)
                pbar.update(1)

    cap.release()
    writer.release()

    print(f"  Video guardado en : {output_path}")
    print(f"  Total frames      : {frame_idx}\n")

    return pd.DataFrame(ball_rows), pd.DataFrame(player_rows)


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

#==========================================================================
# Draw the current frame number in the top left corner of the video
#==========================================================================
def _draw_frame_counter(frame: np.ndarray, frame_idx: int) -> None:
    """Dibuja el número de frame en negro con un fondo blanco sólido."""
    text = f"Frame: {frame_idx}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2
    pos = (10, 30)

    # Calculate the size of the text to make the background fit perfectly
    (w, h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    # Draw the white background rectangle
    cv2.rectangle(
        frame, 
        (pos[0] - 5, pos[1] - h - 5), 
        (pos[0] + w + 5, pos[1] + baseline + 5), 
        (255, 255, 255), 
        cv2.FILLED
    )

    # Draw the black text on top
    cv2.putText(
        frame,
        text,
        pos,
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )