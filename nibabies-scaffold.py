from textwrap import dedent
import argparse
import re
import os
import sys
import subprocess
import tempfile

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
                         """)
    return parser




