from machine import Pin, ADC

# Pin
ADC_PIN = 36


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        # adc.width(ADC.WIDTH_10BIT)
        adc.atten(ADC.ATTN_11DB)

        return adc

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    f = open("test.txt", "w")

    adc = setup()
    if adc is None:
        print("Failed...")
        return

    temp = input("Enter your temperature: ")
    raw = adc.read()
    print(raw)

    with open("test.txt", "w") as f:
        f.write(str(raw) + " " + temp)

    print("Written to test.txt")


if __name__ == "__main__":
    main()
