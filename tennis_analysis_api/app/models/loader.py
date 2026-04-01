import torch
from torchvision import models
from ultralytics import YOLO
from app.config import settings


def load_kps_model():
    device = torch.device(settings.device if settings.device != "0" else "cuda:0")
    model = models.resnet50()
    model.fc = torch.nn.Linear(model.fc.in_features, 14 * 2)
    ckpt = torch.load(settings.kps_model_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model"])
    model = model.to(device)
    model.eval()
    return model


def load_all_models():
    return {
        "kps_model":      load_kps_model(),
        "ball_model":     YOLO(settings.ball_model_path),
        "players_model":  YOLO(settings.players_model_path),
    }