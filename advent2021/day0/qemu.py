#!/usr/bin/env python3

import pexpect
import shutil
import sys
import time
import struct

# This file is a failed attempt to automate this challenge with QEMU. This
# would take too much time and this attempt was abandoned rather quickly.
# This file exists to show my approach and how QEMU _can_ be used to solve
# the challenge if given correct inputs.

DEBUG = False

INPUT_STRING = 'Provide input:'
QUIZ_STRING = 'Initialising Quiz...'
OUTPUT_STRING = 'Output updated. No further input required, for now.'

LEVEL_ANSWERS = [
        'Red',
        'Rudolph',
        'FROGS',
        'ROT13',
        '30258',
        'RC4',
        '3133337',
        'evilsanta1',
]

CRC_FILE_OFFSET = 0x1c3f0
EXPECTED_CRCs = [
        0xC29017C7,
        0xF58CA059,
        0x321485BF,
        0x86ECC293,
        0x4B3269A9,
        0x03B8B555,
        0xF668268D,
        0xEED10399,
]

def file_name(current_level):
    return '{}.png'.format(current_level)

def backup_file_name(current_level):
    return '{}.png.bak'.format(current_level)

def spawn_child(current_level):
    level_name = file_name(current_level)
    child =  pexpect.spawn('qemu-system-i386 -nographic {}'.format(level_name))

    if DEBUG:
        child.logfile = sys.stdout.buffer

    return child

def send_qemu_string(child, s):
    child.send(s)

def send_qemu_line(child, s):
    send_qemu_string(child, s)
    send_qemu_string(child, '\r')

def initial_setup(child):

    # First string

    child.expect(QUIZ_STRING)

    # Sleep to make sure we don't click too early

    time.sleep(0.1)
    send_qemu_string(child, 'a') # any key

def await_output_string(child):
    child.expect(OUTPUT_STRING)
    send_qemu_string(child, 'a') # any key
    child.expect(pexpect.EOF, timeout=None)

def check_solution(child):

    initial_setup(child)

    # Process completed

    await_output_string(child)

def enter_answer(child, answer):

    if len(answer) > 32:
        print('Answer ({}) length must be 32 or smaller'.format(answer))
        answer = answer[:32]

    initial_setup(child)

    # Input string

    child.expect(INPUT_STRING)

    # Send input

    time.sleep(0.1)
    send_qemu_line(child, answer)

    await_output_string(child)

def solve_level(current_level, answer = None):
    child = spawn_child(current_level)

    if answer is None:
        answer = LEVEL_ANSWERS[current_level-1]

    enter_answer(child, answer)

    time.sleep(0.1)

    return answer

def get_file_CRC(file):
    with open(file, 'rb') as f:
        val = f.read()

    raw_crc = val[CRC_FILE_OFFSET:CRC_FILE_OFFSET+4]
    return struct.unpack('<I', raw_crc)[0]

def check_level(current_level):
    child = spawn_child(current_level)
    crc = get_file_CRC(file_name(current_level)) # Grab CRC first

    check_solution(child)
    time.sleep(0.1)

    return crc == EXPECTED_CRCs[current_level-1]

def run_level(current_level, answer = None):

    # Make a backup

    backup_level(current_level)

    if answer is None:
        answer_used = solve_level(current_level)
    else:
        answer_used = solve_level(current_level, answer = answer)

    correct = check_level(current_level)

    if not correct:
        redo_level(current_level)
    else:
        print('Correctly solved level {} with answer {}'.format(current_level, answer_used))
        increment_level(current_level)

    return correct

def backup_level(current_level):
    shutil.copy2(file_name(current_level), backup_file_name(current_level))

def replace_backup(current_level):
    shutil.move(backup_file_name(current_level), file_name(current_level))

def redo_level(current_level):
    replace_backup(current_level)

def increment_level(current_level):
    shutil.copy2(file_name(current_level), file_name(current_level+1))
    replace_backup(current_level) # Save old file copy

def brute_force_level(current_level, values):
    i = 0
    for value in values:
        solved = run_level(current_level, answer=value)
        if solved:
            print('Found answer: {}'.format(value))
            break

        i += 1
        if i % 100 == 0:
            print('{}'.format(value))


def brute_force_level_seven():
    with open('primes.txt', 'r') as f:
        val = f.readlines()

    nums = [x.strip() for x in val]
    brute_force_level(7, nums)

def brute_force_level_eight():
    with open('rockyou.txt', 'r') as f:
        val = f.readlines()

    s = [x.strip() for x in val]
    brute_force_level(8, s)

def exploit():

    # First run

    backup_level(0)
    check_level(0)
    increment_level(0)

    print('Begin the automation process')

    for i in range(8):
        current_level = i+1
        run_level(current_level)

if __name__ == '__main__':
    exploit()
