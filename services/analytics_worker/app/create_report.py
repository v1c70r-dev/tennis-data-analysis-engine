#services/analytics_worker/app/create_report.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.ndimage import gaussian_filter
import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    PageBreak,
)
import numpy as np
from services.analytics_worker.app.player_stats_analysis import PlayerStatsAnalysis


#  Helper 
def _fig_to_rl_image(fig: plt.Figure, width_cm: float, height_cm: float) -> RLImage:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return RLImage(buf, width=width_cm * cm, height=height_cm * cm)


class PlayerStatsCreateReport(PlayerStatsAnalysis):
    """
    Extiende PlayerStatsAnalysis añadiendo renderizado matplotlib
    y exportación a PDF con ReportLab.

    No duplica lógica de datos — toda la fuente de verdad está en
    PlayerStatsAnalysis (summarize, plot_*, get_dashboard_data, etc.)
    """

    def get_color(self, i: int) -> str:
        """Alias para _player_color heredado."""
        from services.analytics_worker.app.player_stats_analysis import _player_color
        return _player_color(i)

    # ------------------------------------------------------------------
    # Cancha matplotlib
    # ------------------------------------------------------------------

    def draw_court_matplotlib(self, ax, margin: float = 1.5) -> None:
        net_y   = self._COURT_LENGTH / 2
        sv_top  = net_y - self._SERVICE_BOX
        sv_bot  = net_y + self._SERVICE_BOX
        inner_l = self._DOUBLES_ALLY
        inner_r = self._COURT_WIDTH - self._DOUBLES_ALLY
        mid_x   = self._COURT_WIDTH / 2

        ax.set_facecolor("#0f3d0f")
        ax.add_patch(plt.Rectangle(
            (0, 0), self._COURT_WIDTH, self._COURT_LENGTH,
            facecolor="#3a6b35", zorder=0,
        ))
        for y0, y1 in [(sv_top, net_y), (net_y, sv_bot)]:
            ax.add_patch(plt.Rectangle(
                (inner_l, y0), inner_r - inner_l, y1 - y0,
                facecolor="#4a7c3f", zorder=1,
            ))

        kw     = dict(color="white", linewidth=1.2, alpha=0.9, zorder=3)
        kw2    = dict(color="white", linewidth=2.0, alpha=0.95, zorder=3)
        kw_net = dict(color="#a0c8ff", linewidth=2.5, zorder=4)

        ax.plot([0, self._COURT_WIDTH, self._COURT_WIDTH, 0, 0],
                [0, 0, self._COURT_LENGTH, self._COURT_LENGTH, 0], **kw2)
        ax.plot([inner_l, inner_l], [0, self._COURT_LENGTH], **kw)
        ax.plot([inner_r, inner_r], [0, self._COURT_LENGTH], **kw)
        ax.plot([inner_l, inner_r], [sv_top, sv_top], **kw)
        ax.plot([inner_l, inner_r], [sv_bot, sv_bot], **kw)
        ax.plot([mid_x, mid_x], [sv_top, sv_bot], **kw)
        ax.plot([0, self._COURT_WIDTH], [net_y, net_y], **kw_net)
        ax.plot(mid_x, net_y, "o", color="#a0c8ff", markersize=3, zorder=5)
        ax.plot([mid_x - 0.15, mid_x + 0.15], [0, 0], **kw2)
        ax.plot([mid_x - 0.15, mid_x + 0.15],
                [self._COURT_LENGTH] * 2, **kw2)

        ax.set_xlim(-margin, self._COURT_WIDTH + margin)
        ax.set_ylim(-margin, self._COURT_LENGTH + margin)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=7)

    # ------------------------------------------------------------------
    # Gráficos matplotlib (mismos nombres que los de Plotly pero retornan fig)
    # ------------------------------------------------------------------

    def mpl_player_speeds(self, expresed_in_time: bool = False) -> plt.Figure:
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        n       = len(players)
        fig, axes = plt.subplots(n, 1, figsize=(12, 3.5 * n), sharex=True)
        if n == 1:
            axes = [axes]

        for ax, pid in zip(axes, players):
            grp   = df[df["player_id"] == pid].sort_values("frame").copy()
            x     = grp["frame"] / self.fps if expresed_in_time and self.fps > 0 else grp["frame"]
            x_label = "Tiempo (s)" if expresed_in_time and self.fps > 0 else "Frame"
            color = self.get_color(players.index(pid))

            ax.fill_between(x, grp["speed_kmh"].fillna(0), alpha=0.15, color=color)
            ax.plot(x, grp["speed_kmh"], color=color, linewidth=1.5,
                    label=f"Jugador {pid}")
            ax.axhline(self.SPRINT_THRESHOLD_KMH, color="#E24B4A",
                       linewidth=0.9, linestyle="--", alpha=0.6)
            ax.text(x.iloc[-1], self.SPRINT_THRESHOLD_KMH + 0.5,
                    f"Sprint {self.SPRINT_THRESHOLD_KMH}km/h",
                    color="#E24B4A", fontsize=8, ha="right")
            ax.set_ylabel("Velocidad (km/h)", fontsize=10)
            ax.set_title(f"Jugador {pid} — Perfil de Velocidad",
                         fontsize=11, fontweight="600")
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", alpha=0.2, linestyle=":")

        axes[-1].set_xlabel(x_label, fontsize=10)
        fig.suptitle("Análisis de Velocidad Instantánea",
                     fontsize=14, fontweight="700", y=1.01)
        plt.tight_layout()
        return fig

    def mpl_speed_distribution(self) -> plt.Figure:
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        fig, axes = plt.subplots(1, len(players),
                                 figsize=(5 * len(players), 4), sharey=False)
        if len(players) == 1:
            axes = [axes]

        for ax, pid in zip(axes, players):
            grp    = df[df["player_id"] == pid].dropna(subset=["speed_kmh"])
            counts, _ = np.histogram(grp["speed_kmh"], bins=self.SPEED_BINS)
            pcts   = counts / counts.sum() * 100
            color  = self.get_color(players.index(pid))
            bars   = ax.bar(self.SPEED_LABELS, pcts, color=color,
                            alpha=0.85, width=0.6, zorder=3)
            for bar, pct in zip(bars, pcts):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5,
                        f"{pct:.1f}%", ha="center", fontsize=9, color="#444")
            ax.set_xlabel("Rango (km/h)", fontsize=10)
            ax.set_ylabel("% de frames", fontsize=10)
            ax.set_title(f"Jugador {pid}", fontsize=11)
            ax.set_ylim(0, max(pcts) * 1.2 + 2)

        fig.suptitle("Distribución de velocidad", fontsize=13, fontweight="500")
        plt.tight_layout()
        return fig

    def mpl_cumulative_distance(self, expresed_in_time: bool = False) -> plt.Figure:
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        fig, ax = plt.subplots(figsize=(12, 4))

        for pid in players:
            grp = df[df["player_id"] == pid].sort_values("frame").copy()
            grp["cumul_dist"] = grp["dist_meters"].fillna(0).cumsum()
            x       = grp["frame"] / self.fps if expresed_in_time and self.fps > 0 else grp["frame"]
            x_label = "Tiempo (s)" if expresed_in_time and self.fps > 0 else "Frame"
            color   = self.get_color(players.index(pid))
            total   = grp["cumul_dist"].iloc[-1]

            ax.plot(x, grp["cumul_dist"], color=color, linewidth=2,
                    label=f"Jugador {pid}  ({total:.1f} m)")
            ax.annotate(f"{total:.1f} m",
                        xy=(x.iloc[-1], total),
                        xytext=(6, 0), textcoords="offset points",
                        fontsize=8.5, color=color, va="center", fontweight="600")

        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel("Distancia acumulada (m)", fontsize=10)
        ax.set_title("Distancia acumulada a lo largo del partido",
                     fontsize=12, fontweight="600")
        ax.legend(fontsize=10)
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        plt.tight_layout()
        return fig

    def mpl_metric_comparison_A(self, summary: pd.DataFrame) -> plt.Figure:
        players = sorted(summary["player_id"].dropna().unique().astype(int).tolist())
        base_metrics = [
            ("dist_total_m",  "Distancia total", "m"),
            ("speed_max_kmh", "Vel. máxima",     "km/h"),
            ("speed_avg_kmh", "Vel. promedio",   "km/h"),
            ("sprints",       "Sprints",         ""),
            ("pct_moving",    "Tiempo en movimiento", "%"),
        ]
        extra_metrics = [
            ("sprint_avg_duration_s", "Duración prom. sprint", "s"),
            ("sprint_max_duration_s", "Duración máx. sprint",  "s"),
        ]
        metrics  = base_metrics + [m for m in extra_metrics if m[0] in summary.columns]
        ncols    = 4
        nrows    = (len(metrics) + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(ncols * 3.2, nrows * 3.8))
        axes = axes.flatten()
        player_colors = [self.get_color(i) for i in range(len(players))]

        for ax_i, (col, label, unit) in enumerate(metrics):
            ax   = axes[ax_i]
            ymax = summary[col].max()
            ax.set_ylim(0, ymax * 1.18 if ymax > 0 else 1)

            for i, pid in enumerate(players):
                val = float(summary[summary["player_id"] == pid].iloc[0][col])
                ax.bar(i, val, color=player_colors[i], alpha=0.85, zorder=3)
                ax.text(i, val + ymax * 0.02, f"{val:.1f}",
                        ha="center", va="bottom", fontsize=8.5, color="#333")

            ylabel = f"{label} ({unit})" if unit else label
            ax.set_ylabel(ylabel, fontsize=8.5)
            ax.set_title(label, fontsize=9.5, fontweight="500", pad=6)
            ax.set_xticks(range(len(players)))
            ax.set_xticklabels([f"J{p}" for p in players], fontsize=9)
            ax.grid(axis="y", alpha=0.18, linestyle="--")
            ax.set_axisbelow(True)

        for j in range(len(metrics), len(axes)):
            axes[j].set_visible(False)

        handles = [plt.Rectangle((0, 0), 1, 1, color=player_colors[i], alpha=0.85)
                   for i in range(len(players))]
        fig.legend(handles, [f"Jugador {p}" for p in players],
                   loc="lower right", fontsize=9,
                   bbox_to_anchor=(0.98, 0.01), framealpha=0.7)
        fig.suptitle("Comparación de métricas por jugador",
                     fontsize=13, fontweight="600", y=1.01)
        plt.tight_layout()
        return fig

    def mpl_metric_comparison_B(self, summary: pd.DataFrame) -> plt.Figure:
        players = sorted(summary["player_id"].dropna().unique().astype(int).tolist())
        base_metrics = [
            ("dist_total_m",  "Distancia\ntotal"),
            ("speed_max_kmh", "Vel.\nmáxima"),
            ("speed_avg_kmh", "Vel.\npromedio"),
            ("sprints",       "Sprints"),
            ("pct_moving",    "% tiempo\nmovimiento"),
        ]
        extra_metrics = [
            ("sprint_avg_duration_s", "Sprint\nprom. (s)"),
            ("sprint_max_duration_s", "Sprint\nmáx. (s)"),
        ]
        metrics  = base_metrics + [m for m in extra_metrics if m[0] in summary.columns]
        cols     = [m[0] for m in metrics]
        labels   = [m[1] for m in metrics]
        N        = len(metrics)
        angles   = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles  += angles[:1]
        maxvals  = summary[cols].max()
        norm_df  = summary[cols].div(maxvals.replace(0, 1)).mul(100)

        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_rlim(0, 110)
        ax.set_rticks([25, 50, 75, 100])
        ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7.5, color="gray")
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9.5)
        ax.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.4)
        ax.spines["polar"].set_visible(False)

        unit_map = {
            "dist_total_m": "m", "speed_max_kmh": "km/h", "speed_avg_kmh": "km/h",
            "sprints": "", "pct_moving": "%",
            "sprint_avg_duration_s": "s", "sprint_max_duration_s": "s",
        }
        for i, pid in enumerate(players):
            values   = norm_df[summary["player_id"] == pid].iloc[0][cols].tolist()
            values  += values[:1]
            color    = self.get_color(i)
            real_row = summary[summary["player_id"] == pid].iloc[0]

            ax.plot(angles, values, color=color, linewidth=2,
                    zorder=3, label=f"Jugador {pid}")
            ax.fill(angles, values, color=color, alpha=0.12)

            for angle, val_norm, col in zip(angles[:-1], values[:-1], cols):
                real_val = real_row[col]
                unit     = unit_map.get(col, "")
                fmt      = f"{real_val:.0f}{unit}" if unit else f"{real_val:.0f}"
                r_offset = val_norm + 4 + i * 6
                ax.annotate(fmt, xy=(angle, val_norm),
                            xytext=(angle, r_offset),
                            fontsize=7.5, color=color, ha="center", va="center")
                ax.plot(angle, val_norm, "o", color=color, markersize=5, zorder=4)

        ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12),
                  fontsize=10, framealpha=0.7)
        ax.set_title("Perfil de rendimiento relativo por jugador\n"
                     "(normalizado al máximo del grupo)",
                     fontsize=11, fontweight="600", pad=20)
        plt.tight_layout()
        return fig

    def mpl_trajectories_combined(self, flip_view: bool = False) -> plt.Figure:
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        fig, ax = plt.subplots(figsize=(6.5, 10.5))
        self.draw_court_matplotlib(ax, margin=2.0)

        cmap     = plt.cm.plasma
        v_max    = df["speed_kmh"].max(skipna=True)
        norm     = mcolors.Normalize(vmin=0, vmax=max(v_max, 1))

        for pid in players:
            grp = (df[df["player_id"] == pid]
                   .dropna(subset=["mx", "my"])
                   .sort_values("frame"))
            if grp.empty:
                continue
            xs     = grp["mx"].values
            ys     = grp["my"].values
            speeds = grp["speed_kmh"].fillna(0).values

            for i in range(1, len(xs)):
                ax.plot([xs[i-1], xs[i]], [ys[i-1], ys[i]],
                        color=cmap(norm(speeds[i])),
                        linewidth=1.8, alpha=0.82, zorder=6)

            ax.scatter(xs[0],  ys[0],  color="#00ff88", s=75, zorder=8,
                       marker="o", edgecolors="white", linewidths=0.8)
            ax.scatter(xs[-1], ys[-1], color="#ff4444", s=75, zorder=8,
                       marker="o", edgecolors="white", linewidths=0.8)
            ax.text(xs[0] + 0.25, ys[0] + 0.25, f"J{pid}",
                    fontsize=9, fontweight="bold", color="white", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#111",
                              alpha=0.7, edgecolor="none"))
            d_total = grp["dist_meters"].sum()
            ax.plot([], [], color="white", linewidth=2.5,
                    label=f"J{pid}  |  {d_total:.0f} m  |  v_max {speeds.max():.1f} km/h")

        ax.scatter([], [], color="#00ff88", s=55, marker="o",
                   edgecolors="white", linewidths=0.5, label="Inicio")
        ax.scatter([], [], color="#ff4444", s=55, marker="o",
                   edgecolors="white", linewidths=0.5, label="Fin")
        ax.legend(fontsize=8, loc="lower left",
                  facecolor="#1a1a1a", labelcolor="white",
                  edgecolor="#555", framealpha=0.85)

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label="km/h", fraction=0.025, pad=0.02)

        ax.set_xlabel("Ancho (m)", fontsize=9)
        ax.set_ylabel("Largo (m)", fontsize=9)
        ax.set_title("Trayectoria real coloreada por velocidad",
                     fontsize=11, fontweight="600", pad=8)
        if flip_view:
            ax.invert_yaxis()
        plt.tight_layout()
        return fig

    def mpl_heatmaps_combined(self, flip_view: bool = False) -> plt.Figure:
        df      = self.df
        players = sorted(df["player_id"].dropna().unique().astype(int).tolist())
        margin  = 2.0
        bins    = 50
        sigma   = 1.5
        x_min, x_max = -margin, self._COURT_WIDTH  + margin
        y_min, y_max = -margin, self._COURT_LENGTH + margin

        fig, ax = plt.subplots(figsize=(6.5, 10.5))
        self.draw_court_matplotlib(ax, margin=margin)

        for idx, pid in enumerate(players):
            grp = df[df["player_id"] == pid].dropna(subset=["mx", "my"])
            if grp.empty:
                continue
            heatmap, xedges, yedges = np.histogram2d(
                grp["mx"].values, grp["my"].values,
                bins=bins, range=[[x_min, x_max], [y_min, y_max]],
            )
            heatmap = gaussian_filter(heatmap.T, sigma=sigma)
            heatmap = heatmap / heatmap.max()
            heatmap_masked = np.ma.masked_where(heatmap < 0.01, heatmap)

            ax.imshow(heatmap_masked, origin="lower",
                      extent=[x_min, x_max, y_min, y_max],
                      cmap="hot", alpha=0.55, aspect="auto",
                      vmin=0, vmax=1, zorder=5 + idx)

            iy, ix = np.unravel_index(np.argmax(heatmap), heatmap.shape)
            peak_x = xedges[ix] + (xedges[1] - xedges[0]) / 2
            peak_y = yedges[iy] + (yedges[1] - yedges[0]) / 2
            ax.scatter(peak_x, peak_y, color="white", s=80,
                       marker="x", linewidths=2, zorder=10 + idx)
            ax.text(peak_x + 0.25, peak_y + 0.25, f"J{pid}",
                    fontsize=9, fontweight="bold", color="white",
                    zorder=12 + idx,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#111",
                              alpha=0.7, edgecolor="none"))

        sm = plt.cm.ScalarMappable(
            cmap="hot", norm=mcolors.Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
        cbar.set_label("Densidad relativa", fontsize=8)
        cbar.set_ticks([0, 0.5, 1])
        cbar.set_ticklabels(["Baja", "Media", "Alta"])

        ax.set_xlabel("Ancho (m)", fontsize=9)
        ax.set_ylabel("Largo (m)", fontsize=9)
        ax.set_title("Mapa de calor — posiciones en cancha",
                     fontsize=11, fontweight="600", pad=8)
        if flip_view:
            ax.invert_yaxis()
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def export_pdf(
        self,
        output_path: str = "player_stats_report.pdf",
        expresed_in_time: bool = False,
        flip_view: bool = False,
    ) -> str:
        summary   = self.summarize(expresed_in_time)
        n_players = len(self.df["player_id"].dropna().unique())

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=1.5*cm, rightMargin=1.5*cm,
            topMargin=1.5*cm,  bottomMargin=1.5*cm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle", parent=styles["Title"],
            fontSize=20, textColor=colors.HexColor("#1a73e8"), spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "SectionTitle", parent=styles["Heading2"],
            fontSize=13, textColor=colors.HexColor("#333333"),
            spaceAfter=8, spaceBefore=16, leftIndent=6,
        )

        story = [
            Paragraph("Reporte de Análisis de Jugadores", title_style),
            Spacer(1, 0.4*cm),
            Paragraph("Resumen Estadístico", styles["Heading2"]),
            Spacer(1, 0.2*cm),
            self._build_summary_table(summary, styles),
            Spacer(1, 0.6*cm),
        ]

        figures_config = [
            ("Perfil de Velocidad",              lambda: self.mpl_player_speeds(expresed_in_time),    16, min(3.5 * n_players, 22)),
            ("Distribución de Velocidad",        lambda: self.mpl_speed_distribution(),               16, 6),
            ("Distancia Acumulada",              lambda: self.mpl_cumulative_distance(expresed_in_time), 16, 6),
            ("Comparación de Métricas (barras)", lambda: self.mpl_metric_comparison_A(summary),       16, 10),
            ("Comparación de Métricas (radar)",  lambda: self.mpl_metric_comparison_B(summary),       14, 14),
            ("Trayectorias en Cancha",           lambda: self.mpl_trajectories_combined(flip_view),   12, 18),
            ("Mapa de Calor",                    lambda: self.mpl_heatmaps_combined(flip_view),       12, 18),
        ]

        for section_name, fig_fn, w_cm, h_cm in figures_config:
            story.append(Paragraph(section_name, section_style))
            story.append(Spacer(1, 0.2*cm))
            try:
                fig = fig_fn()
                story.append(_fig_to_rl_image(fig, w_cm, h_cm))
            except Exception as e:
                story.append(Paragraph(
                    f"[No se pudo renderizar: {e}]", styles["Normal"]))
            story.append(Spacer(1, 0.4*cm))
            story.append(PageBreak())

        doc.build(story)
        return output_path