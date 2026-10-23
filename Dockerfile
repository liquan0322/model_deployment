# Pascal (GTX 1080 Ti / sm_61) 可用的预编译 PyTorch。
FROM pytorch/pytorch:2.14.1-cuda12.6-cudnn9-runtime

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --break-system-packages --upgrade-strategy only-if-needed \
      -r /app/requirements.txt \
    && python -c "import torch; assert torch.__version__.startswith('2.14'), torch.__version__"

COPY third_party/CopyNCE /opt/CopyNCE
COPY proto/copynce_descriptor.proto /app/proto/copynce_descriptor.proto
COPY proto/__init__.py /app/proto/__init__.py
COPY server /app/server
COPY scripts/gen_proto.sh /app/scripts/gen_proto.sh

# 按镜像内 protobuf/grpc 版本重新生成 stub，避免 gencode/runtime 不匹配。
RUN chmod +x /app/scripts/gen_proto.sh && /app/scripts/gen_proto.sh

ENV PYTHONPATH=/app:/opt/CopyNCE
ENV PYTHONUNBUFFERED=1
ENV GRPC_HOST=0.0.0.0
ENV GRPC_PORT=50051
ENV COPYNCE_WEIGHTS=/weights/descriptor_vits_224.pth.tar
ENV COPYNCE_IMAGE_SIZE=224
ENV COPYNCE_DEVICE=cuda:0
ENV COPYNCE_BATCH_SIZE=16

EXPOSE 50051
CMD ["python", "-m", "server.main"]
