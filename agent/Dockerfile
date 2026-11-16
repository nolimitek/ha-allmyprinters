# AllMyPrinters Agent as a Home Assistant app: the same image as the Docker install (ghcr.io/nolimitek/allmyprinters-agent),
# version = version in config.yaml (Home Assistant passes it as BUILD_VERSION). The agent reads /data/options.json itself.
ARG BUILD_VERSION=latest
FROM ghcr.io/nolimitek/allmyprinters-agent:${BUILD_VERSION}
# The app's /data belongs to root
USER root
ENV AMP_DATA=/data AMP_PORT=8090
