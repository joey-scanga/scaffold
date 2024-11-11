from textwrap import dedent
import argparse
import re
import os
import sys
import subprocess
import tempfile
import logging
import math

logger = logging.getLogger(__name__)

SCAFFOLD_TEXT = """\
# Edit this boilerplate command to fit
# your needs, then save and quit.

docker --rm -it \\
-v <rawdata-path-here>:/input:ro \\
-v <derivatives-path-here>:/output \\
-v /opt/FreeSurfer7.3/.license:/opt/freesurfer/license.txt \\
-v <optional-segmentation-output>:/derivatives \\
-v <work-dir>:/work \\
nipreps/nibabies:latest \\
-u $(id -u):$(id -g) \\
--fs-license-file /opt/freesurfer/license.txt \\
--derivatives /derivatives \\
--age-months <age-months> \\
--participant-label <participant-label> \\
--session-id <session-id> \\
--surface-recon-method mcribs \\
--cifti-output 91k
"""

def get_parser():
    """
    Instantiates an ArgumentParser object.
    """
    parser = argparse.ArgumentParser()
    megroup = parser.add_mutually_exclusive_group()
    megroup.add_argument("--hist", "--history",
                        help="Display the 5 most recent Nibabies calls",
                        action="store_true")
    megroup.add_argument("--longhist", "--long_history",
                        help="Display all Nibabies calls using the 'less' pager",
                        action="store_true")
    megroup.add_argument("--clear_history",
                        help="Clears the history file.",
                        action="store_true")
    megroup.add_argument("-e", "--edit_previous_run",
                         help=dedent("""
                         Use a previous Nibabies run as an editable scaffold by specifying
                         a run number. You can get the run number by running with the
                         --hist option.
                         """),
                         type=int)
    parser.add_argument("--histlines",
                        help="Specify the number of lines to print out with the --hist command.",
                        type=int,
                        default=5)
    return parser


def get_paths():
    home=os.path.expanduser("~")
    share=os.path.join(home, ".local/share/nibabies-scaffold")
    if not os.path.isdir(share):
        logger.info("share directory not found, creating at %s", share)
        os.makedirs(share, mode=0o777)
    history=os.path.join(share, "history.txt")
    state=os.path.join(home, ".local/state/nibabies-scaffold")
    if not os.path.isdir(state):
        logger.info("state directory not found, creating at %s", state)
        os.makedirs(state, mode=0o777)
    paths = {
            "home": home,
            "share": share,
            "history": history,
            "state": state,
            }
    return paths


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


def get_lines_to_print(lines: list[str],
                       histlines: int|float = math.inf):
    lines_found = 0
    idx = len(lines) - 1
    final_idx = None
    while lines_found < histlines and idx > 0:
        if re.search(r'\d\d:\d\d:\d\d', lines[idx]):
            lines_found += 1
        if lines_found == histlines:
            final_idx = idx
        else:
            idx -= 1
    if final_idx:
        lines_to_print = lines[final_idx:]
    else:
        lines_to_print = lines
    lines_to_print = number_date_lines(lines_to_print)
    lines_to_print = [str.encode(l) for l in lines_to_print]
    return lines_to_print
 

def run_history(histlines: int):
    paths = get_paths()
    with open(paths["history"]) as f:
        lines = f.readlines()
    lines_to_print = get_lines_to_print(lines, histlines)
    open_less_on_tempfile(lines_to_print)


def run_long_history():
    paths = get_paths()
    with open(paths["history"]) as f:
        lines = f.readlines()
    lines_to_print = get_lines_to_print(lines)
    open_less_on_tempfile(lines_to_print)


def run_clear_history():
    paths = get_paths()
     


def run_edit_previous_run(run_num: int):
    pass


def run_scaffold():
    pass


def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.history: 
        run_history(args.histlines)
    if args.long_history:
        run_long_history()
    if args.clear_history:
        run_clear_history()
    if args.edit_previous_run:
        run_edit_previous_run(args.edit_previous_run)
    else:
        run_scaffold()



