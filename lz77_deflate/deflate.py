# DEFLATE.py
# Compresses files with a DEFLATE-ish algorithm. (Working towards compliance.)

import heapq as hq
import sys
import huff_functions as huff

search_capacity = 32000
lookahead_capacity = 258
search_size = 0
lookahead_size = 0

# Read arguments from command line to determine file to decompress and where to decompress it to
if len(sys.argv) == 3:
    inputname = sys.argv[1]
    outputname = sys.argv[2]
elif len(sys.argv) == 2:
    inputname = sys.argv[1]
    outputname = sys.argv[1] + "_deflated"
else:
    print("Please provide at least one argument")
    sys.exit()

# Setup for lookahead and search buffers
text = open(inputname, "rb")
search = bytearray(search_capacity) # NOTE: This is a dumb inefficient way to do this, replace with hash chained table
lookahead = bytearray(lookahead_capacity)

# Now use LZ77 algorithm to compute three lists: offsets, lengths and next_chars; will be compressed and sent in triples
offsets = []
lengths = []
next_chars = []

# Fill lookahead buffer with first [lookahead_capacity] chars
next_char = text.read(1)
while (lookahead_size != lookahead_capacity) and next_char:
    lookahead[lookahead_size] = int.from_bytes(next_char, byteorder = "big")
    lookahead_size = lookahead_size + 1
    next_char = text.read(1)

# Main LZ77 loop
while not lookahead_size <= 0:
    
    to_encode = 0 # TO_ENCODE: first char in lookahead not coded for
    offset = 0
    length = 0
    shift = 0
      
    for i in range(len(search) - search_size, len(search)):
        if search[i] == lookahead[to_encode]:
            offset = len(search) - i
            break

    if not offset == 0:
        length = 1
        to_encode = to_encode + 1
        while offset > length and search[len(search) - offset + length] == lookahead[to_encode] and not to_encode == lookahead_size - 1:
            to_encode = to_encode + 1
            length = length + 1
            # When loop terminates, length = offset or search[len(search) - offset + length] is first char that doesn't match
        if length == offset:
            while lookahead[length - offset] == lookahead[to_encode] and not to_encode == lookahead_size - 1:
                length = length + 1
                to_encode = to_encode + 1
            # When loop terminates, length = to_encode = lookahead_size or lookahead[length - offset] is first char to not match

        # Write offset and length in 1 byte each, and next char in one byte NOTE: change this for possible smaller buffer?
        # NOTE: this is a hacky fix to not use matches of len 1 and 2, fix with hash chaining 3-length strings
        if length == 1 or length == 2:
            offsets.append(0)
            lengths.append(0)
            next_chars.append(lookahead[to_encode - length])
        
        offsets.append(offset)
        lengths.append(length)
        next_chars.append(lookahead[to_encode])

        shift = length + 1
    else:
        offsets.append(0)
        lengths.append(0)
        next_chars.append(lookahead[to_encode])
    
        shift = 1
      
    # Shift lookahead and search buffers

    # Shift search buffer left by [shift] chars, and fill from lookahead
    for i in range(0, len(search) - shift):
        search[i] = search[i+shift]
    for i in range(0, shift):
        search[len(search) - shift + i] = lookahead[i]
    # Increase size of search buffer if not already full
    search_size = search_size + shift
    if search_size >= search_capacity:
        search_size = search_capacity

    # Shift lookahead buffer left by [shift] chars, and fill from text
    for i in range(0, lookahead_size - shift):
        lookahead[i] = lookahead[i + shift]
    lookahead_size = lookahead_size - shift
    for i in range(0, shift):
        if next_char:
            lookahead[len(lookahead) - shift + i] = int.from_bytes(next_char, byteorder = "big")
            lookahead_size = lookahead_size + 1
            next_char = text.read(1)
        else:
            break


# Open output stream; towrite is a one-bye buffer which fills with the bits we want to be written as bits_written counts up to eight
output = open(outputname, "wb")
towrite = 0
bits_written = 0

# Currently we are putting all data in one dynamically compressed block
# So write BFINAL = 1 and BTYPE = 10 to the buffer, to signify that it is final and dynamically compressed
bit_flicker = 6 << 5
towrite = towrite | bit_flicker
bits_written = 3

