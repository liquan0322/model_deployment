#!/usr/bin/env python3
"""CopyNCE Descriptor gRPC 客户端（独立 proto，非 SSCD 服务名）。"""

from __future__ import annotations

import argparse
import sys

import grpc

from proto import copynce_descriptor_pb2 as pb2
from proto import copynce_descriptor_pb2_grpc as pb2_grpc


def run(server_addr: str, image_paths: list[str]) -> None:
    channel = grpc.insecure_channel(
        server_addr,
        options=[
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ],
    )
    stub = pb2_grpc.CopyNCEDescriptorServiceStub(channel)

    frames = []
    for index, path in enumerate(image_paths):
        with open(path, "rb") as handle:
            frames.append(pb2.FrameData(frame_id=index, data=handle.read()))

    response = stub.ExtractEmbeddings(pb2.ExtractRequest(frames=frames))
    if response.code != pb2.CODE_OK:
        print(f"Request failed (code={response.code}): {response.error}", file=sys.stderr)
        sys.exit(1)

    for result in response.results:
        if result.code == pb2.CODE_OK:
            print(
                f"frame_id={result.frame_id}: dim={len(result.values)}, "
                f"first5={list(result.values)[:5]}"
            )
        else:
            print(f"frame_id={result.frame_id}: code={result.code} error={result.error}")
    channel.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CopyNCE Descriptor gRPC client")
    parser.add_argument(
        "--server",
        default="localhost:49890",
        help="gRPC 地址（nginx 默认 localhost:49890；单副本 localhost:49891）",
    )
    parser.add_argument("images", nargs="+", help="图片路径")
    args = parser.parse_args()
    run(args.server, args.images)


if __name__ == "__main__":
    main()
