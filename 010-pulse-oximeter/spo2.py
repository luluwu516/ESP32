from utime import ticks_ms, ticks_diff
from machine import SoftI2C, Pin
from max30102 import MAX30102
from pulse_oximeter import Pulse_oximeter

# Pin Definitions
SDA_PIN = 21
SCL_PIN = 22

def setup():
    try:
        i2c = SoftI2C(sda=Pin(SDA_PIN),scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor()
        return sensor
    
    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    sensor = setup()
    
    if sensor is None:
        print("Failed...")
        return
    
    pox = Pulse_oximeter(sensor)
    
    last_print = ticks_ms()
    
    try:
        while (True):
            pox.update()
            
            # output per second
            if ticks_diff(ticks_ms(), last_print) > 1000:
                print("SpO2:", pox.get_spo2(), "% HR:", pox.get_heart_rate())
                last_print = ticks_ms()
                
                # print("ir:", pox.get_raw_ir(), "red:", pox.get_raw_red())
    
    except KeyboardInterrupt:
        pass
    
    finally:
        sensor.shutdown()
        print("Sensor shut down")
        

if __name__ == "__main__":
    main()


