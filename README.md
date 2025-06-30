# Wi-Fi 88x2bu 稳定性排查與監控方案

此專案紀錄如何在 Linux 環境中針對 Realtek 88x2bu (例：RTL8822BU) USB Wi-Fi dongle  
進行穩定度排查、驅動重製作、系統設定強化，以及連線品質數據長期監控與繪圖。

---

## 1️⃣ 問題背景

在公共 Wi-Fi 或多使用者環境下，遇到：
- 頻繁掉線
- kernel 顯示 `rtw_8822bu timed out to flush queue`
- 突然無法 reconnect

---

### 2️⃣ 掉線排查

觀察指令
```bash
nmcli device status
iw dev wlan0 link
sudo dmesg | grep -i rtw
journalctl -k -b | grep -i rtw


常見訊息：

    timed out to flush queue

    reset

    usb disconnect

若出現頻繁，建議進行驅動更新。


### 3️⃣ 驅動重製作 (DKMS)

建議使用 morrownr/88x2bu-20210702
進行 DKMS 安裝，方便核心升級後自動重編。

基本流程：

```bash
sudo apt install dkms git build-essential
git clone https://github.com/morrownr/88x2bu-20210702.git
cd 88x2bu-20210702
sudo ./install-driver.sh

```

移除舊版：
```bash
sudo ./remove-driver.sh

```

### 4️⃣ 設定強化

針對公共環境可優化參數
```bash
nmcli connection modify "NewTaipei" 802-11-wireless.powersave 2
nmcli connection modify "NewTaipei" 802-11-wireless.band bg
nmcli connection modify "NewTaipei" 802-11-wireless.bssid 1C:5F:2B:24:8C:60
nmcli connection modify "NewTaipei" ipv6.method ignore
nmcli connection modify "NewTaipei" ipv4.dhcp-timeout 60

```
再重新啟用：
```bash
nmcli connection down "NewTaipei" && sleep 5 && nmcli connection up "NewTaipei"

```

### 5️⃣ 長期監控
監控腳本 wifi_monitor.sh
```bash
#!/usr/bin/env bash

LOGFILE="wifi_monitor_$(date +%Y%m%d_%H%M%S).log"

echo "==== WiFi monitor start ====" | tee -a $LOGFILE
echo "Time: $(date)" | tee -a $LOGFILE

lsmod | grep 88x2bu | tee -a $LOGFILE
nmcli device status | tee -a $LOGFILE

echo "==== iw dev link ====" | tee -a $LOGFILE
iw dev wlan0 link | tee -a $LOGFILE

echo "==== Start continuous ping ====" | tee -a $LOGFILE

# dmesg watcher
(
    echo "=== dmesg watcher started ==="
    dmesg -w | grep --line-buffered -i rtw
) >> $LOGFILE &

DMESG_PID=$!

ping 8.8.8.8 | tee -a $LOGFILE

kill $DMESG_PID
echo "==== WiFi monitor finished ====" | tee -a $LOGFILE

```

### 6️⃣ 即時 RSSI 紀錄 (binary) wifi_monitor_bin.py
功能：
  - 記錄「第一筆 timestamp」作為檔頭
  - 每秒儲存 (offset, dBm)
  - binary 格式方便後端繪圖或大數據系統接入
```python
#!/usr/bin/env python3

import time
import subprocess
import struct
import signal

filename = "wifi_signal.bin"
f = open(filename, "wb")

t0 = int(time.time())
f.write(struct.pack("<Q", t0))
f.flush()
print(f"Started recording at epoch {t0}")

running = True
def handler(sig, frame):
    global running
    running = False
signal.signal(signal.SIGINT, handler)

try:
    while running:
        now = int(time.time())
        offset = now - t0
        try:
            iw_out = subprocess.check_output(["iw", "dev", "wlan0", "link"]).decode()
            line = next((l for l in iw_out.splitlines() if "signal:" in l), None)
            dbm = int(line.split()[1]) if line else -127
        except:
            dbm = -127

        f.write(struct.pack("<Ib", offset, dbm))
        f.flush()
        print(f"[{offset}s] {dbm} dBm")
        time.sleep(1)
finally:
    f.close()

```

### 7️⃣ 繪圖 plot_wifi_bin.py
 - 顯示折線圖
 - 可選 -H （人類可讀時間）
```python
#!/usr/bin/env python3

import struct
import matplotlib.pyplot as plt
import argparse
import datetime

parser = argparse.ArgumentParser()
parser.add_argument(
    "-H",
    "--human",
    action="store_true",
    help="show human readable time on x-axis"
)
args = parser.parse_args()

filename = "wifi_signal.bin"

with open(filename, "rb") as f:
    t0 = struct.unpack("<Q", f.read(8))[0]
    print(f"Start timestamp (epoch): {t0}")
    data = []
    while True:
        rec = f.read(5)
        if len(rec) < 5:
            break
        offset, dbm = struct.unpack("<Ib", rec)
        data.append( (offset, dbm) )

x = [datetime.datetime.fromtimestamp(t0 + o) if args.human else t0 + o for o, _ in data]
y = [d for _, d in data]

plt.figure(figsize=(12,6))
plt.plot(x, y, marker="o")
plt.xlabel("Time" if args.human else "Unix Time (s)")
plt.ylabel("Wi-Fi RSSI (dBm)")
plt.title("Wi-Fi signal strength")
plt.grid(True)
plt.gcf().autofmt_xdate()
plt.show()

```


### 8️⃣ License

可標示 MIT 或 CC0 (依你的喜好)
也可列出感謝
* morrownr/88x2bu
* NetworkManager
* iw

---

## 🚀 結論

透過以上方案：

* 完成驅動穩定度強化
* 實現 RSSI 監控
* 可延伸自動化或大數據平台

Channel Occupancy

歡迎 PR 或一起改進！
