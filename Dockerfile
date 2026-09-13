# Card Pulseのapplication image。APIとWorkerは同じimageを別commandで起動する
# （ADR-0001のモジュラーモノリス、ADR-0005のruntime分離）。
#
# versionの正はこのfileではない。uvのversionは`pyproject.toml`の`required-version`、
# CPythonのversionは`.python-version`、Python依存は`uv.lock`が決める。ここで固定するのは
# ADR-0014が求めるOS variantとimage digestだけで、uv自身がbuild時に`required-version`を
# 検査するため、tagとpyproject.tomlの食い違いはbuildの失敗として現れる。

FROM ghcr.io/astral-sh/uv:0.12.13-trixie-slim@sha256:4298dc3494124b50792f7abbdfe2cae7139c41f4e098f52573f4f6d912cf8bd7 AS builder

# uvが管理するCPythonとvirtual environmentを固定pathへ置き、runtime stageへそのまま複製する。
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PROJECT_ENVIRONMENT=/opt/card-pulse \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /build

# 依存の解決結果だけを先に作る。application codeを変更してもこのlayerは再利用される。
# README.mdはproject metadataの一部として宣言されているため、この段階から必要になる。
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project

# projectはeditableではなくvirtual environmentへ実体として入れる。runtime stageは
# source treeを持たないため、実行するcodeがimageの中で一意に決まる。
COPY src ./src
RUN uv sync --locked --no-dev --no-editable


FROM debian:trixie-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132 AS runtime

COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/card-pulse /opt/card-pulse

ENV PATH=/opt/card-pulse/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARD_PULSE_ARTIFACT_ROOT=/srv/card-pulse/artifacts \
    CARD_PULSE_WORKER_HEARTBEAT_PATH=/srv/card-pulse/state/worker-heartbeat.json

# 非rootで実行する。artifact用volumeはこのmount pointの所有者を引き継ぐため、
# 先にdirectoryを作ってからvolumeを割り当てる。
RUN groupadd --system --gid 10001 card-pulse \
 && useradd --system --uid 10001 --gid card-pulse \
        --home-dir /srv/card-pulse --shell /usr/sbin/nologin card-pulse \
 && mkdir -p /srv/card-pulse/artifacts /srv/card-pulse/state \
 && chown -R card-pulse:card-pulse /srv/card-pulse

USER card-pulse
WORKDIR /srv/card-pulse

# 既定のCMDは置かない。このimageは単独では起動せず、compose.yamlのcommandが
# APIとWorkerのどちらを実行するかを明示する。
