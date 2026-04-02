import numpy as np
import pandas as pd
import cv2
from app.services.mini_court import MiniCourt, _COURT_WIDTH, _COURT_LENGTH


class PlayerStats:

    MAX_SPEED_KMH = 35

    def __init__(self, players_df: pd.DataFrame, mini_court: MiniCourt, fps: float):
        self.fps        = fps
        self.mini_court = mini_court
        self._df        = self._compute(players_df.copy())

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def summary(self) -> pd.DataFrame:
        return (
            self._df.groupby("player_id")
            .agg(
                avg_speed_kmh = ("speed_kmh",   "mean"),
                max_speed_kmh = ("speed_kmh",   "max"),
                total_dist_m  = ("dist_meters", "sum"),
            )
            .round(2)
            .reset_index()
        )

    def heatmap_image(self, player_id: int, width: int = 640, height: int = 480) -> np.ndarray:
        return self._build_heatmap(
            self._df[self._df["player_id"] == player_id], width, height
        )

    def heatmap_video(
        self,
        player_id:   int,
        output_path: str,
        fps:         float | None = None,
        window:      int = 30,
        width:       int = 640,
        height:      int = 480,
    ) -> None:
        fps    = fps or self.fps
        writer = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height),
        )
        rows = (
            self._df[(self._df["player_id"] == player_id) & self._df["mx"].notna()]
            .reset_index(drop=True)
        )
        for i in range(len(rows)):
            window_rows = rows.iloc[max(0, i - window): i + 1]
            writer.write(self._build_heatmap(window_rows, width, height))
        writer.release()

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
                speed = dist * self.fps * 3.6
                if speed > self.MAX_SPEED_KMH:
                    continue
                df.at[idx[i], "dist_meters"] = round(dist, 4)
                df.at[idx[i], "speed_kmh"]   = round(speed, 2)

        return df

    def _build_heatmap(self, df: pd.DataFrame, width: int, height: int) -> np.ndarray:
        heat  = np.zeros((height, width), dtype=np.float32)
        valid = df[df["mx"].notna()] if "mx" in df.columns else pd.DataFrame()

        if len(valid) == 0:
            return cv2.applyColorMap(
                np.zeros((height, width), np.uint8), cv2.COLORMAP_JET
            )
        for mx, my in zip(valid["mx"].values, valid["my"].values):
            px = int(np.clip(mx / _COURT_WIDTH  * (width  - 1), 0, width  - 1))
            py = int(np.clip(my / _COURT_LENGTH * (height - 1), 0, height - 1))
            cv2.circle(heat, (px, py), radius=12, color=1.0, thickness=-1)

        cv2.GaussianBlur(heat, (31, 31), 0, heat)
        norm = cv2.normalize(heat, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return cv2.applyColorMap(norm, cv2.COLORMAP_JET)