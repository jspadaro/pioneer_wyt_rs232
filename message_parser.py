#!/usr/bin/python3
import binascii
import struct

# Convert desired temperature to pioneer serial format
def toC(fahrenheit):
    return (float(fahrenheit)-32.0)*(5.0/9.0)

def toF(celsius):
    return (float(celsius)*(9.0/5.0))+32.0

# Round down to .25, .5, .75
def toNearestQuarter(num):
    return int(num*4)/4

def toPioneerHex(celsius):
    celsius = toNearestQuarter(celsius)
    
    # Pioneer first nibble is X where, 31-X = celsius temp
    first_nibble = 31-int(celsius)
    
    # Final nibble is 0, 4, 8, or c for .25, .5, .75
    final_nibble_options = {0.0: 0x0, 0.25: 0x4, 0.5: 0x8, 0.75: 0xc}
    final_nibble = final_nibble_options[(celsius % 1)]
    
    # And 3 0's in the middle, not sure what they are for
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

# Takes message as either string or byte string to parse
# This should be hexlified!
# Only handles outbound messages from wifi adapter right now
def parse_sent_message(message):
    if type(message) != bytes:
        print('Argument must be bytes')
        return False
    
    # Verify checksum first
    if not check_xor_checksum(binascii.unhexlify(message)):
        print(f'Invalid checksum on message.  Calculated: {calc_xor_checksum(message[:-1]):x}')
        print('Is message data hexlified? Continuing anyway...')
    
    if message[0:2] != b'bb':
        print(f'''Message does not begin with 0xbb, unknown message type''')
        return False
    
    if message[2:6] == b'0001':
        print(f'''Message is from wifi adapter to hvac''')
    elif message[2:6] == b'0100':
        print(f'''Message is from hvac to wifi adapter''')

    command = message[6:8]

    # Would rather use 'match' from python 3.10+, but sticking with older form for now
    if command == b'0a':
        if message == b'bb00010a03050000b6' or message == b'bb00010a03050008be':
            print(f'''Haven't reversed command {command} yet, but have seen this message before''')
        else:
            print(f'''Haven't reversed command {command} yet, but have NOT seen this message before''')
        return False
    elif command == b'09':
        if message == b'bb000109020500b4':
            print(f'''Haven't reversed command {command} yet, but have seen this message before''')
        else:
            print(f'''Haven't reversed command {command} yet, but have NOT seen this message before''')
        return False
    elif command == b'04':
        if message == b'bb000104020100bd':
            print(f'''Haven't reversed command {command} yet, but have seen this message before''')
        else:
            print(f'''Haven't reversed command {command} yet, but have NOT seen this message before''')
        return False
    elif command == b'03':
        # Cut off just the part we care about and unhexlify if we need to deal with whole bytes
        contents = binascii.unhexlify(message[8:])
        
        ###### Do bitwise checking for various options/settings
        
        ###### On / Off
        is_on = (contents[3] & 0x04) > 0
        print(f'Is on: {is_on}')
        
        ###### Display On/Off
        is_display_on = (contents[3] & 0x40) > 0
        print(f'Display on: {is_display_on}')

        ###### Buzzer On/Off
        is_buzzer_on = (contents[3] & 0x20) > 0
        print(f'Buzzer on: {is_buzzer_on}')

        ###### Eco mode
        is_eco = (contents[3] & 0x80) > 0
        print(f'Eco mode: {is_eco}')
        
        ##### 8 Degree Heater
        is_8_deg_heater = (contents[6] & 0x80) > 0
        print(f'8 Degree Heater: {is_8_deg_heater}')

        ##### Health On
        is_health_on = (contents[4] & 0x10) > 0
        print(f'Health on: {is_health_on}')
        
        ##### Sleep Mode
        sleep_mode = 'Off'
        sleep_bits = (contents[15] & 0x3)
        if sleep_bits == 0x1:
            sleep_mode = 'Standard'
        elif sleep_bits == 0x2:
            sleep_mode = 'The Aged'
        elif sleep_bits == 0x3:
            sleep_mode = 'Child'
        print(f'Sleep mode: {sleep_mode}')
        
        ##### Wind Speed
        # Wind speed has a few bits set
        # Mute   - 0x82 - "low" (0x02) + an upper bit set
        # Strong - 0x45 - "high" (0x05) + an upper bit set
        # No other upper bits - so 0xc0 should catch
        wind_ub = contents[4] & 0xc0
        # Lower bits are always set using a max of 0x7 (3 bits)
        wind_lb = contents[6] & 0x7
        wind = wind_ub | wind_lb
        
        wind_speed = 'Unknown'
        # Just make it a setting 1-6 (1 = low, 6 = strong)
        wind_speeds = {0x02: 1, 0x06: 2, 0x03: 3, 0x07: 4, 0x05: 5, 0x45: 6}
        if wind in wind_speeds:
            wind_speed = wind_speeds[wind]
        else:
            if wind == 0x82:
                wind_speed = 'Mute'
            elif wind == 0x0:
                wind_speed = 'Auto'
        print(f'Wind speed: {wind_speed}')
        
        ##### Mode
        mode = 'Unknown'
        mode_byte = contents[4]&0xf
        
        if mode_byte == 0x1:
            mode = 'Heat'
        elif mode_byte == 0x2:
            mode = 'Dehumidify'
        elif mode_byte == 0x3:
            mode = 'Cool'
        elif mode_byte == 0x7:
            mode = 'Fan'
        elif mode_byte == 0x8:
            mode = 'Auto'
        print(f'AC Mode: {mode}')
        
        ##### Set temperature
        # Get temperature, two nibbles in different parts of message
        temp_celsius = fromPioneerHex(nibbleToHexInt(message[19]), nibbleToHexInt(message[24]))
        temp_f = toF(temp_celsius)
        print(f'Set temperature: {temp_f:.2f}F')
        
        ###### Up/Down Fan
        # Setting bits on this byte sets "flow" on/off
        is_flow = (contents[6] & 0x38) == 0x38
        up_down_fan = 'Unknown'
        
        # Could probably also just look at these 5 bits to tell
        if is_flow:
            if contents[28] & 0x18:
                up_down_fan = 'Up/Down Flow'
            elif contents[28] & 0x10:
                up_down_fan = 'Up Flow'
            elif contents[28] & 0x8:
                up_down_fan = 'Down Flow'
        else:
            # Not sure if other bits are used for anything, playing it safe
            fix_bits = contents[28] & 0x7
            
            if fix_bits == 0x1:
                up_down_fan = 'Top Fix'
            elif fix_bits == 0x2:
                up_down_fan = 'Upper Fix'
            elif fix_bits == 0x3:
                up_down_fan = 'Middle Fix'
            elif fix_bits == 0x4:
                up_down_fan = 'Above Down Fix'
            elif fix_bits == 0x5:
                up_down_fan = 'Bottom Fix'
        if (contents[28] & 0x1f) == 0:
            up_down_fan = 'Auto'
        print(f'Up/Down Fan: {up_down_fan}')
        
        ###### Left/Right Fan
        # Setting bits on this byte sets "flow" on/off
        is_flow = (contents[7] & 0x8) == 0x8
        left_right_fan = 'Unknown'
        
        # Left right appears to always use lower 6 bits from this byte
        lr_byte = contents[29] & 0x3f
        if is_flow:
            if lr_byte == 0x08:
                left_right_fan = 'Left-Right Flow'
            elif lr_byte == 0x10:
                left_right_fan = 'Left Flow'
            elif lr_byte == 0x18:
                left_right_fan = 'Middle Flow'
            elif lr_byte == 0x20:
                left_right_fan = 'Right Flow'
        else:
            if lr_byte == 0x1:
                left_right_fan = 'Left Fix'
            elif lr_byte == 0x2:
                left_right_fan = 'A Bit Left Fix'
            elif lr_byte == 0x3:
                left_right_fan = 'Middle Fix'
            elif lr_byte == 0x4:
                left_right_fan = 'Center Right Fix'
            elif lr_byte == 0x5:
                left_right_fan = 'Right Fix'
        if lr_byte == 0:
            left_right_fan = 'Auto'
        print(f'Left/Right Fan: {left_right_fan}')
    else:
        print(f'Unknown command: {command}')
        return False

print('\nThis script will parse supported hexlified messages.  Example message:')
print('bb0001031d000064015c0000800000000000000000000000000000000000000003839d\n')
while True:
    message = input('Enter a message to parse: ').strip().encode('utf-8')
    print('') # Newline
    parse_sent_message(message)
    print('') # Newline
