# TOMATO FRUIT PICKER AND LEAF HEALTH DETECTION

## 1. Problem & Goal
- Problem: 
    F

- Goal :
    1. make a device which can detect leaf is its healthy or not
    2. a device that can detect the ripeness of tomato

## 2. User & Use Cases
- May is not familiar with tomato fruit ripeness, she's not sure whether to pick the tomato or not, so using the handheld device, May points the camera to the fruit, she can see the output via lcd screen attached to the device, the AI model detects if its ripe, overripe, or not ripe. if it is ripe and overripe, the servo for the fruit picker will turn on, if its not ripe, the screen will box the fruit and will say it's "not ripe"
- Yumi wants to check if the fruit leaf of the tomato is healthy or not using the device. She points the camera to the leaf, the screen shows if the leaf is healthy or not

## 3. Hardware Requirements
- Components
    - Main
        - Raspberry Pi 4B
        - Webcam
        - 7 inch hdmi lcd touchscreen (800x480p)
    - Cutting Mechanism
        - Arduino Mega
        - Servo Motor

## 4. Software Requirements
- Platform (Raspberry Pi)
    - tkinter for UI
- Cutting Mechanism trigger
    - raspberry pi will send a signal to arduino mega via serial com

## 5. Data Flow
    during UI startup, user can choose if fruit picker mode or leaf health detection mode via button -> the camera feed will be displayed in the lcd touchscreen with the detection output -> in leaf health mode it will only show if the leaf is healthy or not, in fruit picker mode, it will show if the fruit is ripe, overripe, or unripe, if rip or overripe, the cutting mechanism will turn on (user can choose if automatic pick or manual mode), the raspberry pi will send data to the arduino mega via serial com to trigger the servo
