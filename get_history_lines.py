#!/usr/bin/env python3

import re
import argparse
import subprocess
import tempfile
import pdb

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath",
                        help="Path to nibabies-scaffold history file")
    parser.add_argument("--lines_to_grab",
                        help="Number of history lines to grab",
                        default=5,
                        type=int)
    return parser

def open_less_on_tempfile(lines_to_print):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.writelines(lines_to_print)
        temp_file.flush()
        subprocess.run(["less", temp_file.name], check=True)


def main():
    parser = get_parser()
    args = parser.parse_args()
    with open(args.filepath) as f:
        lines = f.readlines()
    lines_found = 0
    idx = len(lines) - 1
    final_idx = None
    while lines_found < args.lines_to_grab and idx > 0:
        if re.search(r'\d\d:\d\d:\d\d', lines[idx]):
            lines_found += 1
        if lines_found == args.lines_to_grab:
            final_idx = idx
        else:
            idx -= 1
    if final_idx:
        lines_to_print = lines[final_idx:]
    else:
        lines_to_print = lines
    lines_to_print = [str.encode(l) for l in lines_to_print]
    # pdb.set_trace()
    open_less_on_tempfile(lines_to_print)

main()





