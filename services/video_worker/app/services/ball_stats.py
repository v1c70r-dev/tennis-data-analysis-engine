import numpy as np
import pandas as pd
import cv2
from app.services.mini_court import MiniCourt, _COURT_WIDTH, _COURT_LENGTH


class BallStats:

    MAX_SPEED_KMH = 250

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

    #  Heatmaps 

    def heatmap_image(self, width: int = 640, height: int = 480) -> np.ndarray:
        return self._build_heatmap(self._df, width, height)

    def heatmap_video(
        self,
        output_path: str,
        fps: float | None = None,
        window: int = 30,
        width: int = 640,
        height: int = 480,
    ) -> None:
        fps    = fps or self.fps
        writer = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height),
        )
        rows = self._df[self._df["mx"].notna()].reset_index(drop=True)
        for i in range(len(rows)):
            window_rows = rows.iloc[max(0, i - window): i + 1]
            writer.write(self._build_heatmap(window_rows, width, height))
        writer.release()

    #  Cálculo interno 

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        coords   = df.apply(lambda r: self._project(r), axis=1, result_type="expand")
        df["mx"] = coords[0]
        df["my"] = coords[1]

        df["dist_meters"] = float("nan")
        df["speed_kmh"]   = float("nan")

        valid = df["mx"].notna()
        mx    = df.loc[valid, "mx"].values
        my    = df.loc[valid, "my"].values
        idx   = df.index[valid]

        for i in range(1, len(mx)):
            if idx[i] - idx[i - 1] > 3:
                continue
            dist  = float(np.sqrt((mx[i] - mx[i-1])**2 + (my[i] - my[i-1])**2))
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
            cv2.circle(heat, (px, py), radius=8, color=1.0, thickness=-1)

        cv2.GaussianBlur(heat, (21, 21), 0, heat)
        norm = cv2.normalize(heat, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return cv2.applyColorMap(norm, cv2.COLORMAP_JET)