from utime import sleep_ms
from machine import Pin, ADC

# Pin
ADC_PIN = 36

DATA_FILE = "temperature.txt"
NUM_SAMPLES = 20


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        adc.width(ADC.WIDTH_10BIT)  # to match the data in temperature.txt
        adc.atten(ADC.ATTN_11DB)

        return adc

    except Exception as e:
        print("Setup error:", e)
        return None


def read_average(adc):
    total = 0

    for i in range(NUM_SAMPLES):
        total += adc.read()
        sleep_ms(10)

    return int(total / NUM_SAMPLES)


def ask_temperature():
    while True:
        answer = input("Reference temperature, 'skip' or 'end': ").strip()

        if answer == "end":
            return None
        if answer == "skip":
            return "skip"

        try:
            return float(answer)
        except ValueError:
            print("Not a number! Try again.")


def main():
    adc = setup()
    if adc is None:
        print("Failed...")
        return

    f = open(DATA_FILE, "w")
    count = 0

    try:
        while True:
            if input("Enter to sample, or 'end': ").strip() == "end":
                break

            raw = read_average(adc)

            temp = ask_temperature()
            if temp is None:
                break

            if temp == "skip":
                print("Discarded.")
                print()
                continue

            f.write("%d %.1f\n" % (raw, temp))
            f.flush()

            count += 1
            print("raw:", raw, "temp:", temp)
            print()

    except KeyboardInterrupt:
        pass

    finally:
        f.close()
        print("Saved %d records to %s" % (count, DATA_FILE))


if __name__ == "__main__":
    main()
