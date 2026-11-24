# TEMPLATE: Eclipse Mosquitto 2.1 MQTT Broker

Composer spec. `template.json` is the machine-readable copy.

## Service

| Field | Value |
|---|---|
| Name | Mosquitto |
| Source | repo `baranberkay96/mosquitto-railway`, root `/services/mosquitto` |
| Base | `eclipse-mosquitto:2.1.4-alpine@sha256:fa12172a…` (2026-11-17) + python3 |
| Public domain | yes, target port 8080 (railway-gateway: WebSocket pass-through to Mosquitto 127.0.0.1:9001) |
| TCP proxy | 1883 (MQTT) |
| Healthcheck | `/healthz` on `PORT` 8080 (MQTT login check), 300 s |
| Restart | ALWAYS |
| Volume | `/mosquitto/data` |

Variables: `MQTT_USERNAME` mqtt, `MQTT_PASSWORD` (secret 32), `MQTT_MAX_CONNECTIONS` -1, `PORT` 8080, `MQTT_URL`, `MQTT_PUBLIC_URL`, `MQTT_WEBSOCKET_URL`, `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` 15. No required inputs.

## Design

- `railway-mosquitto` (sh, root): validates variables (8.29), writes the password file (`mosquitto_passwd -b`) and `railway.conf` at every start (variables authoritative), chowns the volume to uid 1883, starts the healthz helper, `exec mosquitto` (drops to `mosquitto` itself).
- Listeners: 1883 MQTT (no bind address: IPv4 + IPv6) and 9001 built-in WebSockets on 127.0.0.1. `allow_anonymous false`, persistence every 300 s, `max_connections` per listener.
- `railway-gateway` (python3 asyncio, all addresses on `PORT`): WebSocket upgrades are spliced byte for byte to 127.0.0.1:9001 (Mosquitto's built-in WebSockets close plain HTTP requests without a reply, which Railway's edge shows as 502); `/healthz` performs an MQTT 3.1.1 CONNECT with the generated user and returns 200 only on CONNACK 0 (8.34: a real check); `/` returns a short text page.

## Improvements over market templates

- Market templates use unpinned images, have no healthcheck (or check an HTTP API only), and one leaves `MOSQUITTO_USERNAME` empty. This one pins 2.1.4 (with the 2.1.3 authentication fixes) by digest, enforces password auth, persists sessions, serves WSS on the HTTPS domain plus MQTT on the TCP proxy, and health-checks a real MQTT login.

## Resources

| Service | Idle RAM | Typical RAM | CPU |
|---|---|---|---|
| Mosquitto | ≈15 MB (measured, broker + gateway) | 10-100 MB (connections, retained messages) | ≈0 |

Estimated cost: well under $1/month + volume. Minimum plan: Trial.

## Verification checklist

- `/healthz` passes; anonymous CONNECT refused; wrong password refused.
- Publish/subscribe through the TCP proxy and over `wss://{domain}/mqtt`.
- Retained message survives a redeploy.
- `MQTT_PASSWORD=short` → deploy SUCCESS, user locked, warning (the healthcheck logs in with the random password, so it stays healthy; see open questions).
- `MQTT_MAX_CONNECTIONS` is set per listener (before any `listener` line Mosquitto would create a default listener on 1883 and fail with "Address in use").

## Open questions

- With a locked (invalid) password, the healthz login uses the random password it was given, so the deploy stays healthy while clients are refused; the log explains the fix.
- No TLS on the TCP proxy listener (raw TCP); WSS is the encrypted path.
