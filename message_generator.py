#!/usr/bin/python3
import binascii
from enum import Enum
import struct

# Convert desired temperature to pioneer serial format
def toC(fahrenheit):
    return (float(fahrenheit)-32.0)*(5.0/9.0)

def toF(celsius):
    return (float(celsius)*(9.0/5.0))+32.0

# Round down to .25, .5, .75
def toNearestQuarter(num):
    return int(num*4)/4

def tempToPioneerHex(celsius):
    celsius = toNearestQuarter(celsius)
    
    # Pioneer first nibble is X where, 31-X = celsius temp
    first_nibble = 31-int(celsius)
    
    # Final nibble is 0, 4, 8, or c for .25, .5, .75
    final_nibble_options = {0.0: 0x0, 0.25: 0x4, 0.5: 0x8, 0.75: 0xc}
    final_nibble = final_nibble_options[(celsius % 1)]
    
    # And 3 0's in the middle, not sure what they are for
    return [first_nibble, final_nibble]
    return f'{first_nibble:x}000{final_nibble:x}'
    

def nibbleToHexInt(nibble):
    # Kludge city, I'm sure there's a cleaner way
    return struct.unpack('B', binascii.unhexlify(f'0{chr(nibble)}'))[0]
    
# Assume input is first and last nibbles as integers
# See: nibbleToHexInt
# Returns celsius
def fromPioneerHex(first_nibble, last_nibble):
    final_nibble_options = {0x0: 0.0, 0x4: 0.25, 0x8: 0.5, 0xc: 0.75}
    # 31 - X = celsius temp, + final nibble being a quarter
    return (31.0 - float(first_nibble)) + final_nibble_options[last_nibble]

# Just xor each byte - assumes checksum is NOT present at end
def calc_xor_checksum(my_bytes):
    result = 0
    
    for byte in my_bytes:
        result = result ^ byte
    
    return result

# Check the final byte against a computed xor checksum
# Assumes final byte IS present
def check_xor_checksum(my_bytes):
    current_checksum = my_bytes[-1]
    my_bytes = my_bytes[:-1]
    
    result = 0
    for byte in my_bytes:
        result = result ^ byte
    return result == current_checksum

# The actual wifi adapter sends these quite often in 1,2,3 order
# Unclear if optional?
def get_unknown_message(num):
    messages = [
        binascii.unhexlify(b'bb000104020100bd'),    # 1
        binascii.unhexlify(b'bb00010a03050000b6'),  # 2
        binascii.unhexlify(b'bb000109020500b4'),    # 3
        binascii.unhexlify(b'bb00010a03050008be'),    # This one is sent much less often
    ]

##### These enums are for setting various modes in generate_message()

class SleepMode(Enum):
    OFF = 0x0
    STANDARD = 0x1
    THE_AGED = 0x2 # This name is from Pioneer/Tuya, not me
    CHILD = 0x3

class WindSpeed(Enum):
    # Actually called literally:
    # Low speed, Mid-Low, Medium speed, Mid-High, High, strong [sic]
    # Seemed kinda absurd, just set 1-6 + mute (low speed quiet) and auto
    AUTO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    MUTE = 7

# Heat/Cool/etc
class Mode(Enum):
    HEAT = 0x1
    DEHUMIDIFY = 0x2
    COOL = 0x3
    FAN = 0x7
    AUTO = 0x8

class FanUpDown(Enum):
    AUTO = 0x0 # Not officially called auto
    UP_DOWN_FLOW = 0x18
    UP_FLOW = 0x10
    DOWN_FLOW = 0x08
    TOP_FIX = 0x01
    UPPER_FIX = 0x02
    MIDDLE_FIX = 0x03
    ABOVE_DOWN_FIX = 0x04
    BOTTOM_FIX = 0x05

class FanLeftRight(Enum):
    AUTO = 0x0
    LEFT_RIGHT_FLOW = 0x08
    LEFT_FLOW = 0x10
    MIDDLE_FLOW = 0x18
    RIGHT_FLOW = 0x20
    LEFT_FIX = 0x01
    LEFT_MIDDLE_FIX = 0x02 # This is called "a bit left" for some reason in app
    MIDDLE_FIX = 0x3
    RIGHT_MIDDLE_FIX = 0x4 # Called Center Right in app
    RIGHT_FIX = 0x5

