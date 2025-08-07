import time
import urequests
import ure
import uasyncio as asyncio
import gc
import machine
class Time_Manager:
    def __init__(self, ethernet, timezone_offset=0, http_time_url="http://192.168.42.9:1880/api/time"):
        self.ethernet = ethernet
        self.timezone_offset = timezone_offset * 3600
        self.http_time_url = http_time_url
        self.ntp_sync = False
        self.sync_iso = None
        self.sync_ticks = None
        self.boot_ticks = time.ticks_ms()
        gc.collect()

    def get_iso_timestamp(self):
        current_utc_seconds = time.time() 
        local_time_seconds = current_utc_seconds + self.timezone_offset
        tm = time.localtime(local_time_seconds)
        iso_str = f"{tm[0]:04d}-{tm[1]:02d}-{tm[2]:02d}T{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
        gc.collect()
        return iso_str

    def parse_iso(self, iso_str):
        m = ure.match(r"(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)", iso_str)
        if m:
            parsed_tuple = tuple(int(m.group(i)) for i in range(1, 7))
        else:
            print("Error: Could not parse ISO string:", iso_str,"✘")
            parsed_tuple = (0, 0, 0, 0, 0, 0)
        gc.collect()
        return parsed_tuple

    def iso_add_ms(self, iso_anchor, delta_ms):
        y, m, d, H, M, S = self.parse_iso(iso_anchor)
        local_time_anchor_seconds = time.mktime((y, m, d, H, M, S, 0, 0))
        utc_time_anchor_seconds = local_time_anchor_seconds - self.timezone_offset
        new_utc_seconds = utc_time_anchor_seconds + (delta_ms // 1000)
        tm = time.localtime(new_utc_seconds + self.timezone_offset)
        iso_str = f"{tm[0]:04d}-{tm[1]:02d}-{tm[2]:02d}T{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
        gc.collect()
        return iso_str

    async def sync_http_time(self):
        try:
            res = urequests.get(self.http_time_url)
            data = res.json()
            self.sync_iso = data['iso']
            self.sync_ticks = time.ticks_ms()
            self.ntp_sync = True
            print("Debug: HTTP time synced @", self.sync_iso, "✔")
            res.close()
            gc.collect()
            return True
        except Exception as e:
            print("Error: HTTP time sync failed:", e, "✘")
            self.ntp_sync = False
            machine.reset()
            return False

    async def sync_ntp_task(self):
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            if self.ethernet.isconnected():
                success = await self.sync_http_time()
                if success:
                    return True
                else:
                    print(f"Debug: Time sync failed on attempt {attempt + 1} ✘")
            else:
                print("Debug: Ethernet not connected ✘")
                break

            await asyncio.sleep(retry_delay)

        print("Error: Time sync failed after all retries ✘")
        self.ntp_sync = False
        gc.collect()
        return False

    async def start_service_ntp_sync(self, interval=10):
        await self.sync_ntp_task()
        while True:
            await self.sync_ntp_task()
            await asyncio.sleep(interval)
            gc.collect()

    def now(self):
        if self.sync_iso and self.sync_ticks is not None:
            delta = time.ticks_diff(time.ticks_ms(), self.sync_ticks)
            iso_str = self.iso_add_ms(self.sync_iso, delta)
        else:
            iso_str = self.get_iso_timestamp()
        gc.collect()
        return iso_str

    def uptime(self):
        up = time.ticks_diff(time.ticks_ms(), self.boot_ticks) / 1000
        gc.collect()
        return up
