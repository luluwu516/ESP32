# Network on ESP32

The ESP32 is widely known for its integrated Wi-Fi and Bluetooth capabilities, making it ideal for IoT (Internet of Things) and embedded applications requiring wireless communication.

Amazon forgot to send me the tube that should come with the pump, so I returned it. While waiting for my pump and tube, I think I can do something more, like connecting the event to my Line account so I will know when my machine is watering my plants. If the system had some issues when I was not home, I could ask my friend to check it at least.

<img width="613" alt="Thonny" src="https://github.com/luluwu516/ESP32/assets/98475122/f73306ac-089b-4974-b95d-727244ecbb77">

<br />

<br />

## IFTTT (IF This Then That)

[IFTTT (If This Then That)](https://ifttt.com/explore) is a powerful automation platform that connects various online services and devices to create custom workflows, known as applets, based on simple conditional statements. The platform's name reflects its functionality: "If this, then that." It allows users to create chains of conditional statements called applets, which trigger an action in one service when a predefined condition occurs in another.

I planned to use the service to connect my auto-watering system to Line so I would know when my machine was watering my plants.

<img width="613" alt="IFTTT Homepage" src="https://github.com/luluwu516/ESP32/assets/98475122/be758b14-e80d-4470-8f4a-25d066118543">

<br />

<br />

Here is how to create automation on IFTTT:

1. After logging in with your account (Apple, Google, or Facebook), hit the "Create" button on the top right
2. Press the "Add" button after "If This"

<img width="612" alt="IFTTT Create" src="https://github.com/luluwu516/ESP32/assets/98475122/4170b37f-e4fb-4c34-804f-4120c6f412dc">

3. Select Webhooks, which allows users to connect any service that supports webhooks to create custom applets. The service used to be free, but it is not now.

<img width="613" alt="IFTTT Services" src="https://github.com/luluwu516/ESP32/assets/98475122/d20567f6-cd11-4406-b6b8-39ff3e8f660b">

4. Choose "Receive a web request"

<img width="612" alt="IFTTT Webhooks" src="https://github.com/luluwu516/ESP32/assets/98475122/d2b2482a-834a-4285-a155-1589398bfe7d">

5. Enter the event name. I used "water_plants" here.

<img width="612" alt="IFTTT Webhooks' event name" src="https://github.com/luluwu516/ESP32/assets/98475122/93361560-5c35-442c-8bc7-e505fdffe27b">

6. Then, press the "Add" button after "Then That"
<img width="613" alt="IFTTT Then That" src="https://github.com/luluwu516/ESP32/assets/98475122/f6b75a68-6353-41c8-b912-ca44b32f78fd">

7. Select the service you want to use, such as Google Sheets and Line. I used Line service for this project.

<img width="613" alt="IFTTT Line" src="https://github.com/luluwu516/ESP32/assets/98475122/c8784086-fb43-4ce0-bab6-c8cbbb473d6b">

8. For Line Service, we can send messages to ourselves. Then, press "Create action"

<img width="613" alt="IFTTT Line settings" src="https://github.com/luluwu516/ESP32/assets/98475122/a0c445de-fa8e-4320-bab3-48e826d9c62d">

9. Press the "Continue" button

<img width="612" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/ad19dde0-2c06-4bf1-ab9a-bdba460c2b47">

10. Review and finish the settings

11. Click the Webhooks icon

12. Open the Documentation and copy the key and URL to your program (see the "network-IFTTT.py")

<br />

## Reference
* [FLAG](https://www.flag.com.tw/maker/FM622A)


