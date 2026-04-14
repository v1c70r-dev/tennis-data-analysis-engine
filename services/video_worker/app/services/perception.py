# services/video_worker/app/services/perception.py
import json
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
from app.services.mini_court import MiniCourt
from app.services.ball_stats import BallStats
from app.services.player_stats import PlayerStats
from app.services.storage import upload_dataframe
from scipy.interpolate import CubicSpline
from app.services.video_overlay_stats import VideoOverlayStats

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
    conf: float = 0.20,
    imgsz: int = 640,
    device: int | str = "cpu",
) -> tuple[pd.DataFrame, pd.DataFrame, MiniCourt, float, dict, dict]:

    #  Inicializar detectores 
    ball_detector  = BallDetector(ball_model_path, conf=conf, imgsz=imgsz, buffer_size=30)
    player_tracker = PlayerTracker(players_model_path, conf=conf, imgsz=imgsz)

    #  Video I/O 
    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Guardar datos del video para análisis posterior
    video_metadata = {
        "width": width,
        "height": height,
        "fps": fps,
        "total_frames": total_frames,
    }

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
    ball_detector.court_poly = court_poly
    player_ids, avg_positions = player_tracker.identify_players(
        first_frames, court_poly, device
    )

    mini_court = MiniCourt(origin=(20, None))
    mini_court.set_frame_size(height)
    mini_court.set_court_reference(kps)   # kps del primer frame, ya calculados

    mini_court_state = {
        "kps": kps.tolist(),
        "frame_height": height,
        "frame_width": width,
        "origin": mini_court._origin,
    }

    print(f"--- Iniciando perception layer: {video_path} ---")

    #  Loop principal 
    ball_rows    = []
    player_rows  = []
    frame_idx    = 0

    with torch.inference_mode():
        with tqdm(total=total_frames, desc="Analizando video", unit="frame") as pbar:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                ball_row = ball_detector.detect(frame, device, frame_idx)

                player_rows_frame, players_result = player_tracker.track(frame, device, frame_idx, player_ids=player_ids)
                kps = kps_detector.detect(frame)
                ball_row["shot_by"] = _assign_shot_to_player(ball_row, player_rows_frame) 

                ball_rows.append(ball_row)
                player_rows.extend(player_rows_frame)

                annotated = frame.copy()
                ball_detector.draw(annotated, ball_row)
                player_tracker.draw(annotated, players_result, player_ids=player_ids)
                kps_detector.draw(annotated, kps)
                mini_court.draw(annotated, player_rows_frame, ball_row=ball_row)
                # _draw_stats_overlay(
                #     annotated, ball_rows, player_rows,
                #     sorted(player_ids), mini_court, fps,
                # )
                _draw_frame_counter(annotated, frame_idx)

                writer.write(annotated)
                pbar.update(1)

    cap.release()
    writer.release()

    player_df = pd.DataFrame(player_rows)
    ball_df  = pd.DataFrame(ball_rows)
    ball_df  = smooth_ball_positions(ball_df, max_gap=15, use_spline=True) #extra post processing to interpolate the trajectory of the ball in a smoother way
    
    print(f"  Video guardado en : {output_path}")
    print(f"  Total frames      : {frame_idx}\n")

    return ball_df, player_df, mini_court, fps, mini_court_state, video_metadata


