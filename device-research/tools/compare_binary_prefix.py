"""Compare two binary files over the length of the shorter file."""

import hashlib
import pathlib
import sys


left_path, right_path = map(pathlib.Path, sys.argv[1:3])
left = left_path.read_bytes()
right = right_path.read_bytes()
size = min(len(left), len(right))
positions = [i for i, (a, b) in enumerate(zip(left[:size], right[:size])) if a != b]
print(f"left={len(left)} right={len(right)} compared={size}")
print("left_prefix_sha256=" + hashlib.sha256(left[:size]).hexdigest())
print("right_prefix_sha256=" + hashlib.sha256(right[:size]).hexdigest())
if positions:
    print(f"different_bytes={len(positions)} first=0x{positions[0]:X} last=0x{positions[-1]:X}")
else:
    print("different_bytes=0")
if len(right) > size:
    tail = right[size:]
    print(f"right_tail={len(tail)} nonzero={sum(value != 0 for value in tail)} sha256={hashlib.sha256(tail).hexdigest()}")

