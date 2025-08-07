import uasyncio as asyncio
import gc
from EthernetManager import Ethernet_Manager
from TimeManager import Time_Manager
from MQTTManager import MQTT_Manager
from DHT22Manager import DHT22_Manager
from LEDManager import LED_Manager
from machine import reset

async def main():
    # สร้าง instance ของ EthernetManager และ LEDManager ก่อน
    ethernet = Ethernet_Manager()
    led_mgr = LED_Manager()

    # ทำการเชื่อมต่อ Ethernet ก่อนที่จะเรียกใช้ MAC Address
    await ethernet.connect()
    mac = ethernet.get_mac()
    print("💻 MAC Address:", mac)

    # สร้าง instance ของ Manager อื่นๆ หลังจากได้ MAC Address
    time_mgr = Time_Manager(ethernet)
    mqtt_mgr = MQTT_Manager(mac)
    dht_mgr = DHT22_Manager(
        time_manager=time_mgr,
        ethernet=ethernet,
        mqtt_manager=mqtt_mgr,
        led_manager=led_mgr
    )

    # เริ่ม Service ทั้งหมดพร้อมกันเป็น asyncio tasks
    asyncio.create_task(ethernet.check_reset_config(mqtt_manager=mqtt_mgr, dht22_manager=dht_mgr))
    asyncio.create_task(ethernet.led_status_manager())
    asyncio.create_task(ethernet.retry_connect_loop())
    asyncio.create_task(time_mgr.start_service_ntp_sync())
    asyncio.create_task(mqtt_mgr.start_service_mqtt())
    await dht_mgr.start_service_dht22()

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
    gc.collect()
