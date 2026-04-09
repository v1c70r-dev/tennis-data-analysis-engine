import numpy as np
import pandas as pd
from app.services.mini_court import MiniCourt


class PlayerStats:

    MAX_SPEED_KMH = 36.05 #Novak Djokovic: 36.02 km/h

    def __init__(self, players_df: pd.DataFrame, mini_court: MiniCourt, fps: float):
        self.fps        = fps
        self.mini_court = mini_court
        self._df        = self._compute(players_df.copy())

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["mx"]          = float("nan")
        df["my"]          = float("nan")
        df["dist_meters"] = float("nan")
        df["speed_kmh"]   = float("nan")

        for pid, group in df.groupby("player_id"):
            for idx, row in group.iterrows():
                result = self.mini_court.project_to_meters(row["cx"], row["cy"])
                if result is None:
                    continue
                df.at[idx, "mx"] = result[0]
                df.at[idx, "my"] = result[1]

            valid = df[(df["player_id"] == pid) & df["mx"].notna()]
            mx    = valid["mx"].values
            my    = valid["my"].values
            idx   = valid.index

            for i in range(1, len(mx)):
                if idx[i] - idx[i - 1] > 5:
                    continue
                dist  = float(np.sqrt((mx[i] - mx[i-1])**2 + (my[i] - my[i-1])**2))
                speed = dist * self.fps * 3.6 #m/s a km/hr
                if speed > self.MAX_SPEED_KMH:
                    continue
                df.at[idx[i], "dist_meters"] = round(dist, 4) 
                df.at[idx[i], "speed_kmh"]   = round(speed, 2) 
                # obs. dist, es lo que recorrió el jugador desde su última ubicación 
                # conocida (hace máximo 5 frames) hasta su ubicación actual, 
                # medido en metros reales (homografia de la cancha)
        return df