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
        """
        Devuelve array de keypoints [x0,y0, x1,y1, ...] ya escalados
        a las dimensiones reales del frame.
        """
        frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_tensor = self.transforms_pipeline(frame_rgb).unsqueeze(0).to(self.device)
        kps          = self.model(input_tensor).squeeze().cpu().numpy()
        kps[::2]  *= self.width  / 224.0
        kps[1::2] *= self.height / 224.0
        return kps

    #  Dibujo 
    def draw(self, frame: np.ndarray, kps: np.ndarray) -> None:
        """Dibuja los keypoints sobre el frame (in-place)."""
        for i in range(0, len(kps), 2):
            x, y = int(kps[i]), int(kps[i + 1])
            cv2.circle(frame, (x, y), radius=5, color=(0, 255, 0), thickness=-1)

    #  Helpers
    @staticmethod
    def _load_checkpoint(path: str, model, optimizer=None):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        if optimizer:
            optimizer.load_state_dict(ckpt["optimizer"])