def run_perception(video_path: str, job_id: str) -> dict:
    output_path        = os.path.join(tempfile.gettempdir(), f"{job_id}.mp4")
    output_smooth_path = os.path.join(tempfile.gettempdir(), f"{job_id}_smooth.mp4")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ball_df, players_df, mini_court, fps, mini_court_state, video_metadata = perception_layer(
        ball_model_path    = settings.ball_model_path,
        players_model_path = settings.players_model_path,
        kps_model_path     = settings.kps_model_path,
        video_path         = video_path,
        output_path        = output_path,
        conf               = 0.20,
        imgsz              = 640,
        device             = device,
    )

    # Calcular stats
    ball_stats   = BallStats(ball_df, mini_court, fps)
    player_stats = PlayerStats(players_df, mini_court, fps)
    
    # Trayectoria de la pelota con suavizado spline/lineal y render overlay para validación visual
    render_smooth_overlay(
        input_video  = output_path,         
        output_video = output_smooth_path,  
        ball_df      = ball_df,
    )

    # video with overlay stats
    overlay_stats_path = output_smooth_path.replace(".mp4", "_overlay_stats.mp4")
    video_overlay_stats = VideoOverlayStats(
        input_video = output_smooth_path,
        output_video = overlay_stats_path,
        ball_stats = ball_stats.df,
        player_stats = player_stats.df,
        video_metadata=video_metadata
    )
    video_overlay_stats.process()

    # Sanitize mini_court_state
    mini_court_state_clean = {k: sanitize_for_json(v) for k, v in mini_court_state.items()}
    upload_file_path = "/tmp/mini_court_state.json"
    with open(upload_file_path, "w") as f:
        json.dump(mini_court_state_clean, f)

    # Sanitize video_metadata
    video_metadata_clean = {k: sanitize_for_json(v) for k, v in video_metadata.items()}
    upload_file_path = "/tmp/video_metadata.json"
    with open(upload_file_path, "w") as f:
        json.dump(video_metadata_clean, f)

    video_object = f"{job_id}/processed/video.mp4"
    upload_file(overlay_stats_path, video_object)     
    video_url = get_presigned_url(video_object)
    os.remove(output_path)                             
    os.remove(output_smooth_path)
    os.remove(overlay_stats_path)
        
    # Subir DataFrames
    upload_dataframe(ball_stats.df, f"{job_id}/processed/ball_stats.csv")
    upload_dataframe(player_stats.df, f"{job_id}/processed/player_stats.csv")

    return {
        "video_url"   : video_url,
        "ball_stats"  : clean_data(ball_stats.df.to_dict(orient="records")),
        "player_stats": clean_data(player_stats.df.to_dict(orient="records")),
        "mini_court_homography_state": clean_data(mini_court_state_clean),
        "video_data": clean_data(video_metadata_clean)
    }

#==========================================================================
# Sanitize data json
#==========================================================================

def sanitize_for_json(obj):
    # Si es un DataFrame de una sola fila, lo tratamos como registro único
    if isinstance(obj, pd.DataFrame):
        if len(obj) == 1:
            return sanitize_for_json(obj.iloc[0].to_dict())
        return obj.to_dict(orient="records")

    # Si es una Serie, tomamos sus valores
    if isinstance(obj, pd.Series):
        # Si el índice es simple (como [0]), convertimos a lista o valor único
        dict_obj = obj.to_dict()
        if list(dict_obj.keys()) == [0]: # Si solo existe el índice 0
            return sanitize_for_json(dict_obj[0])
        return {k: sanitize_for_json(v) for k, v in dict_obj.items()}

    if isinstance(obj, np.ndarray):
        return obj.tolist()
        
    if hasattr(obj, 'item') and not isinstance(obj, (list, dict)):
        return obj.item()
        
    return obj

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

def _assign_shot_to_player(
    ball_row:         dict,
    player_rows_frame: list[dict],
) -> int | None:
    """Retorna el player_id del jugador más cercano a la pelota en el frame actual."""
    if not player_rows_frame:
        return None
    if pd.isna(ball_row.get("cx")) or pd.isna(ball_row.get("cy")):
        return None

    bcx, bcy = ball_row["cx"], ball_row["cy"]
    closest  = min(
        player_rows_frame,
        key=lambda r: (r["cx"] - bcx)**2 + (r["cy"] - bcy)**2,
    )
    return closest["player_id"]


