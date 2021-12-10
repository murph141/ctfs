# Why is GDB so loud?
set startup-quietly on

# Connect to remote GDB stub and prepare for real mode debugging
target remote :1234
set tdesc filename target.xml

# Break on entrypoint
b *0x7c00
c

# Dump binary
#
# You should be able to open `level-dump` as an image.
# Make sure you hitting any key to get to the "Provide input:"
# prompt in QEMU.

b *0x82e2
c

dump binary memory level-dump 0x7c00 0x24000
