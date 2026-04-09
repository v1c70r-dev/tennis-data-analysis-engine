import cv2
import numpy as np
import pandas as pd
from pathlib import Path


class VideoOverlayStats:
    def __init__(
        self,
        input_video: str,
        output_video: str,
        ball_stats: pd.DataFrame,
        player_stats: pd.DataFrame,
        video_metadata: dict,
    ):
        self.input_video = input_video
        self.output_video = output_video
        self.ball_stats = ball_stats.set_index("frame") if "frame" in ball_stats.columns else ball_stats
        self.player_stats = player_stats
        self.video_metadata = video_metadata

        # Detectar IDs de jugadores únicos (ordenados)
        self._player_ids = sorted(self.player_stats["player_id"].unique().tolist())

        # Parámetros visuales del overlay
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._font_scale = 0.45
        self._font_scale_header = 0.42
        self._thickness = 1
        self._line_h = 22          # altura de cada fila
        self._col_w = 80           # ancho de cada columna de jugador
        self._label_w = 140        # ancho de la columna de etiquetas
        self._padding = 10         # padding interior
        self._alpha = 0.55         # transparencia del fondo (0=transparente, 1=sólido)

        # Colores BGR
        self._bg_color = (20, 20, 20)
        self._header_color = (200, 200, 200)
        self._value_color = (255, 255, 255)
        self._label_color = (170, 200, 255)
        self._border_color = (80, 80, 80)
        self._accent_color = (60, 180, 120)   # verde para el header de jugadores

    # ------------------------------------------------------------------
    # Helpers de extracción de datos por frame
    # ------------------------------------------------------------------

    def _get_ball_row(self, frame_idx: int) -> pd.Series | None:
        """Devuelve la fila de ball_stats para el frame dado, o None."""
        if frame_idx in self.ball_stats.index:
            return self.ball_stats.loc[frame_idx]
        return None

    def _get_player_row(self, frame_idx: int, player_id: int) -> pd.Series | None:
        """Devuelve la fila de player_stats para (frame, player_id), o None."""
        mask = (self.player_stats["frame"] == frame_idx) & (self.player_stats["player_id"] == player_id)
        rows = self.player_stats[mask]
        if not rows.empty:
            return rows.iloc[0]
        return None

    def _accumulated_stats(self, frame_idx: int, player_id: int) -> dict:
        """
        Calcula las estadísticas acumuladas hasta el frame actual para un jugador:
          - dist_meters acumulada
          - avg speed_kmh (promedio de frames con velocidad > 0)
        """
        subset = self.player_stats[
            (self.player_stats["player_id"] == player_id)
            & (self.player_stats["frame"] <= frame_idx)
        ]
        total_dist = subset["dist_meters"].sum(skipna=True) if "dist_meters" in subset.columns else 0.0
        speeds = subset["speed_kmh"].dropna()
        speeds = speeds[speeds > 0]
        avg_speed = speeds.mean() if not speeds.empty else 0.0
        return {"dist_meters": total_dist, "avg_speed_kmh": avg_speed}

    def _accumulated_ball_stats(self, frame_idx: int) -> dict:
        """
        Calcula la velocidad promedio de la pelota hasta el frame actual.
        """
        subset = self.ball_stats[self.ball_stats.index <= frame_idx]
        speeds = subset["speed_kmh"].dropna() if "speed_kmh" in subset.columns else pd.Series([], dtype=float)
        speeds = speeds[speeds > 0]
        avg_speed = speeds.mean() if not speeds.empty else 0.0
        return {"avg_speed_kmh": avg_speed}

    # ------------------------------------------------------------------
    # Dibujado del overlay
    # ------------------------------------------------------------------

    def _draw_stats_overlay(self, frame: np.ndarray, frame_idx: int) -> np.ndarray:
        """
        Dibuja tabla de stats acumuladas en la esquina inferior derecha (in-place).

                          | P{id1}  | P{id2}  |
        curr ball speed   |  x km/h |  x km/h |
        avg ball speed    |  x km/h |  x km/h |
        player distance   |    x m  |    x m  |
        avg player speed  |  x km/h |  x km/h |

        Parameters
        ----------
        frame : np.ndarray
            Frame BGR sobre el que se dibuja.
        frame_idx : int
            Número de frame actual (1-based, igual que en los DataFrames).

        Returns
        -------
        np.ndarray
            Frame con el overlay aplicado.
        """
        n_players = len(self._player_ids)
        rows_data = 4   # curr ball speed / avg ball speed / player dist / avg player speed
        rows_total = 1 + rows_data  # header + datos

        table_w = self._label_w + n_players * self._col_w + 2 * self._padding
        table_h = rows_total * self._line_h + 2 * self._padding

        h_frame, w_frame = frame.shape[:2]
        x0 = w_frame - table_w - 12
        y0 = h_frame - table_h - 12

        # --- Fondo semitransparente ---
        overlay = frame.copy()
        cv2.rectangle(overlay, (x0, y0), (x0 + table_w, y0 + table_h), self._bg_color, -1)
        cv2.rectangle(overlay, (x0, y0), (x0 + table_w, y0 + table_h), self._border_color, 1)
        cv2.addWeighted(overlay, self._alpha, frame, 1 - self._alpha, 0, frame)

        # --- Recopilar datos ---
        ball_row = self._get_ball_row(frame_idx)
        curr_ball_speed = ball_row["speed_kmh"] if ball_row is not None and pd.notna(ball_row.get("speed_kmh")) else None
        ball_acc = self._accumulated_ball_stats(frame_idx)

        player_data = {}
        for pid in self._player_ids:
            p_row = self._get_player_row(frame_idx, pid)
            p_acc = self._accumulated_stats(frame_idx, pid)
            player_data[pid] = {"row": p_row, "acc": p_acc}

        # --- Posiciones base ---
        x_label = x0 + self._padding
        y_header = y0 + self._padding + self._line_h // 2

        def col_cx(i: int) -> int:
            """Centro X de la columna del jugador i (0-based)."""
            return x0 + self._padding + self._label_w + i * self._col_w + self._col_w // 2

        def row_cy(r: int) -> int:
            """Centro Y de la fila r (0=header, 1..4=datos)."""
            return y0 + self._padding + r * self._line_h + self._line_h // 2

        def put(img, text, cx, cy, color, scale=None, bold=False):
            sc = scale or self._font_scale
            th = 2 if bold else self._thickness
            tw, _ = cv2.getTextSize(text, self._font, sc, th)[0], None
            tw = cv2.getTextSize(text, self._font, sc, th)[0][0]
            cv2.putText(img, text, (cx - tw // 2, cy + 5), self._font, sc, color, th, cv2.LINE_AA)

        def put_left(img, text, x, cy, color, scale=None):
            sc = scale or self._font_scale
            cv2.putText(img, text, (x, cy + 5), self._font, sc, color, self._thickness, cv2.LINE_AA)

        # --- Separador vertical etiquetas | columnas ---
        sep_x = x0 + self._padding + self._label_w
        cv2.line(frame, (sep_x, y0), (sep_x, y0 + table_h), self._border_color, 1)

        # --- Separador horizontal header | datos ---
        sep_y = y0 + self._padding + self._line_h
        cv2.line(frame, (x0, sep_y), (x0 + table_w, sep_y), self._border_color, 1)

        # --- Header de jugadores ---
        for i, pid in enumerate(self._player_ids):
            put(frame, f"P{pid}", col_cx(i), row_cy(0), self._accent_color,
                scale=self._font_scale_header, bold=True)
            # separador vertical entre columnas de jugadores
            if i > 0:
                cx_sep = x0 + self._padding + self._label_w + i * self._col_w
                cv2.line(frame, (cx_sep, sep_y), (cx_sep, y0 + table_h), self._border_color, 1)

        # --- Filas de datos ---
        labels = [
            "Curr ball spd",
            "Avg ball spd",
            "Player dist",
            "Avg plyr spd",
        ]

        for r, label in enumerate(labels, start=1):
            put_left(frame, label, x_label, row_cy(r), self._label_color)

            for i, pid in enumerate(self._player_ids):
                acc = player_data[pid]["acc"]

                if r == 1:  # curr ball speed
                    val = f"{curr_ball_speed:.1f} km/h" if curr_ball_speed is not None else "-- km/h"
                elif r == 2:  # avg ball speed
                    v = ball_acc["avg_speed_kmh"]
                    val = f"{v:.1f} km/h" if v else "-- km/h"
                elif r == 3:  # player distance
                    d = acc["dist_meters"]
                    val = f"{d:.1f} m"
                elif r == 4:  # avg player speed
                    v = acc["avg_speed_kmh"]
                    val = f"{v:.1f} km/h" if v else "-- km/h"
                else:
                    val = "--"

                put(frame, val, col_cx(i), row_cy(r), self._value_color)

            # Separador horizontal entre filas de datos
            if r < rows_data:
                row_sep_y = y0 + self._padding + (r + 1) * self._line_h
                cv2.line(frame, (x0, row_sep_y), (x0 + table_w, row_sep_y), self._border_color, 1)

        return frame

    # ------------------------------------------------------------------
    # Procesamiento del video
    # ------------------------------------------------------------------

    def process(self) -> None:
        """
        Lee el video de entrada frame a frame, aplica el overlay de estadísticas
        y escribe el resultado en output_video.
        """
        cap = cv2.VideoCapture(self.input_video)
        if not cap.isOpened():
            raise FileNotFoundError(f"No se pudo abrir el video: {self.input_video}")

        width  = self.video_metadata["width"]
        height = self.video_metadata["height"]
        fps    = self.video_metadata["fps"]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(self.output_video, fourcc, fps, (width, height))

        frame_idx = 0
        total = self.video_metadata.get("total_frames", 0)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            frame = self._draw_stats_overlay(frame, frame_idx)
            out.write(frame)

            if total:
                pct = frame_idx / total * 100
                print(f"\r  Procesando... {frame_idx}/{total}  ({pct:.1f}%)", end="", flush=True)

        print()  # newline final
        cap.release()
        out.release()
        print(f"Video guardado en: {self.output_video}")