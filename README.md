# Pioneer WYT RS232 Protocol

Python script that creates and parses the RS232 protocol used by Pioneer WYT mini splits

## Overview

The Pioneer WYT mini split works with a $35 Wifi adapter based on the Tuya
TYWE1S.  This is an ESP8266 flashed with Tuya firmware that uses Tuya's cloud
smart home functionality.

It connects to the mini split via a 4-pin connector that has 5V/Gnd and RX/TX
for a serial connection.  The serial protocol is 9600 8E1 (8 bits, even parity,
1 stop bit).

I managed to reverse how to format command messages to change any HVAC settings,
at least on my unit.  There are still four status messages that I don't
understand - neither the message itself nor the response:

4 Unknown Status Messages:
```
bb000109020500b4
bb00010a03050000b6
bb000104020100bd
bb00010a03050008be
```

At least three of these change frequently, implying they have status information
from the HVAC unit.
