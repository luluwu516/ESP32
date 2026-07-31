from wifi import *  # the module store my wifi info
import network

ssid = REPLACE_WITH_YOUR_SSID
pw = REPLACE_WITH_YOUR_PASSWORD


def connect_to_wifi(ssid, password):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)

    while not sta.isconnected():
        pass

    print("Connected to WiFi:", sta.ifconfig())


def main():
    connect_to_wifi(ssid, pw)


if __name__ == "__main__":
    main()
