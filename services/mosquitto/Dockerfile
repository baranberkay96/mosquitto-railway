# syntax=docker/dockerfile:1
#
# Eclipse Mosquitto 2.1.4 for Railway.
#
# Base: the official eclipse-mosquitto image (Alpine), multi-arch index
# digest checked 2026-11-24. Added: python3 for the private /healthz that
# Railway's healthcheck uses (it logs in over MQTT with the generated user).
FROM eclipse-mosquitto:2.1.4-alpine@sha256:fa12172a051310efe5bcb7a6a11b77bd5faacb82cbacd7742aa758bf024fd8e4

RUN apk add --no-cache python3

COPY --chmod=0755 railway-mosquitto.sh /usr/local/bin/railway-mosquitto
COPY --chmod=0755 railway-healthz.py /usr/local/bin/railway-healthz

ENV PORT=8081
EXPOSE 1883 8080 8081

ENTRYPOINT ["/usr/local/bin/railway-mosquitto"]
