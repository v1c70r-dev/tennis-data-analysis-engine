# services/video_worker/app/services/ball_stats.py
import numpy as np
import pandas as pd
from app.services.mini_court import MiniCourt


class BallStats:

    MAX_SPEED_KMH = 263
    #km/hr record de velocidad de saque Challenger de Busan (no oficial) es de 263 km/hr (Sam Groth, 2012)
    #km/hr record de velocidad de saque oficial ATP es de 253 km/hr (John Isner, 2016)

    def __init__(self, ball_df: pd.DataFrame, mini_court: MiniCourt, fps: float):
        self.fps        = fps
        self.mini_court = mini_court
        self._df        = self._compute(ball_df.copy())

    #  API pública 
    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def avg_shot_speed(self) -> float:
        return round(float(self._df["speed_kmh"].mean(skipna=True)), 2)

    @property
    def max_shot_speed(self) -> float:
        return round(float(self._df["speed_kmh"].max(skipna=True)), 2)

    def avg_shot_speed_by_player(self, player_id: int) -> float:
        subset = self._df[self._df["shot_by"] == player_id]["speed_kmh"]
        return round(float(subset.mean(skipna=True)), 2)

    def max_shot_speed_by_player(self, player_id: int) -> float:
        subset = self._df[self._df["shot_by"] == player_id]["speed_kmh"]
        return round(float(subset.max(skipna=True)), 2)

    #  Cálculo interno 
    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforma las coordenadas de píxeles (2D de la cámara) en métricas 
        del mundo real (metros y km/h) aplicando geometría y cinemática.
        Esto se hace proyectando las coordenadas del centro de la pelota (cx, cy) a 
        un sistema de coordenadas en metros basado en la mini cancha, y luego 
        calculando la distancia y velocidad entre frames consecutivos. 
        """
        coords   = df.apply(lambda r: self._project(r), axis=1, result_type="expand")
        df["mx"] = coords[0]
        df["my"] = coords[1]

        df["dist_meters"] = float("nan")
        df["speed_kmh"]   = float("nan")

        valid = df["mx"].notna()
        mx    = df.loc[valid, "mx"].values
        my    = df.loc[valid, "my"].values
        idx   = df.index[valid] #frames donde la pelota fue detectada

        for i in range(1, len(mx)):
            #Si entre la detección actual (idx[i]) y la anterior (idx[i-1]) pasaron más de 3 frames (aprox. 0.1 segundos a 30fps) => no calcular velocidad
            #Si la pelota desaparece mucho tiempo y reaparece lejos, el cálculo daría una velocidad muy alta. Solo se calcula si hay continuidad visual.
            if idx[i] - idx[i - 1] > 3: 
                continue
            dist  = float(np.sqrt((mx[i] - mx[i-1])**2 + (my[i] - my[i-1])**2)) #dist. eculidiana (pitágoras)
            speed = dist * self.fps * 3.6
            if speed > self.MAX_SPEED_KMH:
                continue
            df.at[idx[i], "dist_meters"] = round(dist, 4)
            df.at[idx[i], "speed_kmh"]   = round(speed, 2)

        return df

    def _project(self, row) -> tuple:
        if pd.isna(row.get("cx")) or pd.isna(row.get("cy")):
            return (float("nan"), float("nan"))
        result = self.mini_court.project_to_meters(row["cx"], row["cy"])
        return result if result is not None else (float("nan"), float("nan"))