#################################################
def smooth_ball_positions(
    ball_df: pd.DataFrame,
    max_gap: int = 15,
    use_spline: bool = True,
) -> pd.DataFrame:
    """
    Post-procesamiento bidireccional de posiciones de la pelota.

    Para cada secuencia de frames inválidos (no detectados o interpolados),
    busca el último punto válido antes y el primero válido después, e interpola
    entre ellos. Si la brecha supera max_gap frames, no interpola (deja NaN).

    Parámetros
    ----------
    ball_df  : DataFrame de salida de perception_layer (una fila por frame)
    max_gap  : máximo número de frames consecutivos inválidos que se rellenan
    use_spline: True = CubicSpline (suave, requiere ≥4 puntos ancla)
                False = interpolación lineal (siempre disponible)

    Retorna
    -------
    DataFrame nuevo con columnas cx_smooth, cy_smooth, smooth_method añadidas.
    El DataFrame original no se modifica.
    """
    df = ball_df.copy()
    df["cx_smooth"]    = df["cx"].copy()
    df["cy_smooth"]    = df["cy"].copy()
    df["smooth_method"] = "original"

    #  Identificar frames válidos 
    # Un frame es válido si fue detectado dentro de la cancha (no interpolado)
    valid_mask = df["ball_detected"] & ~df["interpolated"]
    valid_idx  = df.index[valid_mask].tolist()

    if len(valid_idx) < 2:
        # Sin suficientes puntos válidos, no hay nada que hacer
        return df

    #  Recorrer gaps entre puntos válidos consecutivos 
    for i in range(len(valid_idx) - 1):
        left  = valid_idx[i]        # último frame válido antes del gap
        right = valid_idx[i + 1]    # primer frame válido después del gap
        gap   = right - left - 1    # frames inválidos entre ambos

        if gap == 0:
            continue  # frames contiguos, nada que rellenar

        if gap > max_gap:
            # Brecha demasiado larga => dejar NaN, no inventar
            df.loc[left + 1 : right - 1, "smooth_method"] = "gap_too_large"
            continue

        frames_to_fill = list(range(left + 1, right))

        #  Elegir método según puntos ancla disponibles 
        if use_spline:
            # Tomar hasta 4 puntos ancla a cada lado para el spline
            left_anchors  = [idx for idx in valid_idx if idx <= left][-4:]
            right_anchors = [idx for idx in valid_idx if idx >= right][:4]
            anchor_idx    = left_anchors + right_anchors

            if len(anchor_idx) >= 4:
                anchor_cx = df.loc[anchor_idx, "cx"].values
                anchor_cy = df.loc[anchor_idx, "cy"].values

                cs_x = CubicSpline(anchor_idx, anchor_cx)
                cs_y = CubicSpline(anchor_idx, anchor_cy)

                df.loc[frames_to_fill, "cx_smooth"] = cs_x(frames_to_fill).round(2)
                df.loc[frames_to_fill, "cy_smooth"] = cs_y(frames_to_fill).round(2)
                df.loc[frames_to_fill, "smooth_method"] = "spline"
                continue
            # Si no hay suficientes puntos para spline, caer a lineal

        #  Interpolación lineal 
        cx_left,  cy_left  = df.loc[left,  "cx"], df.loc[left,  "cy"]
        cx_right, cy_right = df.loc[right, "cx"], df.loc[right, "cy"]

        for f in frames_to_fill:
            t = (f - left) / (right - left)
            df.loc[f, "cx_smooth"] = round(cx_left  + t * (cx_right - cx_left),  2)
            df.loc[f, "cy_smooth"] = round(cy_left  + t * (cy_right - cy_left),  2)
            df.loc[f, "smooth_method"] = "linear"

    return df

def draw_smooth(frame: np.ndarray, row: pd.Series) -> None:
    cx = row.get("cx_smooth")
    cy = row.get("cy_smooth")
    if pd.isna(cx) or pd.isna(cy):
        return
    cx, cy = int(cx), int(cy)
    method = row.get("smooth_method", "")
    label  = {"spline": "SP", "linear": "LN", "original": "OR"}.get(method, "?")
    cv2.circle(frame, (cx, cy), radius=10, color=(255, 0, 128), thickness=4)
    cv2.putText(
        frame, label,
        (cx + 12, cy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 128), 2,
    )

def render_smooth_overlay(
    input_video: str,
    output_video: str,
    ball_df: pd.DataFrame,
) -> None:
    cap    = cv2.VideoCapture(input_video)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)

    writer = cv2.VideoWriter(
        output_video,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        rows = ball_df[ball_df["frame"] == frame_idx]
        if not rows.empty:
            draw_smooth(frame, rows.iloc[0])

        writer.write(frame)

    cap.release()
    writer.release()
    print(f"Video con smooth guardado en: {output_video}")