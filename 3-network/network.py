import network

ssid = "REPLACE_WITH_YOUR_SSID"
pw = "REPLACE_WITH_YOUR_PASSWORD"

sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(ssid, pw)

while not sta.isconnected():
    pass

print(sta.ifconfig())