# MQTT Integration

This document describes the PySide6 host-side MQTT integration. TCP remains available.

## Configuration

Copy `.env.example` to `.env` in `上位机/waist_ui`, then fill in the real EMQX username and password.

```env
COMM_MODE=mqtt
MQTT_BROKER_HOST=m4673563.ala.cn-hangzhou.emqxsl.cn
MQTT_BROKER_PORT=8883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
MQTT_CLIENT_ID=waist-ui-device001
MQTT_DEVICE_ID=device001
MQTT_TOPIC_PREFIX=waist
MQTT_TLS_ENABLE=true
MQTT_CA_CERT_PATH=certs/emqxsl-ca.crt
MQTT_VERSION=3.1.1
```

`.env` is ignored by git. Do not put real passwords in source code.

## CA Certificate

Put the EMQX Serverless CA certificate at:

```text
上位机/waist_ui/certs/emqxsl-ca.crt
```

If you use another path, update `MQTT_CA_CERT_PATH` in `.env`.

## Dependencies

Install the host-side dependencies:

```bash
pip install -r requirements.txt
```

The MQTT integration requires `paho-mqtt` and `python-dotenv`.

## Standalone Test

Run:

```bash
cd 上位机/waist_ui
python tools/test_emqx_connection.py
```

Expected behavior:

- connects to EMQX over TLS port `8883`
- subscribes to telemetry/status/ack/cmd
- publishes one telemetry JSON message every 2 seconds
- prints received topic and payload

## Mode Switch

TCP mode:

```env
COMM_MODE=tcp
```

MQTT mode:

```env
COMM_MODE=mqtt
```

TCP mode uses the existing `TCPClient`. MQTT mode uses `MQTTClient` with the same high-level methods used by the UI.

## Topics

```text
waist/device001/telemetry
waist/device001/status
waist/device001/cmd
waist/device001/ack
```

## Telemetry Example

Publish with MQTTX:

Topic:

```text
waist/device001/telemetry
```

Payload:

```json
{
  "device_id": "device001",
  "LF": 12.3,
  "RF": 11.8,
  "LB": 13.1,
  "RB": 12.9
}
```

The host converts this JSON into the UI dict format:

```python
{"LF": 12.3, "RF": 11.8, "LB": 13.1, "RB": 12.9}
```

## Command Example

When the UI sliders change in MQTT mode, the host publishes to:

```text
waist/device001/cmd
```

Payload:

```json
{
  "cmd": "set_force",
  "device_id": "device001",
  "RB": 1.0,
  "RF": 2.0,
  "LB": 3.0,
  "LF": 4.0
}
```

Manual text commands are published as:

```json
{
  "cmd": "text",
  "device_id": "device001",
  "value": "user input"
}
```

## Common Problems

- CA certificate path is wrong: check `MQTT_CA_CERT_PATH`.
- Username or password is wrong: verify the same values in MQTTX.
- Port is set to `1883`: EMQX Serverless TLS should use `8883`.
- TLS is disabled: keep `MQTT_TLS_ENABLE=true`.
- `.env` is not loaded: install `python-dotenv`, or set environment variables manually.
- MQTTX connects but PySide6 does not: compare host, port, TLS, username, password, client id, and CA certificate path.