##### End enums

# Outputs raw bytes to send
def generate_message(mode, temp_celsius, wind_speed=WindSpeed.AUTO, up_down_mode=FanUpDown.AUTO, left_right_mode=FanLeftRight.AUTO, sleep_mode=SleepMode.OFF, is_on=True, is_display_on=True, is_buzzer_on=False, is_eco=False, is_8_deg_heater=False, is_health_on=False):
    ##### Sanity checking, should likely add more
    if temp_celsius > 31 or temp_celsius < 16:
        print(f'Temperature must be between 16 and 31 degrees celsius')
        return None
    ##### End sanity checking
    
    # Assume we're generating commands from wifi adapter to hvac unit
    message = bytearray(b'\xbb\x00\x01')
    
    # Also assume we're sending a temperature change command
    message += b'\x03'
    
    # This is a minimal message with all bits below set to 0.  Not sure what the other bits set represent.
    #command = bytearray(binascii.unhexlify(b'000000004c00048000000000000000000000000000000000000000008099'))
    command = bytearray(binascii.unhexlify(b'000000000c00008000000000000000000000000000000000000000008099'))
    
    ###### Bitwise operations to set various settings
    
    ###### On / Off
    if is_on:
        command[3] = command[3] | 0x04
    
    ###### Display On/Off
    if is_display_on:
        command[3] = command[3] | 0x40

    ###### Buzzer On/Off
    if is_buzzer_on:
        command[3] = command[3] | 0x20

    ###### Eco mode
    if is_eco:
        command[3] = command[3] | 0x80
    
    ##### 8 Degree Heater
    if is_8_deg_heater:
        command[6] = command[6] | 0x80

    ##### Health On
    if is_health_on:
        command[4] = command[4] | 0x10
        
    ##### Sleep Mode
    command[15] = command[15] | sleep_mode.value
        
    ###### Wind Speed
    if wind_speed == WindSpeed.AUTO:
        # Wind speed auto zeroes both of these
        # Doing that again is unnecessary
        pass
    elif wind_speed == WindSpeed.MUTE:
        # Mute sets sets this bit plus
        command[4] = command[4] | 0x80
        # Also sets other byte to "low"
        command[6] = command[6] | 0x02
    elif wind_speed == WindSpeed.SIX:
        # "Strong" sets this bit plus
        command[4] = command[4] | 0x40
        # Also sets other byte to "high"
        command[6] = command[6] | 0x05
    else:
        # All other wind speeds clear these two bits from this byte
        command[4] = command[4] & ~0xc0
        
        # Seems like protocol intended low/med/high (0x2,0x3,0x5) then added two more speeds
        # Order is confusing
        speeds = {1: 0x2, 2: 0x06, 3: 0x03, 4: 0x07, 5: 0x05}
        
        command[6] = command[6] | speeds[wind_speed.value]
    
    ###### Mode
    command[4] = command[4] | mode.value
    
    ###### Set temperature
    temp_bytes = tempToPioneerHex(temp_celsius)
    command[9] = command[9] | temp_bytes[0]
    command[11] = command[11] | temp_bytes[1]
    
    ####### Up/Down Fan
    if up_down_mode in [FanUpDown.UP_DOWN_FLOW, FanUpDown.UP_FLOW, FanUpDown.DOWN_FLOW]:
        # Flow modes set this bit:
        command[6] = command[6] | 0x38
    # Regardless of mode, assign enum value to this byte
    command[28] = command[28] | up_down_mode.value
    
    ####### Left/Right Fan
    if left_right_mode in [FanLeftRight.LEFT_RIGHT_FLOW, FanLeftRight.LEFT_FLOW, FanLeftRight.MIDDLE_FLOW, FanLeftRight.RIGHT_FLOW]:
        # Flow modes set this bit:
        command[7] = command[7] | 0x8
    # Regardless of mode, assign enum value to this byte
    command[29] = command[29] | left_right_mode.value
    
    # Put command on message
    message = message + command

    # Append checksum byte
    message.append(calc_xor_checksum(message))
    
    return message

## Generate a message with the provided command syntax
message = generate_message(Mode.HEAT, 20)
print(binascii.hexlify(message).decode())
