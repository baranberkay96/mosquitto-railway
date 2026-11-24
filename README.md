# Deploy and Host Eclipse Mosquitto with Railway

Eclipse Mosquitto is the lightweight, open-source MQTT broker used by IoT devices, home automation and real-time apps to publish and subscribe to messages. This template runs Mosquitto 2.1 with password authentication, persistent sessions on a volume, MQTT through Railway's TCP proxy and encrypted MQTT over WebSockets on an HTTPS domain.

## About Hosting Eclipse Mosquitto

An MQTT broker on the internet needs authentication from the first second, a raw TCP endpoint for devices, a WebSocket endpoint for browsers, and persistence so retained messages and offline sessions survive restarts. This community template builds the official `eclipse-mosquitto` image (pinned by digest) with a start script that disables anonymous access, writes the password file from the service variables on every start, persists data on a Railway volume and listens on all IPv4 and IPv6 addresses. Railway's healthcheck uses a private `/healthz` that really logs in to the broker over MQTT.

## Common Use Cases

- IoT telemetry from ESP32, Raspberry Pi, Tasmota, Shelly or Zigbee2MQTT devices
- Home Assistant, Node-RED and OpenHAB message bus reachable from anywhere
- Real-time dashboards and browser apps with MQTT.js over secure WebSockets
- Lightweight pub/sub between backend services on Railway's private network

## Dependencies for Eclipse Mosquitto Hosting

- Eclipse Mosquitto 2.1.4 (official image)
- A Railway volume at `/mosquitto/data` (retained messages, persistent sessions)

### Deployment Dependencies

- [Mosquitto documentation](https://mosquitto.org/documentation/)
- [mosquitto.conf reference](https://mosquitto.org/man/mosquitto-conf-5.html)
- [Mosquitto releases](https://mosquitto.org/blog/)

### Implementation Details

| Endpoint | Address | Use |
|---|---|---|
| MQTT, private | `${{Mosquitto.MQTT_URL}}` (`mqtt://mosquitto.railway.internal:1883`) | Railway services |
| MQTT, public TCP | `${{Mosquitto.MQTT_PUBLIC_URL}}` (TCP proxy host and port) | Devices and tools outside Railway |
| MQTT over WebSockets | `wss://{your-domain}/mqtt` on port 443 | Browsers, MQTT.js, clients that support WSS |

Log in with `MQTT_USERNAME` (default `mqtt`) and `MQTT_PASSWORD` (generated, see the Variables tab). Anonymous clients are refused.

**Quick test**

```
mosquitto_sub -h {proxy-host} -p {proxy-port} -u mqtt -P {password} -t 'test/#' -v
mosquitto_pub -h {proxy-host} -p {proxy-port} -u mqtt -P {password} -t test/hello -m 'hi'
```

In MQTT Explorer or MQTT.js, use the WebSocket URL with TLS: `wss://{your-domain}/mqtt`, port 443.

**Security note**

Railway's TCP proxy passes raw TCP, so plain MQTT on the TCP proxy is not encrypted (the password travels in clear text, like any MQTT without TLS). Use the `wss://` endpoint, which Railway encrypts with HTTPS, for anything sensitive, and keep plain MQTT for the private network or for devices that cannot do TLS. If you do not need outside TCP access, delete the TCP proxy in the service settings.

**Variables**

| Variable | Default | Purpose |
|---|---|---|
| `MQTT_USERNAME` / `MQTT_PASSWORD` | `mqtt` / generated | The broker's user, rewritten at every start |
| `MQTT_MAX_CONNECTIONS` | `-1` | Connection limit per listener |

An invalid user name falls back to `mqtt`; a password outside 12-128 characters (or with spaces) locks the user with a random one and the log explains the fix. Messages are persisted every 5 minutes and on shutdown.

**More users and ACLs**

Eject the repo and extend `services/mosquitto/railway-mosquitto.sh`: add more `mosquitto_passwd -b` lines (from extra variables) and an `acl_file`. The generated config is `/mosquitto/config/railway.conf`.

**Scaling and upgrades**

One broker handles thousands of connected devices on a small amount of RAM; scale vertically. To upgrade, change the tag and digest in `services/mosquitto/Dockerfile` after reading the release notes and redeploy.

**Resources**

Measured idle use on Railway is listed in TEMPLATE.md; a broker with a few clients uses a few MB. Trial is enough.

### Why Deploy Eclipse Mosquitto on Railway?

Railway gives Mosquitto exactly what an MQTT broker needs: a TCP proxy for devices, an HTTPS domain for secure WebSockets, a private network for your backend and a volume for persistence. You get an authenticated broker in about a minute and it costs very little to run. This is a community template, not affiliated with the Eclipse Foundation.
