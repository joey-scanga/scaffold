#!/usr/bin/env python3

import re
import argparse
import subprocess
import tempfile

def get_parser():
    """
    Instantiates an ArgumentParser object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath",
                        help="Path to nibabies-scaffold history file")
    parser.add_argument("--lines_to_grab",
                        help="Number of history lines to grab",
                        default=5,
                        type=int)
    return parser

def open_less_on_tempfile(lines_to_print):
    """
    Runs the UNIX command "less" to page through the transformed lines using a NamedTemporaryFile object.

    :param lines_to_print: Transformed lines, in bytearray form
    :type lines_to_print: list[byte]
    """
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.writelines(lines_to_print)
        temp_file.flush()
        subprocess.run(["less", temp_file.name], check=True)


def number_date_lines(lines_to_print: list[str]):
    """
    Will add an index number to the output of --hist that can be inputted into the -r option.

    :param lines_to_print: List of lines in string format
    :type lines_to_print: list[str]
    :return: List of the same lines with indexes prepended to the date lines
    :rtype: list[str]
    """
    try:
        count = len([l for l in lines_to_print if re.search(r'\d\d:\d\d:\d\d', l)])
        date_indices = [i for i in range(len(lines_to_print)) if re.search(r'\d\d:\d\d:\d\d', lines_to_print[i])]
        for idx in date_indices:
            lines_to_print[idx] = f"{count}) {lines_to_print[idx]}"
            count -= 1
            # Extend the dashes to match the length of the date line after numbering
            lines_to_print[idx+1] = ('-' * len(lines_to_print[idx]))[:-1] + '\n'
        return lines_to_print
    except IndexError:
        print("Couldn't index the sessions in your recent history file; will print the sessions without any numbers. ")
        return lines_to_print


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
    lines_to_print = number_date_lines(lines_to_print, args.lines_to_grab)
    lines_to_print = [str.encode(l) for l in lines_to_print]
    open_less_on_tempfile(lines_to_print)

if __name__ == "__main__":
    main()





