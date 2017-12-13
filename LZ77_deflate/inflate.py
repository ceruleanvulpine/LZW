# INFLATE.PY
# Decompresses files compressed with deflate_not3
# Theoretically.

import heapq as hq
import sys
import bitstring as bs
import huff_functions as huff
import deflate_fns as defl

# -------------------------------------------------------------
# Function that takes care of buffer for reading individual bits from file
cur_byte = 0
bits_read = 0

# Returns the next n bits as an integer
def readbits(n):
    global cur_byte
    global bits_read
    
    read = 0;
    for i in range(0, n):
        bit_getter = 1 << (7 - bits_read)
        bit = bit_getter & cur_byte
        if bit != 0:
            bit = 1
            
        read = read * 2
        read = read + bit
        bits_read = bits_read + 1

        if bits_read == 8:
            bits_read = 0
            cur_byte = int.from_bytes(text.read(1), byteorder = "big")

    return read

# -----------------------------------------------------------

search_capacity = 32000
search_size = 0

lookahead_capacity = 258
lookahead_size = 0

chars_sent = 0 # Position of next character to send, relative to the start of the file. (Gives a consistent frame of reference for offsets.)

# Read arguments from command line to determine which file to decompress and where to 
if len(sys.argv) == 3:
    inputname = sys.argv[1]
    outputname = sys.argv[2]
elif len(sys.argv) == 2:
    inputname = sys.argv[1]
    outputname = sys.argv[1] + "_deflated"
else:
    print("Please provide at least one argument")
    sys.exit()

# Setup for lookahead and search buffers, and the dictionary "search" (which contains the locations of all the three-length strings encountered)
text = open(inputname, "rb")
cur_byte = int.from_bytes(text.read(1), byteorder = "big")
search_buffer = bytearray(search_capacity)
lookahead = bytearray(lookahead_capacity)
search = {}
    
# First read in btype (currently we are only sending one block & it is dynamically compressed, so it will always be a 3-bit 6)
btype = readbits(3)
print(btype)

clc_codelengths = {}

# Read in code lengths for clc tree, which are printed in this weird order
for i in [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]:
    clc_codelengths[i] = readbits(3)

clc_codelengths_list = []
for i in range(0, 19):
    clc_codelengths_list.append(clc_codelengths[i])
print(clc_codelengths_list)



# Construct canonical huffman code for code length codes
clc_canonical = huff.makecanonical(range(0, 19), clc_codelengths_list)
# Construct dictionary w/1/0 strings
clc_canonical_strings = huff.makecanonical_strings(range(0, 19), clc_codelengths_list, clc_canonical)
print(clc_canonical_strings)

sys.exit(1)
    
# Use this code to decode code lengths for length/literal and distance trees
# NOTE: Build tree first? Is that faster?
# 286 length/literal code lengths and 30 distance code lengths
# But code is tricky and uses extra bits

ll_codelengths_list = []
prev = -1

for j in range(0, 10):
#while not len(ll_codelengths_list) == 286:
    
    current_code = readbits(1)
    print("first bit of code: " + str(current_code))
    while not current_code in clc_canonical_dec:
        print("Current code not in decoder list; adding")
        print(current_code)
        current_code = current_code * 2
        current_code = current_code + readbits(1)
        print("Current code is now " + str(current_code))

    print(current_code)
        
    length_code = clc_canonical_dec[current_code]

    print(length_code)
    
    if length_code < 16:
        # Represent literally code lengths of 0-15
        ll_codelengths_list.append(length_code)
        prev = length_code
    elif length_code == 16:
        # 16 followed by 2 extra bits represents prev code repeated 3-6 times
        extrabits = readbits(2)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    elif length_code == 17:
        # 17 followed by 3 extra bits represents 0 repeated 3-10 times
        extrabits = readbits(3)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    elif length_code == 18:
        # 18 followed by 7 extra bits represents 0 repeated 11-138 times
        extrabits = readbits(7)
        numrepeats = 11 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    else:
        print("error")

print(ll_codelengths_list)