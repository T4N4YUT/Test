import uasyncio as asyncio
from mqtt_as import MQTTClient, config as mqtt_config
import ujson
import ubinascii
import machine
import time
import gc
import os
from ConfigManager import Config_Manager

class MQTT_Manager:
    def __init__(self, mac, ethernet, dht22_manager):
        self.config_manager = Config_Manager("mqtt_config.json", default_config_file="mqtt_default_config.json")
        self.mac = mac
        self.ethernet = ethernet
        self.dht22_manager = dht22_manager
        self.is_mqtt_ready = False
        client_id = self.mac.replace(':', '') if self.mac else ubinascii.hexlify(machine.unique_id()).decode()
        lwt_topic = self.config_manager.get_config('lwt_topic', f'esp32/{client_id}/status')
        lwt_payload = ujson.dumps({"status": "offline", "mac": self.mac})
        mqtt_config['will'] = (lwt_topic, lwt_payload, True, 1)
        mqtt_config['server'] = self.config_manager.get_config('broker')
        mqtt_config['port'] = self.config_manager.get_config('port', 1883)
        mqtt_config['user'] = self.config_manager.get_config('user', '')
        mqtt_config['password'] = self.config_manager.get_config('password', '')
        mqtt_config['keepalive'] = self.config_manager.get_config('keepalive', 120)
        mqtt_config['client_id'] = client_id
        mqtt_config['queue_len'] = 1
        MQTTClient.DEBUG = True
        self.client = MQTTClient(mqtt_config)
        self._status_topic = self.config_manager.get_config('status_topic', f'esp32/{client_id}/status')
        self.subscribe_topics = self.config_manager.get_config('subscribe_topics', [])
        gc.collect()

    def is_connected(self):
        return self.client.isconnected()

    async def safe_publish(self, topic, data, retain=False, qos=0):
        if not self.is_mqtt_ready:
            print("Error: Publish failed(MQTT not ready) ✘")
            return False
        try:
            payload_str = ujson.dumps(data)
            await self.client.publish(topic, payload_str, retain=retain, qos=qos)
            print(f"Debug: Published to {topic} ✔")
            return True
        except Exception as e:
            print(f"Error: Publish Failed {e} ✘")
            return False

    async def publish_status_task(self):
        while True:
            await asyncio.sleep(19)
            if self.is_mqtt_ready:
                payload = {"status": "online", "mac": self.mac}
                await self.safe_publish(self._status_topic, payload, retain=False)

    async def message_handler(self):
        async for topic, msg, retained in self.client.queue:
            try:
                t = topic.decode('utf-8')
                p = msg.decode('utf-8')
                print(f"Debug: MQTT Message Received on '{t}': {p} ✔")
                if t == 'esp32/commands' and p.strip() == '{"command":"get_config"}':
                    print("Debug: Received get_config command. Gathering configuration...")
                    ethernet_config = self.ethernet.config.load_config()
                    mqtt_config = self.config_manager.load_config()
                    dht22_config = self.dht22_manager.config_manager.load_config()
                    response_payload = {
                        "ethernet": ethernet_config,
                        "mqtt": mqtt_config,
                        "alerts": {
                            "temp_crit_low": dht22_config.get("CON_TEMP_MIN"),
                            "temp_warn_low": dht22_config.get("CON_TEMP_WARN_LOW"),
                            "temp_warn_high": dht22_config.get("CON_TEMP_WARN_HIGH"),
                            "temp_crit_high": dht22_config.get("CON_TEMP_MAX"),
                            "hum_crit_low": dht22_config.get("CON_HUM_MIN"),
                            "hum_warn_low": dht22_config.get("CON_HUM_WARN_LOW"),
                            "hum_warn_high": dht22_config.get("CON_HUM_WARN_HIGH"),
                            "hum_crit_high": dht22_config.get("CON_HUM_MAX")
                        }
                    }
                    response_topic = f"esp32/response/{self.mac}/config"
                    await self.safe_publish(response_topic, response_payload)
            except Exception as e:
                print(f"Error: Processing message: {e} ✘")

    async def connection_handler(self):
        while True:
            await self.client.up.wait()
            self.client.up.clear()
            self.is_mqtt_ready = True
            print("Debug: MQTT is connected ✔")
            
            for topic in self.subscribe_topics:
                try:
                    await self.client.subscribe(topic, 1)
                    print(f"Debug: Subscribed to topic: {topic} ✔")
                except Exception as e:
                    print(f"Error: Subscribe failed for topic {topic}: {e} ✘")
            
            payload = {"status": "online", "mac": self.mac}
            await self.safe_publish(self._status_topic, payload, retain=True)

            await self.client.down.wait()
            self.client.down.clear()
            self.is_mqtt_ready = False
            print("Debug: MQTT disconnected ✘.")

    async def start_service_mqtt(self):
        asyncio.create_task(self.connection_handler())
        asyncio.create_task(self.publish_status_task())
        asyncio.create_task(self.message_handler())
        while True:
            try:
                await self.client.connect()
                break
            except OSError:
                await asyncio.sleep(10)

    def reset_mqtt_config(self):
        try:
            self.config_manager.reset_config(keys=["broker", "port", "user", "password"])
            print("✅ MQTT config has been reset to default values.")
        except Exception as e:
            print(f"⚠️ Failed to reset MQTT config: {e}")

