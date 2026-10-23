from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from omegaconf import OmegaConf
from PIL import Image
from torchvision import transforms
from torchvision.transforms import InterpolationMode


def _ensure_copynce_path() -> None:
    candidates = [
        Path("/opt/CopyNCE"),
        Path(__file__).resolve().parents[1] / "third_party" / "CopyNCE",
    ]
    for root in candidates:
        if (root / "core").is_dir():
            path = str(root)
            if path not in sys.path:
                sys.path.insert(0, path)
            return
    raise RuntimeError("找不到 CopyNCE 源码（/opt/CopyNCE 或 third_party/CopyNCE）")


class DescriptorModel:
    """CopyNCE Descriptor：单图 → L2 归一化向量（与 model_test 评测预处理一致）。"""

    def __init__(
        self,
        weights: Path,
        image_size: int = 224,
        device: str = "cuda:0",
        batch_size: int = 16,
    ) -> None:
        _ensure_copynce_path()
        from core.configs import __default_config_factory__
        from core.models.build import build_copy_descriptor
        from core.utils.serialization import load_weights

        cfg = OmegaConf.create(__default_config_factory__["descriptor"])
        cfg.input.img_size = image_size
        self.device = torch.device(device)
        self.batch_size = max(1, batch_size)
        self.image_size = image_size
        self.model = build_copy_descriptor(cfg)

        checkpoint = torch.load(weights, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            load_weights(self.model, checkpoint, key="model")
        else:
            load_weights(self.model, {"model": checkpoint}, key="model")

        self.model.to(self.device).eval()
        self.preprocess = transforms.Compose(
            [
                transforms.Resize(
                    (image_size, image_size),
                    interpolation=InterpolationMode.BICUBIC,
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        with torch.no_grad():
            dummy = Image.new("RGB", (image_size, image_size), (0, 0, 0))
            self.dim = int(self.embed_images([dummy]).shape[-1])

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        if not images:
            return np.zeros((0, getattr(self, "dim", 0)), dtype=np.float32)

        outputs: list[np.ndarray] = []
        for start in range(0, len(images), self.batch_size):
            chunk = images[start : start + self.batch_size]
            batch = torch.stack([self.preprocess(image.convert("RGB")) for image in chunk])
            if self.device.type == "cuda":
                batch = batch.pin_memory().to(self.device, non_blocking=True)
            else:
                batch = batch.to(self.device)
            with torch.no_grad():
                out = self.model({"images": batch})
                feat = out.get("feat", out["cls_token"])
                feat = F.normalize(feat.float(), dim=1)
            outputs.append(feat.detach().cpu().numpy().astype(np.float32))
        return np.concatenate(outputs, axis=0)
