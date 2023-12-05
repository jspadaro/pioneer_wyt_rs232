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
at least on my unit.  **The first three are important as a handshake!** There
are still four status messages that I don't understand - neither the message
itself nor the response:

4 Unknown Status Messages:
```
bb000104020100bd
bb00010a03050000b6
bb000109020500b4
bb00010a03050008be
```

At least three of these change frequently, implying they have status information
from the HVAC unit.

### Handshake and Issuing Settings

- Connect over serial to the unit
- You must send these 3 messages:
    - **A:** bb000104020100bd
    - **B:** bb00010a03050000b6
    - **C:** bb000109020500b4
- And they are sent as follows:
    - A 3 times
    - B 3 times
    - C 3 times
    - A **5** times
        - I assume this is some kind of synchronization / end of message thing
    - <Pause>
- I'm not sure the exact timing on the pause, I just know that's what the real
  unit sends
- Once you do the above, you can send a generated temperature control message
  three times afterwards and it should work
    - If you skip the handshake/heartbeat, it won't work
    - The real unit sends everything 3 times, so I do too
- If you see the exact thing you sent reflected back to you, you've got
  something wrong
    - If done correctly, you'll get some kind of status response I don't
      understand

### Other Notes

- This is similar to the documented Midea protocol, but different
    - Messages begin with bb rather than aa, for example
- The wifi adapter sends any given command message 3 to 5 times
- Each message from wifi adapter to HVAC gets a result
