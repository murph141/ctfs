#!/bin/bash

tar zxvf *.tar.xz 2>/dev/null
ls -rt jigsaw_pieces/* | xargs exiftool -s -s -s - | grep 'Secret data' | sed "s_.*: '\(.*\)'_\1_g" | tr -d '\n' | base64 -D

# Cleanup
rm -rf jigsaw_pieces