# Constructing huffman tree for lengths and literals
# First count frequencies of codes: 0-255 are literals, 256 is end of block, 257-285 reprsent lengths (some are ranges of lengths, with extra bits after symbol)
# NOTE: Not sure this program actually uses 256 anywhere? Fix that 
ll_frequencies = {}
for nc in next_chars:
    if nc in ll_frequencies:
        ll_frequencies[nc] = ll_frequencies[nc] + 1
    else:
        ll_frequencies[nc] = 1

for l in lengths:
    code = -1
    if l <= 10:
        code = 254 + l
    elif l == 11 or l == 12:
        code = 265
    elif l == 13 or l == 14:
        code = 266
    elif l == 15 or l == 16:
        code = 267
    elif l == 17 or l == 18:
        code = 268
    elif l >= 19 and l <= 22:
        code = 269
    elif l >= 23 and l <= 26:
        code = 270
    elif l >= 27 and l <= 30:
        code = 271
    elif l >= 31 and l <= 34:
        code = 272
    elif l >= 35 and l <= 42:
        code = 273
    elif l >= 43 and l <= 50:
        code = 274
    elif l >= 51 and l <= 58:
        code = 275
    elif l >= 59 and l <= 66:
        code = 276
    elif l >= 67 and l <= 82:
        code = 277
    elif l >= 83 and l <= 98:
        code = 278
    elif l >= 99 and l <= 114:
        code = 279
    elif l >= 115 and l <= 130:
        code = 280
    elif l >= 131 and l <= 162:
        code = 281
    elif l >= 163 and l <= 194:
        code = 282
    elif l >= 195 and l <= 226:
        code = 283
    elif l >= 227 and l <= 257:
        code = 284
    elif l == 258:
        code = 285

    if code in ll_frequencies:
        ll_frequencies[code] = ll_frequencies[code] + 1
    else:
        ll_frequencies[code] = 1

# Build generic huffman tree from frequencies
ll_forest = huff.build_forest(ll_frequencies)
ll_tree = huff.buildhufftree(ll_forest)

# Get ordered list of code lengths to create canonical huffman code 
ll_codelengths = huff.getcodelengths(ll_tree)
ll_codelengths_list = []
for i in range(0, 286):
    if i in ll_codelengths:
        ll_codelengths_list.append(ll_codelengths[i])
    else:
        ll_codelengths_list.append(0)

# Construct list of code length codes for canonical huffman tree for lengths/literals
# See deflate docs for length encoding scheme
prev = -1
repeat_length = 0
codetowrite = 0
codelengthcodes = []
for length in ll_codelengths_list:
    
    # If the code length is a repeat, increase the repeat length
    # If we have reached the limit of repeat size, output code for repeat section
    if prev == length:
        repeat_length = repeat_length + 1
        if 1 <= prev <= 15 and repeat_length == 6:
            # Write repeat code (16) plus code for 6 repeats (3)
            codelengthcodes.append(16)
            codelengthcodes.append(3)
            repeat_length = 0
        elif prev == 0 and repeat_length == 138:
            # Write long zero repeat code (18) plus code for 138 repeats (127)
            codelengthcodes.append(18)
            codelengthcodes.append(127)
            repeat_length = 0

    # If we have changed code lengths, output code for last repeat section if
    # there is one, then output code for new character
    else:
        if repeat_length != 0:
            # NOTE: TO FIX: If repeat length is 1 or 2, just output code more times
            if prev == 0:
                if 3 <= repeat_length <= 10:
                    codelengthcodes.append(17)
                    codelengthcodes.append(repeat_length - 3)
                elif 11 <= repeat_length <= 138:
                    codelengthcodes.append(18)
                    codelengthcodes.append(repeat_length - 11)
            else:
                if 3 <= repeat_length <= 6:
                    codelengthcodes.append(16)
                    codelengthcodes.append(repeat_length - 3)
             repeat_length = 0
        codelengthcodes.append(length)
        prev = length

# Compress THOSE code length codes with ANOTHER canonical huffman code and output

    

# Construct canonical huffman code for length/literal tree

# Repeat this all for distances

# Output compressed data


