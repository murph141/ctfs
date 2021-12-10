#!/usr/bin/env python3

from unicorn import *
from unicorn.x86_const import *

import struct, threading, zlib

# Debugging

DEBUG = False

# File data

# The data dump from gdb of level eight.
BINARY_TO_EMULATE = open('images/level-eight-gdb-dump.png', 'rb').read() # load once

# List of ascii inputs to bruteforce. Inputs are provided on
# different lines.
INPUT_DATA = open('data/santa.txt', 'r').readlines()
BRUTEFORCE_INPUTS = [x.strip() for x in INPUT_DATA]

# For simplicity (and to avoid an endianness issue), provide
# expected CRC input in both potential formats.
EXPECTED_CRCS = [0xEED10399, 0x9903D1EE] # CRCs for level 8

FILE_SIZE = 115712
CRC_FILE_OFFSET = 0x1c3f0
IDAT_OFFSET = 817
IDAT_LENGTH = 114879

# Emulation addresses

IMG_BASE = 0x7c00
ENTRY_POINT = 0x82e2

# Threading

NUM_THREADS = 8
RESULTS = [False] * NUM_THREADS

# Interrupts

INT_PRINT = 0x10
INT_GET_KEY = 0x16

def print_regs(mu):

    ax = mu.reg_read(UC_X86_REG_AX)
    bx = mu.reg_read(UC_X86_REG_BX)
    cx = mu.reg_read(UC_X86_REG_CX)
    dx = mu.reg_read(UC_X86_REG_DX)
    si = mu.reg_read(UC_X86_REG_SI)
    di = mu.reg_read(UC_X86_REG_DI)
    sp = mu.reg_read(UC_X86_REG_SP)
    bp = mu.reg_read(UC_X86_REG_BP)

    cs = mu.reg_read(UC_X86_REG_CS)
    ds = mu.reg_read(UC_X86_REG_DS)
    es = mu.reg_read(UC_X86_REG_ES)
    ss = mu.reg_read(UC_X86_REG_SS)

    ip = mu.reg_read(UC_X86_REG_IP)

    print('AX: {:x}'.format(ax))
    print('BX: {:x}'.format(bx))
    print('CX: {:x}'.format(cx))
    print('DX: {:x}'.format(dx))

    print('SI: {:x}'.format(si))
    print('DI: {:x}'.format(di))

    print('SP: {:x}'.format(sp))
    print('BP: {:x}'.format(bp))

    print('CS: {:x}'.format(cs))
    print('DS: {:x}'.format(ds))
    print('ES: {:x}'.format(es))
    print('SS: {:x}'.format(ss))

    print('IP: {:x}'.format(ip))

    print()
    print('Dumping stack:')
    print()

    for i in range(1, 21):
        val = mu.mem_read((ss << 4) + sp + 2*(i-1), 2)
        print(val.hex(), end='')

        if i % 5 == 0:
            print()
        else:
            print(' ', end='')

def dump_file(mu, file_name):
    val = mu.mem_read(IMG_BASE, FILE_SIZE)
    with open(file_name, 'wb+') as f:
        f.write(val)

def check_exploit_success(mu, crcs):

    # Calculate IDAT CRC value

    val = mu.mem_read(0x7c00 + IDAT_OFFSET, IDAT_LENGTH)
    actual = zlib.crc32(val)

    return actual in crcs

def fix_up_initial_regs(mu):

    # These register values are values based on what was seen in gdb
    # when hitting `ENTRY_POINT` (0x82e2).

    mu.reg_write(UC_X86_REG_AX, 0x0e00)
    mu.reg_write(UC_X86_REG_BX, 0x0)
    mu.reg_write(UC_X86_REG_CX, 0x0)
    mu.reg_write(UC_X86_REG_DX, 0x80)

    mu.reg_write(UC_X86_REG_SI, 0x970b)
    mu.reg_write(UC_X86_REG_DI, 0x4000)

    mu.reg_write(UC_X86_REG_SP, 0xFFDE)
    mu.reg_write(UC_X86_REG_BP, 0x1)

    mu.reg_write(UC_X86_REG_CS, 0x0)
    mu.reg_write(UC_X86_REG_DS, 0x0)
    mu.reg_write(UC_X86_REG_ES, 0x0)
    mu.reg_write(UC_X86_REG_SS, 0x7000)

    # Write values to stack

    mu.mem_write(0x7ffde, struct.pack('<H', 0x4000))
    mu.mem_write(0x7ffde+0x02, struct.pack('<H', 0x956f))
    mu.mem_write(0x7ffde+0x04, struct.pack('<H', 0x1))
    mu.mem_write(0x7ffde+0x06, struct.pack('<H', 0xffee))
    mu.mem_write(0x7ffde+0x08, struct.pack('<H', 0x0))
    mu.mem_write(0x7ffde+0x0a, struct.pack('<H', 0x80))
    mu.mem_write(0x7ffde+0x0c, struct.pack('<H', 0x0))
    mu.mem_write(0x7ffde+0x0e, struct.pack('<H', 0x3920))
    mu.mem_write(0x7ffde+0x10, struct.pack('<H', 0x7fbc))

