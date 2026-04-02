import cv2
import numpy as np


# Posiciones normalizadas de cada keypoint en la cancha real
# (x, y) en metros, origen en kp0 (esquina superior izquierda)
# Cancha dobles: 23.77m largo x 10.97m ancho
_COURT_WIDTH  = 10.97
_COURT_LENGTH = 23.77
_SERVICE_BOX  = 6.40   # distancia de la red a la línea de servicio
_DOUBLES_ALLY = 1.37   # ancho del pasillo de dobles

_KP_REAL_COORDS = {
    # Esquinas externas
    0:  (0.0,                        0.0),
    1:  (_COURT_WIDTH,               0.0),
    2:  (0.0,                        _COURT_LENGTH),
    3:  (_COURT_WIDTH,               _COURT_LENGTH),
    # Líneas de dobles internas (separación de pasillo)
    4:  (_DOUBLES_ALLY,              0.0),
    5:  (_DOUBLES_ALLY,              _COURT_LENGTH),
    6:  (_COURT_WIDTH - _DOUBLES_ALLY, 0.0),
    7:  (_COURT_WIDTH - _DOUBLES_ALLY, _COURT_LENGTH),
    # Líneas de servicio
    8:  (_DOUBLES_ALLY,              _COURT_LENGTH / 2 - _SERVICE_BOX),
    9:  (_COURT_WIDTH - _DOUBLES_ALLY, _COURT_LENGTH / 2 - _SERVICE_BOX),
    10: (_DOUBLES_ALLY,              _COURT_LENGTH / 2 + _SERVICE_BOX),
    11: (_COURT_WIDTH - _DOUBLES_ALLY, _COURT_LENGTH / 2 + _SERVICE_BOX),
    # Centro de la red
    12: (_COURT_WIDTH / 2,           _COURT_LENGTH / 2 - _SERVICE_BOX),
    13: (_COURT_WIDTH / 2,           _COURT_LENGTH / 2 + _SERVICE_BOX),
}


class MiniCourt:
    """
    Dibuja una minicancha cenital en una esquina del frame,
    proyectando jugadores usando homografía desde los keypoints del court.
    """

    # Colores jugadores (mismos que PlayerTracker para consistencia)
    _PLAYER_COLORS = [
        (255, 100, 0), (0, 200, 255), (0, 255, 100),
        (200, 0, 255), (255, 200, 0), (0, 100, 255),
    ]

    def __init__(
        self,
        origin: tuple[int, int] = (20, None),  # None se calcula en set_frame_size
        width:  int = 150,
        height: int = 280,
        margin: int = 20,
    ):
        self.width   = width
        self.height  = height
        self.margin  = margin
        self._origin = origin          # (x, y) esquina superior izquierda del rectángulo
        self._H      = None            # homografía imagen minicancha

    def set_frame_size(self, frame_height: int) -> None:
        """Calcula la posición vertical si origin[1] es None (anclar al fondo)."""
        x, y = self._origin
        if y is None:
            y = frame_height - self.height - self.margin
        self._origin = (x, y)

    def set_court_reference(self, kps: np.ndarray) -> None:
        """
        Calcula la homografía entre los keypoints de imagen y la minicancha.
        Debe llamarse una vez con los keypoints del primer frame.
        """
        ox, oy = self._origin
        pad    = self.margin

        # Escala metros pixels dentro del rectángulo de la minicancha
        scale_x = (self.width  - 2 * pad) / _COURT_WIDTH
        scale_y = (self.height - 2 * pad) / _COURT_LENGTH

        # Puntos fuente (imagen) y destino (minicancha) para la homografía
        src_pts, dst_pts = [], []
        for kp_idx, (rx, ry) in _KP_REAL_COORDS.items():
            ix = kps[kp_idx * 2]
            iy = kps[kp_idx * 2 + 1]
            mx = ox + pad + rx * scale_x
            my = oy + pad + ry * scale_y
            src_pts.append([ix, iy])
            dst_pts.append([mx, my])

        src = np.array(src_pts, dtype=np.float32)
        dst = np.array(dst_pts, dtype=np.float32)
        self._H, _ = cv2.findHomography(src, dst, cv2.RANSAC)

    def project_point(self, x: float, y: float) -> tuple[int, int] | None:
        """Proyecta un punto de imagen a coordenadas de minicancha."""
        if self._H is None:
            return None
        pt  = np.array([[[x, y]]], dtype=np.float32)
        out = cv2.perspectiveTransform(pt, self._H)
        return int(out[0][0][0]), int(out[0][0][1])

    def draw(
        self,
        frame:       np.ndarray,
        player_rows: list[dict],
    ) -> None:
        """
        Dibuja la minicancha y proyecta los jugadores (in-place).
        player_rows: filas del frame actual del PlayerTracker.
        """
        self._draw_court(frame)
        self._draw_players(frame, player_rows)

    #  Helpers  

    def _draw_court(self, frame: np.ndarray) -> None:
        """Dibuja el rectángulo y las líneas de la cancha."""
        ox, oy = self._origin
        pad    = self.margin
        scale_x = (self.width  - 2 * pad) / _COURT_WIDTH
        scale_y = (self.height - 2 * pad) / _COURT_LENGTH

        def mp(rx, ry):  # metros pixel en minicancha
            return (
                int(ox + pad + rx * scale_x),
                int(oy + pad + ry * scale_y),
            )

        # Fondo semitransparente
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (ox, oy), (ox + self.width, oy + self.height),
            (30, 30, 30), -1,
        )
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        c = (200, 200, 200)  # color líneas
        t = 1                # grosor

        # Borde externo (dobles)
        cv2.rectangle(frame, mp(0, 0), mp(_COURT_WIDTH, _COURT_LENGTH), c, t)

        # Líneas de singles (pasillos)
        cv2.line(frame, mp(_DOUBLES_ALLY, 0),              mp(_DOUBLES_ALLY, _COURT_LENGTH),              c, t)
        cv2.line(frame, mp(_COURT_WIDTH - _DOUBLES_ALLY, 0), mp(_COURT_WIDTH - _DOUBLES_ALLY, _COURT_LENGTH), c, t)

        # Red (centro)
        net_y = _COURT_LENGTH / 2
        cv2.line(frame, mp(0, net_y), mp(_COURT_WIDTH, net_y), (100, 200, 255), 2)

        # Líneas de servicio
        sv_top = net_y - _SERVICE_BOX
        sv_bot = net_y + _SERVICE_BOX
        cv2.line(frame, mp(_DOUBLES_ALLY, sv_top), mp(_COURT_WIDTH - _DOUBLES_ALLY, sv_top), c, t)
        cv2.line(frame, mp(_DOUBLES_ALLY, sv_bot), mp(_COURT_WIDTH - _DOUBLES_ALLY, sv_bot), c, t)

        # Centro de la línea de servicio (T)
        cv2.line(frame, mp(_COURT_WIDTH / 2, sv_top), mp(_COURT_WIDTH / 2, sv_bot), c, t)

    def _draw_players(self, frame: np.ndarray, player_rows: list[dict]) -> None:
        """Proyecta y dibuja cada jugador en la minicancha."""
        for row in player_rows:
            pt = self.project_point(row["cx"], row["cy"])
            if pt is None:
                continue
            pid   = row["player_id"]
            color = self._PLAYER_COLORS[pid % len(self._PLAYER_COLORS)]
            cv2.circle(frame, pt, radius=6, color=color, thickness=-1)
            cv2.putText(
                frame, f"P{pid}",
                (pt[0] + 7, pt[1] + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
            )