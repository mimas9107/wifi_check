#!/usr/bin/env python3
''' -*- coding: utf-8 -*-
**優化重點：
- 支援 `-f` 指定檔名
- 檔案不存在或格式錯誤時有明確錯誤訊息
- 封裝成函式，主程式結構更清晰
- 若無資料會提示並安全結束
- `plt.tight_layout()` 避免標籤重疊
- 保留原有功能與參數相容
'''
import struct
import matplotlib.pyplot as plt
import argparse
import datetime
import sys
import os

def read_wifi_bin(filename):
    if not os.path.exists(filename):
        print(f"[錯誤] 找不到檔案: {filename}", file=sys.stderr)
        sys.exit(1)
    data = []
    with open(filename, "rb") as f:
        header = f.read(8)
        if len(header) < 8:
            print("[錯誤] 檔案內容不足，無法讀取 timestamp", file=sys.stderr)
            sys.exit(1)
        t0 = struct.unpack("<Q", header)[0]
        print(f"Start timestamp (epoch): {t0}")
        while True:
            rec = f.read(5)
            if len(rec) < 5:
                break
            offset, dbm = struct.unpack("<Ib", rec)
            data.append((offset, dbm))
    return t0, data

def main():
    parser = argparse.ArgumentParser(description="繪製 Wi-Fi RSSI 折線圖")
    parser.add_argument("-H", "--human", action="store_true", help="x 軸顯示人類可讀時間")
    parser.add_argument("-f", "--file", default="wifi_signal.bin", help="輸入檔名 (預設: wifi_signal.bin)")
    args = parser.parse_args()

    t0, data = read_wifi_bin(args.file)
    if not data:
        print("[警告] 沒有資料可繪圖", file=sys.stderr)
        sys.exit(0)

    x = [datetime.datetime.fromtimestamp(t0 + o) if args.human else t0 + o for o, _ in data]
    y = [d for _, d in data]

    plt.figure(figsize=(12,6))
    plt.plot(x, y, marker="o")
    plt.xlabel("Time" if args.human else "Unix Time (s)")
    plt.ylabel("Wi-Fi RSSI (dBm)")
    plt.title("Wi-Fi signal strength")
    plt.grid(True)
    if args.human:
        plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()