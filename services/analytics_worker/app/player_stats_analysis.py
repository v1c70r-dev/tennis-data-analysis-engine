#services/analytics_worker/app/player_stats_analysis.py
import io
import pandas as pd
from typing import Any
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.ndimage import gaussian_filter
# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    PageBreak, Table, TableStyle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fig_to_png_bytes(fig: go.Figure, width: int = 900, height: int = 500) -> bytes:
    """Renderiza una figura Plotly a PNG (requiere kaleido)."""
    return fig.to_image(format="png", width=width, height=height, scale=1.5)


def _fig_to_rl_image(fig: go.Figure, width_cm: float = 16,
                     height_cm: float = 9) -> RLImage:
    """Convierte una figura Plotly en un objeto Image de ReportLab."""
    png = _fig_to_png_bytes(fig, width=int(width_cm * 37.8),
                             height=int(height_cm * 37.8))
    buf = io.BytesIO(png)
    return RLImage(buf, width=width_cm * cm, height=height_cm * cm)


# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------

_PLAYER_COLORS = [
    "#FF6400", "#00C8FF", "#00FF64",
    "#C800FF", "#FFC800", "#0064FF",
]

def _player_color(i: int) -> str:
    return _PLAYER_COLORS[i % len(_PLAYER_COLORS)]


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class PlayerStatsAnalysis:
    """
    Análisis de estadísticas de jugadores basado en Plotly.

    Parameters
    ----------
    df  : DataFrame con columnas mínimas: player_id, frame, speed_kmh,
          dist_meters, [mx, my] (para cancha).
    fps : fotogramas por segundo del vídeo.
    """

    SPRINT_THRESHOLD_KMH: float = 20.0
    SPEED_BINS  = [0, 5, 10, 15, 20, 35]
    SPEED_LABELS = ["0-5", "5-10", "10-15", "15-20", ">20"]

    _COURT_WIDTH   = 10.97
    _COURT_LENGTH  = 23.77
    _SERVICE_BOX   =  6.40
    _DOUBLES_ALLY  =  1.37

    # Tema oscuro compartido por todos los gráficos
    _LAYOUT_BASE: dict = dict(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font=dict(family="Inter, sans-serif", color="#e6edf3"),
        margin=dict(l=50, r=30, t=60, b=50),
    )

    def __init__(self, df: pd.DataFrame, fps: float):
        self.df  = df.dropna(subset=["dist_meters", "speed_kmh"])
        self.fps = fps

    # ------------------------------------------------------------------
    # 1. Resumen estadístico
    # ------------------------------------------------------------------

    def summarize(self, expresed_in_time: bool = False) -> pd.DataFrame:
        """Genera un resumen estadístico por jugador."""
        rows = []
        for pid, grp in self.df.groupby("player_id"):
            valid = grp.dropna(subset=["speed_kmh", "dist_meters"])

            above   = (valid["speed_kmh"] > self.SPRINT_THRESHOLD_KMH).astype(int)
            sprints = int((above.diff() == 1).sum())
            if len(above) > 0 and above.iloc[0] == 1:
                sprints += 1

            frames_moving = int((valid["speed_kmh"] > 1.0).sum())
            frames_total  = int(len(grp))

            row: dict[str, Any] = {
                "player_id": int(float(pid)),
                "dist_total_m":  round(float(valid["dist_meters"].sum()), 2),
                "speed_max_kmh": round(float(valid["speed_kmh"].max()), 2),
                "speed_avg_kmh": round(float(valid["speed_kmh"].mean()), 2),
                "sprints":       sprints,
                "frames_moving": frames_moving,
                "frames_total":  frames_total,
            }

            if expresed_in_time and self.fps > 0:
                sprint_runs: list[float] = []
                in_sprint, count = False, 0
                for v in valid["speed_kmh"]:
                    if v > self.SPRINT_THRESHOLD_KMH:
                        in_sprint, count = True, count + 1
                    elif in_sprint:
                        sprint_runs.append(count / self.fps)
                        in_sprint, count = False, 0
                if in_sprint:
                    sprint_runs.append(count / self.fps)

                row["sprint_avg_duration_s"] = round(float(np.mean(sprint_runs)), 2) if sprint_runs else 0.0
                row["sprint_max_duration_s"] = round(float(max(sprint_runs)), 2)     if sprint_runs else 0.0

            rows.append(row)

        summary = pd.DataFrame(rows)
        if not summary.empty:
            summary["pct_moving"] = (
                summary["frames_moving"] / summary["frames_total"] * 100
            ).round(1)
        return summary

    # ------------------------------------------------------------------
    # 2. Perfil de velocidad por jugador
    # ------------------------------------------------------------------

    def plot_player_speeds(self, expresed_in_time: bool = False) -> dict:
        """
        Devuelve un dict con la figura Plotly (subplots por jugador).
        """
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())

        fig = make_subplots(
            rows=len(players), cols=1,
            shared_xaxes=True,
            subplot_titles=[f"Jugador {p} — Perfil de Velocidad" for p in players],
            vertical_spacing=0.06,
        )

        x_label = "Tiempo (s)" if expresed_in_time and self.fps > 0 else "Frame"

        for row_i, pid in enumerate(players, start=1):
            grp   = df[df["player_id"] == pid].sort_values("frame").copy()
            x     = grp["frame"] / self.fps if expresed_in_time and self.fps > 0 else grp["frame"]
            color = _player_color(players.index(pid))

            # Área rellena — convertir hex a rgba para la transparencia
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            fill_color = f"rgba({r},{g},{b},0.15)"

            fig.add_trace(go.Scatter(
                x=x, y=grp["speed_kmh"].fillna(0),
                fill="tozeroy",
                fillcolor=fill_color,
                line=dict(color=color, width=1.8),
                name=f"Jugador {pid}",
                showlegend=(row_i == 1),
            ), row=row_i, col=1)

            # Línea de umbral de sprint
            fig.add_hline(
                y=self.SPRINT_THRESHOLD_KMH,
                line=dict(color="#E24B4A", width=1, dash="dash"),
                annotation_text=f"Sprint {self.SPRINT_THRESHOLD_KMH} km/h",
                annotation_font_color="#E24B4A",
                annotation_font_size=9,
                row=row_i, col=1,
            )

            fig.update_yaxes(title_text="Velocidad (km/h)", row=row_i, col=1)

        fig.update_xaxes(title_text=x_label, row=len(players), col=1)
        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Análisis de Velocidad Instantánea", font=dict(size=16)),
            height=350 * len(players),
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 3. Distribución de velocidades
    # ------------------------------------------------------------------

    def plot_speed_distribution(self) -> dict:
        """Distribución de velocidades por jugador (barras agrupadas)."""
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())

        fig = make_subplots(
            rows=1, cols=len(players),
            subplot_titles=[f"Jugador {p}" for p in players],
        )

        for col_i, pid in enumerate(players, start=1):
            grp    = df[df["player_id"] == pid].dropna(subset=["speed_kmh"])
            counts, _ = np.histogram(grp["speed_kmh"], bins=self.SPEED_BINS)
            pcts   = counts / counts.sum() * 100
            color  = _player_color(players.index(pid))

            fig.add_trace(go.Bar(
                x=self.SPEED_LABELS,
                y=pcts.tolist(),
                marker_color=color,
                opacity=0.85,
                name=f"Jugador {pid}",
                text=[f"{p:.1f}%" for p in pcts],
                textposition="outside",
                showlegend=False,
            ), row=1, col=col_i)

            fig.update_yaxes(title_text="% de frames", row=1, col=col_i)
            fig.update_xaxes(title_text="Rango (km/h)", row=1, col=col_i)

        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Distribución de Velocidad", font=dict(size=16)),
            height=420,
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 4. Distancia acumulada
    # ------------------------------------------------------------------

    def plot_cumulative_distance(self, expresed_in_time: bool = False) -> dict:
        """Distancia acumulada por jugador a lo largo del partido."""
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())

        fig     = go.Figure()
        x_label = "Tiempo (s)" if expresed_in_time and self.fps > 0 else "Frame"

        for pid in players:
            grp = df[df["player_id"] == pid].sort_values("frame").copy()
            grp["cumul_dist"] = grp["dist_meters"].fillna(0).cumsum()
            x   = grp["frame"] / self.fps if expresed_in_time and self.fps > 0 else grp["frame"]
            color = _player_color(players.index(pid))
            total = float(grp["cumul_dist"].iloc[-1])

            fig.add_trace(go.Scatter(
                x=x.tolist(),
                y=grp["cumul_dist"].tolist(),
                mode="lines",
                line=dict(color=color, width=2),
                name=f"Jugador {pid}  ({total:.1f} m)",
            ))

            # Anotación del total al final
            fig.add_annotation(
                x=float(x.iloc[-1]),
                y=total,
                text=f"<b>{total:.1f} m</b>",
                showarrow=False,
                xanchor="left",
                xshift=6,
                font=dict(color=color, size=10),
            )

        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Distancia Acumulada a lo Largo del Partido", font=dict(size=16)),
            xaxis_title=x_label,
            yaxis_title="Distancia acumulada (m)",
            legend=dict(bgcolor="rgba(0,0,0,0.4)"),
            height=430,
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 5. Comparación de métricas — subplots (Opción A)
    # ------------------------------------------------------------------

    def plot_metric_comparison_A(self, summary: pd.DataFrame) -> dict:
        """Subplots independientes por métrica, barras por jugador."""
        players = sorted(summary["player_id"].dropna().unique().astype(int).tolist())
        colors  = [_player_color(i) for i in range(len(players))]

        base_metrics = [
            ("dist_total_m",  "Distancia total (m)"),
            ("speed_max_kmh", "Vel. máxima (km/h)"),
            ("speed_avg_kmh", "Vel. promedio (km/h)"),
            ("sprints",       "Sprints"),
            ("pct_moving",    "Tiempo en movimiento (%)"),
        ]
        extra_metrics = [
            ("sprint_avg_duration_s", "Sprint prom. (s)"),
            ("sprint_max_duration_s", "Sprint máx. (s)"),
        ]
        metrics = base_metrics + [m for m in extra_metrics if m[0] in summary.columns]

        ncols = 4
        nrows = (len(metrics) + ncols - 1) // ncols

        fig = make_subplots(
            rows=nrows, cols=ncols,
            subplot_titles=[m[1] for m in metrics],
            vertical_spacing=0.14,
            horizontal_spacing=0.08,
        )

        for idx, (col, label) in enumerate(metrics):
            row_i = idx // ncols + 1
            col_i = idx % ncols + 1

            for j, pid in enumerate(players):
                val = float(summary[summary["player_id"] == pid].iloc[0][col])
                fig.add_trace(go.Bar(
                    x=[f"J{pid}"],
                    y=[val],
                    marker_color=colors[j],
                    opacity=0.85,
                    name=f"Jugador {pid}",
                    showlegend=(idx == 0),
                    text=[f"{val:.1f}"],
                    textposition="outside",
                    legendgroup=f"J{pid}",
                ), row=row_i, col=col_i)

        # Ocultar ejes sobrantes
        for j in range(len(metrics), nrows * ncols):
            r = j // ncols + 1
            c = j % ncols + 1
            fig.update_xaxes(visible=False, row=r, col=c)
            fig.update_yaxes(visible=False, row=r, col=c)

        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Comparación de Métricas por Jugador", font=dict(size=16)),
            barmode="group",
            height=350 * nrows,
            legend=dict(bgcolor="rgba(0,0,0,0.4)"),
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 6. Radar chart (Opción B)
    # ------------------------------------------------------------------

    def plot_metric_comparison_B(self, summary: pd.DataFrame) -> dict:
        """Radar/spider chart normalizado (0-100) por jugador."""
        players = sorted(summary["player_id"].dropna().unique().astype(int).tolist())

        base_metrics = [
            ("dist_total_m",  "Distancia total"),
            ("speed_max_kmh", "Vel. máxima"),
            ("speed_avg_kmh", "Vel. promedio"),
            ("sprints",       "Sprints"),
            ("pct_moving",    "% Movimiento"),
        ]
        extra_metrics = [
            ("sprint_avg_duration_s", "Sprint prom."),
            ("sprint_max_duration_s", "Sprint máx."),
        ]
        metrics = base_metrics + [m for m in extra_metrics if m[0] in summary.columns]

        cols   = [m[0] for m in metrics]
        labels = [m[1] for m in metrics]

        maxvals = summary[cols].max()
        norm    = summary[cols].div(maxvals.replace(0, 1)).mul(100)

        fig = go.Figure()

        for i, pid in enumerate(players):
            row    = norm[summary["player_id"] == pid].iloc[0]
            values = row[cols].tolist()
            real   = summary[summary["player_id"] == pid].iloc[0]

            # Texto en cada vértice con valor real
            hover = [
                f"{labels[j]}: {float(real[cols[j]]):.1f}"
                for j in range(len(cols))
            ]

            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                fillcolor='rgba({},{},{},0.12)'.format(int(_player_color(i)[1:3],16),int(_player_color(i)[3:5],16),int(_player_color(i)[5:7],16)),
                line=dict(color=_player_color(i), width=2),
                name=f"Jugador {pid}",
                hovertemplate="<b>%{theta}</b><br>" + f"Jugador {pid}" + "<br>%{r:.1f} (norm)<extra></extra>",
            ))

        fig.update_layout(
            **self._LAYOUT_BASE,
            polar=dict(
                bgcolor="#161b22",
                angularaxis=dict(linecolor="#444", tickcolor="#888"),
                radialaxis=dict(
                    visible=True, range=[0, 110],
                    tickvals=[25, 50, 75, 100],
                    ticktext=["25", "50", "75", "100"],
                    linecolor="#444",
                    gridcolor="#333",
                ),
            ),
            title=dict(
                text="Perfil de Rendimiento Relativo<br><sup>Normalizado al máximo del grupo</sup>",
                font=dict(size=16),
            ),
            legend=dict(bgcolor="rgba(0,0,0,0.4)"),
            height=520,
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 7. Trayectorias en cancha
    # ------------------------------------------------------------------

    def plot_trajectories_combined(self, flip_view: bool = False) -> dict:
        """
        Trayectoria de todos los jugadores sobre cancha de tenis cenital.
        Coloreado por velocidad (escala plasma).
        """
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        fig     = go.Figure()

        # Dibuja cancha
        self._draw_court_plotly(fig)

        v_global_max = float(df["speed_kmh"].max(skipna=True))

        for pid in players:
            grp = (df[df["player_id"] == pid]
                   .dropna(subset=["mx", "my"])
                   .sort_values("frame"))
            if grp.empty:
                continue

            xs     = grp["mx"].values
            ys     = grp["my"].values
            speeds = grp["speed_kmh"].fillna(0).values

            # Trayectoria con colorscale plasma usando scatter coloreado
            fig.add_trace(go.Scatter(
                x=xs.tolist(),
                y=ys.tolist(),
                mode="lines+markers",
                marker=dict(
                    color=speeds.tolist(),
                    colorscale="Plasma",
                    cmin=0, cmax=max(v_global_max, 1),
                    size=3,
                    showscale=(pid == players[0]),
                    colorbar=dict(
                        title="km/h", len=0.5,
                        tickfont=dict(size=9),
                        x=1.02,
                    ),
                ),
                line=dict(color="rgba(200,200,200,0.3)", width=1.5),
                name=f"J{pid} | {speeds.max():.1f} km/h máx",
                hovertemplate=(
                    f"<b>Jugador {pid}</b><br>"
                    "x: %{x:.2f} m<br>y: %{y:.2f} m<br>"
                    "velocidad: %{marker.color:.1f} km/h<extra></extra>"
                ),
            ))

            # Inicio (verde) / Fin (rojo)
            fig.add_trace(go.Scatter(
                x=[xs[0]], y=[ys[0]],
                mode="markers+text",
                marker=dict(color="#00ff88", size=10, symbol="circle",
                            line=dict(color="white", width=1)),
                text=[f"J{pid}"], textposition="top right",
                textfont=dict(color="white", size=9),
                name="Inicio", showlegend=(pid == players[0]),
                legendgroup="inicio",
            ))
            fig.add_trace(go.Scatter(
                x=[xs[-1]], y=[ys[-1]],
                mode="markers",
                marker=dict(color="#ff4444", size=10, symbol="circle",
                            line=dict(color="white", width=1)),
                name="Fin", showlegend=(pid == players[0]),
                legendgroup="fin",
            ))

        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Trayectoria Coloreada por Velocidad", font=dict(size=16)),
            xaxis=dict(title="Ancho (m)", scaleanchor="y", constrain="domain"),
            yaxis=dict(title="Largo (m)", autorange="reversed" if flip_view else True),
            height=700,
            legend=dict(bgcolor="rgba(0,0,0,0.4)"),
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 8. Heatmap de posiciones
    # ------------------------------------------------------------------

    def plot_heatmaps_combined(
        self,
        margin: float = 2.0,
        bins: int = 50,
        sigma: float = 1.5,
        flip_view: bool = False,
    ) -> dict:
        """Mapa de calor de posiciones de todos los jugadores."""
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())

        x_min = -margin;  x_max = self._COURT_WIDTH  + margin
        y_min = -margin;  y_max = self._COURT_LENGTH + margin

        # Un subplot por jugador (1 fila, N columnas)
        fig = make_subplots(
            rows=1, cols=len(players),
            subplot_titles=[f"Jugador {p}" for p in players],
            horizontal_spacing=0.06,
        )

        for col_i, pid in enumerate(players, start=1):
            grp = df[df["player_id"] == pid].dropna(subset=["mx", "my"])
            if grp.empty:
                continue

            heatmap, xedges, yedges = np.histogram2d(
                grp["mx"].values, grp["my"].values,
                bins=bins,
                range=[[x_min, x_max], [y_min, y_max]],
            )
            heatmap = gaussian_filter(heatmap.T, sigma=sigma)
            heatmap = heatmap / heatmap.max()

            fig.add_trace(go.Heatmap(
                z=heatmap.tolist(),
                x=((xedges[:-1] + xedges[1:]) / 2).tolist(),
                y=((yedges[:-1] + yedges[1:]) / 2).tolist(),
                colorscale="Hot",
                showscale=(col_i == len(players)),
                colorbar=dict(title="Densidad", len=0.8,
                              tickvals=[0, 0.5, 1],
                              ticktext=["Baja", "Media", "Alta"]),
                zmin=0, zmax=1,
                name=f"Jugador {pid}",
                hovertemplate="x: %{x:.2f} m<br>y: %{y:.2f} m<br>densidad: %{z:.2f}<extra></extra>",
            ), row=1, col=col_i)

            # Punto de máxima densidad
            iy, ix = np.unravel_index(np.argmax(heatmap), heatmap.shape)
            peak_x = float((xedges[ix] + xedges[ix + 1]) / 2)
            peak_y = float((yedges[iy] + yedges[iy + 1]) / 2)

            fig.add_trace(go.Scatter(
                x=[peak_x], y=[peak_y],
                mode="markers+text",
                marker=dict(symbol="x", size=12, color="white", line=dict(width=2)),
                text=[f"J{pid}"], textposition="top right",
                textfont=dict(color="white", size=9),
                showlegend=False,
            ), row=1, col=col_i)

            # Superponer silueta de cancha
            self._draw_court_plotly(fig, row=1, col=col_i, opacity=0.4)

            fig.update_yaxes(
                autorange="reversed" if flip_view else True,
                row=1, col=col_i,
            )
            fig.update_xaxes(title_text="Ancho (m)", row=1, col=col_i)

        fig.update_layout(
            **self._LAYOUT_BASE,
            title=dict(text="Mapa de Calor — Posiciones en Cancha", font=dict(size=16)),
            height=600,
        )
        return fig.to_dict()

    # ------------------------------------------------------------------
    # 9. Dashboard completo (para el frontend)
    # ------------------------------------------------------------------

    def get_dashboard_data(
        self,
        expresed_in_time: bool = False,
        flip_view: bool = False,
    ) -> dict:
        """
        Devuelve un dict con todos los datos del dashboard:
        - summary: lista de dicts (serializable)
        - figures: dict de nombre → figura Plotly serializada

        Ejemplo de uso en FastAPI:
            from fastapi.responses import JSONResponse
            return JSONResponse(analysis.get_dashboard_data())
        """
        summary = self.summarize(expresed_in_time)

        return {
            "summary": summary.to_dict(orient="records"),
            "figures": {
                "player_speeds":         self.plot_player_speeds(expresed_in_time),
                "speed_distribution":    self.plot_speed_distribution(),
                "cumulative_distance":   self.plot_cumulative_distance(expresed_in_time),
                "metric_comparison_A":   self.plot_metric_comparison_A(summary),
                "metric_comparison_B":   self.plot_metric_comparison_B(summary),
                "trajectories":          self.plot_trajectories_combined(flip_view),
                "heatmaps":              self.plot_heatmaps_combined(flip_view=flip_view),
            },
        }

    # ------------------------------------------------------------------
    # 10. Exportar PDF
    # ------------------------------------------------------------------

    def export_pdf(
        self,
        output_path: str = "player_stats_report.pdf",
        expresed_in_time: bool = False,
        flip_view: bool = False,
    ) -> str:
        """
        Genera un PDF con todos los gráficos del análisis.

        Requiere: pip install kaleido reportlab

        Returns
        -------
        output_path : ruta del PDF generado
        """
        summary = self.summarize(expresed_in_time)

        # Figuras que se incluirán en el PDF (nombre, fig, ancho_cm, alto_cm)
        figures_config = [
            ("Perfil de Velocidad",                self.plot_player_speeds(expresed_in_time),  16, 9 * len(self.df["player_id"].unique())),
            ("Distribución de Velocidad",          self.plot_speed_distribution(),             16, 8),
            ("Distancia Acumulada",                self.plot_cumulative_distance(expresed_in_time), 16, 8),
            ("Comparación de Métricas (barras)",   self.plot_metric_comparison_A(summary),     16, 10),
            ("Comparación de Métricas (radar)",    self.plot_metric_comparison_B(summary),     14, 14),
            ("Trayectorias en Cancha",             self.plot_trajectories_combined(flip_view), 12, 18),
            ("Mapa de Calor",                      self.plot_heatmaps_combined(flip_view=flip_view), 16, 9),
        ]

        # Construir el PDF con ReportLab
        doc    = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#1a73e8"),
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#e6edf3"),
            backColor=colors.HexColor("#161b22"),
            spaceAfter=8,
            spaceBefore=16,
            leftIndent=6,
        )

        story = []

        # Portada
        story.append(Paragraph("Reporte de Análisis de Jugadores", title_style))
        story.append(Spacer(1, 0.4 * cm))

        # Tabla de resumen
        story.append(Paragraph("Resumen Estadístico", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * cm))
        story.append(self._build_summary_table(summary, styles))
        story.append(Spacer(1, 0.6 * cm))

        # Gráficos
        for section_name, fig_dict, w_cm, h_cm in figures_config:
            story.append(Paragraph(section_name, section_style))
            story.append(Spacer(1, 0.2 * cm))

            # Reconstruir go.Figure desde dict para renderizar
            fig = go.Figure(fig_dict)
            # Ajustar altura para PDF (puede ser diferente a la interactiva)
            h_cm_clamped = min(h_cm, 22)   # máx. 22 cm en A4
            try:
                rl_img = _fig_to_rl_image(fig, width_cm=w_cm, height_cm=h_cm_clamped)
                story.append(rl_img)
            except Exception as e:
                story.append(Paragraph(
                    f"[No se pudo renderizar el gráfico: {e}]",
                    styles["Normal"],
                ))
            story.append(Spacer(1, 0.4 * cm))
            story.append(PageBreak())

        doc.build(story)
        return output_path

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _build_summary_table(self, summary: pd.DataFrame, styles) -> Table:
        """Construye una tabla ReportLab con el resumen estadístico."""
        col_map = {
            "player_id":     "Jugador",
            "dist_total_m":  "Dist. (m)",
            "speed_max_kmh": "V. máx.",
            "speed_avg_kmh": "V. prom.",
            "sprints":       "Sprints",
            "pct_moving":    "% Mov.",
        }
        extra = {
            "sprint_avg_duration_s": "Sprint prom (s)",
            "sprint_max_duration_s": "Sprint máx (s)",
        }
        cols = list(col_map.keys()) + [k for k in extra if k in summary.columns]
        headers = [col_map.get(c, extra.get(c, c)) for c in cols]

        data = [headers]
        for _, row in summary.iterrows():
            data.append([str(round(row[c], 2)) if isinstance(row[c], float) else str(row[c]) for c in cols])

        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#1a73e8")),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#f8f9fa"), colors.HexColor("#e8ecef")]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def _draw_court_plotly(
        self,
        fig: go.Figure,
        row: int | None = None,
        col: int | None = None,
        opacity: float = 1.0,
    ) -> None:
        """Dibuja la cancha de tenis sobre una figura Plotly."""
        net_y   = self._COURT_LENGTH / 2
        sv_top  = net_y - self._SERVICE_BOX
        sv_bot  = net_y + self._SERVICE_BOX
        inner_l = self._DOUBLES_ALLY
        inner_r = self._COURT_WIDTH - self._DOUBLES_ALLY
        mid_x   = self._COURT_WIDTH / 2

        kw = dict(row=row, col=col) if row else {}
        line_kw = dict(color=f"rgba(255,255,255,{opacity})", width=1.5)
        net_kw  = dict(color=f"rgba(160,200,255,{opacity})", width=2.5)

        def add_line(x0, y0, x1, y1, **extra):
            fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                          line={**line_kw, **extra}, **kw)

        def add_rect(x0, y0, x1, y1, fillcolor):
            fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(width=0),
                          fillcolor=fillcolor, **kw)

        # Fondo cancha
        add_rect(0, 0, self._COURT_WIDTH, self._COURT_LENGTH, f"rgba(58,107,53,{opacity*0.9})")
        # Cuadros de servicio
        for y0, y1 in [(sv_top, net_y), (net_y, sv_bot)]:
            add_rect(inner_l, y0, inner_r, y1, f"rgba(74,124,63,{opacity*0.9})")

        # Líneas
        # Borde exterior
        add_line(0, 0, self._COURT_WIDTH, 0, width=2.0)
        add_line(self._COURT_WIDTH, 0, self._COURT_WIDTH, self._COURT_LENGTH, width=2.0)
        add_line(self._COURT_WIDTH, self._COURT_LENGTH, 0, self._COURT_LENGTH, width=2.0)
        add_line(0, self._COURT_LENGTH, 0, 0, width=2.0)
        # Pasillos dobles
        add_line(inner_l, 0, inner_l, self._COURT_LENGTH)
        add_line(inner_r, 0, inner_r, self._COURT_LENGTH)
        # Líneas de servicio
        add_line(inner_l, sv_top, inner_r, sv_top)
        add_line(inner_l, sv_bot, inner_r, sv_bot)
        # T central
        add_line(mid_x, sv_top, mid_x, sv_bot)
        # Red
        fig.add_shape(type="line", x0=0, y0=net_y, x1=self._COURT_WIDTH, y1=net_y,
                      line=net_kw, **kw)