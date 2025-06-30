#!/usr/bin/env python3
'''
以下是針對你 README.md 中「即時 RSSI 紀錄 (binary)」腳本的優化建議，重點在於：

- 用 with 管理檔案，避免遺漏 close
- 捕捉 subprocess.CalledProcessError，避免過度寬鬆 except
- 支援自訂介面名稱（參數化）
- 增加註解與錯誤提示
- SIGTERM 也能安全結束
- 可選擇輸出檔名
'''

import time
import subprocess
import struct
import signal
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="即時記錄 Wi-Fi RSSI (binary)")
    parser.add_argument("-i", "--iface", default="wlan0", help="Wi-Fi 介面名稱 (預設: wlan0)")
    parser.add_argument("-o", "--output", default="wifi_signal.bin", help="輸出檔名")
    args = parser.parse_args()

    running = True
    def handler(sig, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    with open(args.output, "wb") as f:
        t0 = int(time.time())
        f.write(struct.pack("<Q", t0))
        f.flush()
        print(f"Started recording at epoch {t0}")

        while running:
            now = int(time.time())
            offset = now - t0
            try:
                iw_out = subprocess.check_output(
                    ["iw", "dev", args.iface, "link"],
                    stderr=subprocess.DEVNULL
                ).decode()
                line = next((l for l in iw_out.splitlines() if "signal:" in l), None)
                dbm = int(line.split()[1]) if line else -127
            except subprocess.CalledProcessError:
                print(f"[警告] 無法取得 {args.iface} 訊號，寫入 -127", file=sys.stderr)
                dbm = -127
            except Exception as e:
                print(f"[錯誤] {e}", file=sys.stderr)
                dbm = -127

            f.write(struct.pack("<Ib", offset, dbm))
            f.flush()
            print(f"[{offset}s] {dbm} dBm")
            time.sleep(1)

if __name__ == "__main__":
    main()