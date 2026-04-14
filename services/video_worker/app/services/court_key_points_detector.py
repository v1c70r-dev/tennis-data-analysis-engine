# services/video_worker/app/services/court_key_points_detector.py
import torch
import cv2
import numpy as np
from torchvision import models, transforms


class CourtKeypointDetector:
    """Encapsula carga, inferencia y visualización de keypoints de la cancha."""

    def __init__(self, model_path: str, device: int | str = "cpu"):
        self.device = device
        self.width  = None
        self.height = None

        model = models.resnet50()
        model.fc = torch.nn.Linear(model.fc.in_features, 14 * 2)
        self._load_checkpoint(model_path, model)
        model = model.to(device)
        model.eval()
        self.model = model

        self.transforms_pipeline = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def set_frame_size(self, width: int, height: int) -> None:
        """Debe llamarse una vez con las dimensiones del video antes del loop."""
        self.width  = width
        self.height = height

    #  Inferencia 
    def detect(self, frame: np.ndarray) -> np.ndarray:
        frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_tensor = self.transforms_pipeline(frame_rgb).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            kps = self.model(input_tensor).squeeze().cpu().numpy()
        kps[::2]  *= self.width  / 224.0
        kps[1::2] *= self.height / 224.0
        return kps

    #  Dibujo 
    def draw(self, frame: np.ndarray, kps: np.ndarray) -> None:
        """Dibuja los keypoints sobre el frame (in-place)."""
        for i in range(0, len(kps), 2):
            x, y = int(kps[i]), int(kps[i + 1])
            kp_idx = i // 2
            cv2.circle(frame, (x, y), radius=5, color=(0, 0, 255), thickness=-1)
            cv2.putText(frame, str(kp_idx), (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)

    #  Helpers
    @staticmethod
    def _load_checkpoint(path: str, model, optimizer=None):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        if optimizer:
            optimizer.load_state_dict(ckpt["optimizer"])

    def court_polygon(self, kps: np.ndarray) -> np.ndarray:
        """
        Construye el convex hull del court a partir de los keypoints.
        Retorna polígono (N, 1, 2) int32 listo para cv2.pointPolygonTest.
        """
        points = kps.reshape(-1, 2).astype(np.float32)
        hull   = cv2.convexHull(points)
        return hull.astype(np.int32)