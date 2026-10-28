# CopyNCE Descriptor 在线服务

平行复制 `jhf/sscd` 的部署拓扑：**多副本 gRPC + 独立 nginx**。  
字段布局对齐 SSCD 的 `ExtractEmbeddings`，但 **proto / 服务名独立**：

- proto：`proto/copynce_descriptor.proto`
- 服务：`copynce_descriptor.CopyNCEDescriptorService/ExtractEmbeddings`

- **不含 Matcher**（成对打分，不进本拓扑）
- **不与 SSCD 共用** nginx / upstream / 向量库 / proto 包名
- 预处理固定在服务内（224 bicubic + ImageNet normalize + L2）

## 端口（避开 SSCD 的 59990/59991+）

| 角色 | 端口 |
|------|------|
| nginx 入口 | **49890** |
| desc1 / GPU0 | 49891 |
| desc2 / GPU1 | 49892 |
| desc3 / GPU2 | 49893 |

## 目录

```
copynce_descriptor/
  Dockerfile
  docker-compose.yml
  nginx/nginx.conf          # compose 内 nginx
  nginx/nginx.host.conf     # 宿主机 nginx 示例
  proto/                    # 独立 proto（copynce_descriptor）
  server/                   # gRPC 服务 + CopyNCE 加载
  weights/                  # descriptor_vits_224.pth.tar
  third_party/CopyNCE/      # 构建时需要（见下方）
  client.py
```

## 准备

```bash
cd /home/lan/epg/zsn/copynce_descriptor

# 1) CopyNCE 源码（若目录为空）
rsync -a --exclude '.git' ../model_test/third_party/CopyNCE/ third_party/CopyNCE/

# 2) 权重
cp -n ../model_test/data/weights/descriptor_vits_224.pth.tar weights/ \
  || ./scripts/download_weights.sh
```

## 启动

一键启停（启动时会先停 AnyPattern，避免抢 GPU）：

```bash
./scripts/start.sh
./scripts/stop.sh
# 或在 zsn/ 下：../switch_feature_service.sh copynce|anypattern|stop|status
```

手动：

```bash
docker compose build
docker compose up -d
docker compose ps
```

单副本调试：

```bash
docker compose up -d desc1
python client.py --server localhost:49891 /path/to/a.jpg
```

经 nginx：

```bash
python client.py --server localhost:49890 /path/to/a.jpg /path/to/b.jpg
```

## 下游向量库

使用独立 collection / index（与 SSCD 隔离）。本服务返回 **L2 归一化** float 向量，维度以实际响应 `len(values)` 为准（ViT-S Descriptor）。

## 与 SSCD 对照

| | SSCD | CopyNCE Descriptor |
|--|------|-------------------|
| 入口 | :59990 | :49890 |
| proto | `sscd.SSCDService` | `copynce_descriptor.CopyNCEDescriptorService` |
| RPC | ExtractEmbeddings | ExtractEmbeddings（字段对齐） |
| 镜像 | sscdrec:mask | copynce-descriptor:latest |
| 预处理 | SSCD 自有 | CopyNCE 224 bicubic |
| Matcher | — | **不上** |