def hook_interrupt(mu, intno, user_data):

    ah = mu.reg_read(UC_X86_REG_AH)

    if intno == INT_GET_KEY and ah == 0x00:
        guess = user_data[0]

        to_write = ord('\r')
        if len(guess) > 0:
            to_write = guess[0]
            guess = guess[1:] # chop off a character in our guess
            user_data[0] = guess

        if DEBUG:
            print('Injecting keystroke: {}'.format(chr(to_write)))

        mu.reg_write(UC_X86_REG_AL, to_write)

    elif intno == INT_PRINT:
        pass # Ignore

    else:
        print("Unknown interrupt no: {:x}", intno)
        mu.emu_stop()

def thread_func(input_str, crcs, thread_num):
    RESULTS[thread_num] = emulate(input_str, crcs)

def exploit():

    expected_crcs = EXPECTED_CRCS
    potential_inputs = BRUTEFORCE_INPUTS
    num_threads = NUM_THREADS

    for i in range(0, len(potential_inputs), num_threads):

        threads = [None] * num_threads
        for j in range(num_threads):
            inp = potential_inputs[i+j]
            t = threading.Thread(target=thread_func, args=(inp, expected_crcs, j))
            t.start()
            threads[j] = t

            if (i+j) % 100 == 0:
                print('Trying input: {}'.format(inp))

        for j in range(num_threads):
            threads[j].join()

        for j in range(NUM_THREADS):
            if RESULTS[j]:
                print('Found solution: {}'.format(potential_inputs[i+j]))
                quit()

# The name of the game with emulate is speed and accuracy. If we can accurately
# emulate the code quickly, we can bruteforce the answers. These two attributes
# are achieved in a few different ways:
#
# Speed:
# - Instead of emulating the whole program, we run the program in gdb up to a
#   certain point (`ENTRY_POINT`) and dump memory. Afterwards, we init registers
#   to the values they would be during normal execution and continue emulation.
# - We *only* hook interrupts and do not hook code. This allows less overhead
#   in emulation from Unicorn.
# - We only emulate until shortly after all the CRC code has run. This is
#   achieved by specifying a `count` to `emu_start`. We aren't hooking code due
#   to the item above, so this is our best workaround.
# - We add support for multithreading so that we can paralleize the work.
#
# Accuracy:
# - We mirror register values at the beginning of our emulation and make sure
#   to emulate all the way through the relevant code.
# - Verify inputs match expected CRCs for early levels and for later levels
#   with canned inputs.
# - We cross-check against the list of expected CRCs in code to validate when
#   we have found the correct input.

def emulate(guess, crcs):

    mu = Uc(UC_ARCH_X86, UC_MODE_16)
    guess = bytearray(guess.encode('utf-8'))

    try:
        mem_size = 2 * 1024 * 1024 # 2 MiB
        mu.mem_map(0, mem_size)

        mu.mem_write(IMG_BASE, BINARY_TO_EMULATE) # MBR + more

        if DEBUG:
            print('Add hooks')

        # Note: we don't have a code hook since it slows down emulation so much.
        # Instead, we populate registers with their initial values.
        fix_up_initial_regs(mu)

        mu.hook_add(UC_HOOK_INTR, hook_interrupt, user_data=[guess])

        if DEBUG:
            print('Start emu')

        mu.emu_start(ENTRY_POINT, 0, count=3000000)

        if DEBUG:
            print('Emulation done')

    except UcError as e:

        print('Error during emulation: {}'.format(e))
        print('Printing registers')

        print_regs(mu)

    return check_exploit_success(mu, crcs)

if __name__ == '__main__':
    exploit()
