#!/bin/sh
# Eclipse Mosquitto on Railway.
#
#   1883  MQTT (private network, and the TCP proxy for clients outside Railway)
#   8080  MQTT over WebSockets (the public HTTPS domain: wss://{domain}/)
#   $PORT private /healthz (MQTT login check) for Railway's healthcheck
#
# Anonymous access is off; the user comes from MQTT_USERNAME/MQTT_PASSWORD and
# is rewritten on every start. Deploy-form values never stop the deploy
# (STANDARD 8.29): an invalid user name falls back to the default, an
# invalid password locks the user with a random one, and the log says why.
set -eu

log() { echo "railway-mosquitto: $*" >&2; }
random_secret() { head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }

CONF_DIR=/mosquitto/config
DATA=/mosquitto/data
PASSWD=$CONF_DIR/railway-passwd
CONF=$CONF_DIR/railway.conf

case "${PORT:-}" in ''|*[!0-9]*) log "PORT='${PORT:-}' is not a number, using 8081"; PORT=8081 ;; esac
case "$PORT" in 1883|8080) log "PORT=$PORT collides with an MQTT listener, using 8081"; PORT=8081 ;; esac
export PORT

user="${MQTT_USERNAME:-mqtt}"
if ! printf '%s' "$user" | grep -Eq '^[A-Za-z0-9._@-]{1,64}$'; then
  log "MQTT_USERNAME may only use letters, digits and . _ @ - (1-64 chars), using 'mqtt'"
  user=mqtt
fi
pass="${MQTT_PASSWORD:-}"
pass_len=$(printf '%s' "$pass" | wc -c | tr -d ' ')
if [ "$pass_len" -lt 12 ] || [ "$pass_len" -gt 128 ] || printf '%s' "$pass" | grep -q '[[:space:]]'; then
  log "WARNING: MQTT_PASSWORD must be 12-128 characters without spaces (got $pass_len)."
  log "WARNING: user '$user' is LOCKED with a random password nobody knows; set MQTT_PASSWORD and redeploy."
  pass=$(random_secret 40)
fi

max_conn="${MQTT_MAX_CONNECTIONS:--1}"
case "$max_conn" in -1) ;; ''|*[!0-9]*) log "MQTT_MAX_CONNECTIONS='$max_conn' is not a number, using -1 (unlimited)"; max_conn=-1 ;; esac

mkdir -p "$CONF_DIR" "$DATA"
chown -R mosquitto:mosquitto "$DATA"

umask 077
: > "$PASSWD"
mosquitto_passwd -b "$PASSWD" "$user" "$pass"
# Owner root (future Mosquitto versions require it), readable by the mosquitto group:
# the broker reads it after dropping privileges.
chown root:mosquitto "$PASSWD"
chmod 0640 "$PASSWD"
# Credentials for the local healthcheck login (root-only file).
mkdir -p /run
printf '%s\n%s\n' "$user" "$pass" > /run/railway-mqtt-health
chmod 0600 /run/railway-mqtt-health
unset pass MQTT_PASSWORD
umask 022

cat > "$CONF" <<EOT
# Written by railway-mosquitto at every start; edit the service variables instead.
user mosquitto
allow_anonymous false
password_file $PASSWD
persistence true
persistence_location $DATA/
autosave_interval 300
log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
connection_messages true
log_timestamp_format %Y-%m-%dT%H:%M:%S

# MQTT, all IPv4 and IPv6 addresses (private network and TCP proxy).
listener 1883
protocol mqtt
max_connections $max_conn

# MQTT over WebSockets behind Railway's HTTPS domain.
listener 8080
protocol websockets
max_connections $max_conn
EOT

python3 /usr/local/bin/railway-healthz &

log "starting Mosquitto: MQTT :1883, WebSockets :8080, healthz :$PORT, user '$user'"
exec /usr/sbin/mosquitto -c "$CONF"
