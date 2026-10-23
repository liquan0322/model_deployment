from __future__ import annotations

import argparse
import io
import logging
import os
import signal
from concurrent import futures
from pathlib import Path

import grpc
from PIL import Image, UnidentifiedImageError

from proto import copynce_descriptor_pb2 as pb2
from proto import copynce_descriptor_pb2_grpc as pb2_grpc
from server.model import DescriptorModel

LOGGER = logging.getLogger("copynce_descriptor")


class DescriptorServicer(pb2_grpc.CopyNCEDescriptorServiceServicer):
    """CopyNCE Descriptor：ExtractEmbeddings（字段对齐 SSCD，服务名独立）。"""

    def __init__(self, model: DescriptorModel) -> None:
        self.model = model

    def ExtractEmbeddings(self, request, context):  # noqa: N802
        if not request.frames:
            return pb2.ExtractResponse(
                code=pb2.CODE_NO_FRAMES,
                error="no frames in request",
            )

        images: list[Image.Image | None] = []
        results: list[pb2.FrameEmbedding] = []
        valid_indices: list[int] = []

        for frame in request.frames:
            if not frame.data:
                results.append(
                    pb2.FrameEmbedding(
                        frame_id=frame.frame_id,
                        code=pb2.CODE_EMPTY_FRAME,
                        error="empty frame data",
                    )
                )
                images.append(None)
                continue
            try:
                image = Image.open(io.BytesIO(frame.data)).convert("RGB")
            except (UnidentifiedImageError, OSError) as exc:
                results.append(
                    pb2.FrameEmbedding(
                        frame_id=frame.frame_id,
                        code=pb2.CODE_DECODE_FAILED,
                        error=f"decode failed: {exc}",
                    )
                )
                images.append(None)
                continue
            valid_indices.append(len(images))
            images.append(image)
            results.append(pb2.FrameEmbedding(frame_id=frame.frame_id, code=pb2.CODE_OK))

        try:
            if valid_indices:
                vectors = self.model.embed_images(
                    [images[i] for i in valid_indices]  # type: ignore[list-item]
                )
                for offset, index in enumerate(valid_indices):
                    results[index].values.extend(vectors[offset].tolist())
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("embed failed")
            return pb2.ExtractResponse(
                code=pb2.CODE_INTERNAL_ERROR,
                error=f"embed failed: {exc}",
            )

        return pb2.ExtractResponse(code=pb2.CODE_OK, results=results)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CopyNCE Descriptor gRPC server")
    parser.add_argument("--host", default=os.environ.get("GRPC_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("GRPC_PORT", "50051")))
    parser.add_argument(
        "--weights",
        default=os.environ.get("COPYNCE_WEIGHTS", "/weights/descriptor_vits_224.pth.tar"),
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=int(os.environ.get("COPYNCE_IMAGE_SIZE", "224")),
    )
    parser.add_argument(
        "--device",
        default=os.environ.get("COPYNCE_DEVICE", "cuda:0"),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("COPYNCE_BATCH_SIZE", "16")),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("GRPC_WORKERS", "4")),
    )
    return parser.parse_args()


def serve() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()
    weights = Path(args.weights)
    if not weights.is_file():
        raise FileNotFoundError(f"找不到权重: {weights}")

    LOGGER.info(
        "loading CopyNCE Descriptor weights=%s device=%s image_size=%s",
        weights,
        args.device,
        args.image_size,
    )
    model = DescriptorModel(
        weights=weights,
        image_size=args.image_size,
        device=args.device,
        batch_size=args.batch_size,
    )
    LOGGER.info("model ready dim=%s", model.dim)

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=args.workers),
        options=[
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ],
    )
    pb2_grpc.add_CopyNCEDescriptorServiceServicer_to_server(
        DescriptorServicer(model), server
    )
    listen = f"{args.host}:{args.port}"
    server.add_insecure_port(listen)
    server.start()
    LOGGER.info("CopyNCE Descriptor gRPC listening on %s", listen)

    stop = lambda *_: server.stop(grace=5)  # noqa: E731
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
