# NOTICE: Eclipse Mosquitto template

This is a community template. It is not made, endorsed or supported by the Eclipse Foundation or Railway. Eclipse Mosquitto is a trademark of the Eclipse Foundation.

## Components

| Component | Source | License | How it is used |
|---|---|---|---|
| Eclipse Mosquitto 2.1.4 (`eclipse-mosquitto:2.1.4-alpine@sha256:fa12172a051310efe5bcb7a6a11b77bd5faacb82cbacd7742aa758bf024fd8e4`) | https://github.com/eclipse-mosquitto/mosquitto | EPL-2.0 or EDL-1.0 (BSD-3-Clause), per the image label `EPL-2.0 OR BSD-3-Clause` | Official image as the base; `python3` added from Alpine |

## Files written for this template

`services/mosquitto/Dockerfile`, `railway-mosquitto.sh`, `railway-gateway.py` (WebSocket pass-through and MQTT 3.1.1 CONNECT healthcheck, written for this template) and the documentation were written for this template and are offered under the MIT License.

## Upstream files checked (tag v2.1.4)

- `docker/2.1-alpine/Dockerfile` and `docker-entrypoint.sh` (uid 1883, `/mosquitto/{config,data,log}`), `ChangeLog.txt` (2.1 built-in WebSockets, `password_file` deprecated in favour of the plugin but supported until 3.0, 2.1.3 security fixes).

## Market templates

The Mosquitto templates on the Railway marketplace (`Lima-e-Silva/mosquitto_railway_template`, `vergissberlin/railwayapp-mqtt`, `gridalpha/mosquitto-railway`) were reviewed for features only. No files or text were copied.
