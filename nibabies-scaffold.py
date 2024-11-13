#!/usr/bin/env python3
from glob import glob
from textwrap import dedent, wrap
import argparse
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Create a handler to output to the console
console_handler = logging.StreamHandler()
# Set the logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# Add the handler to the logger
logger.addHandler(console_handler)

DEFAULT_SCAFFOLD_TEXT = """\
# Edit this boilerplate command to fit your needs, then save and quit.
# To save this command as a template, make this first line
# in this file, keeping the hash in front as well as the quotes around the
# template name:
#
# template_name="<template-name-here>"
#
# The template name can only contain letters, numbers, underscores, or hyphens.

docker run --rm -it \\
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

DEFAULT_CONFIG_SETTINGS = {
        "editor": "nano",
}

def wrap_cmd_txt(cmd_text):
    wrapped_txt_lines = wrap(cmd_text,
                             subsequent_indent='\t',
                             break_long_words=False,
                             break_on_hyphens=False,
                             tabsize=4,)
    wrapped_txt_lines = [f"{l} \\" for l in wrapped_txt_lines]
    wrapped_txt = "\n".join(wrapped_txt_lines)
    return wrapped_txt


def save_template(cmd_lines):
    if template_match := re.match(r'^#\s*template_name\s*=\s*\"([\w\-_\d]+)\"', cmd_lines[0]):
        try:
            template_name = template_match.group(1)
        except AttributeError:
            logger.error("Invalid template name. Exiting...")
            sys.exit(1)
        paths = get_paths()
        template_path = os.path.join(paths["templates"], f"{template_name}.txt")
        template_path_exists = os.path.exists(template_path)
        i = 0
        new_template_path = None
        while template_path_exists:
            new_template_path = re.sub(r'\.txt$', '', template_path) + f"_template_{i}.txt"
            template_path_exists = os.path.exists(new_template_path)
        if new_template_path:
            template_path = new_template_path
        logger.info("Saving template to %s", template_path)
        # TODO: prevent colliding file names
        with open(template_path, "w", encoding='utf-8') as f:
            f.writelines(cmd_lines[1:])
    else:
        logger.debug("Will not be saved as a template.")
        # paths = get_paths()


def list_templates():
    paths = get_paths()
    template_paths = [os.path.basename(p) for p in glob(f"{paths['templates']}/*.txt")]
    template_names = [re.sub(r'\.txt', '', p) for p in template_paths]
    for name in template_names:
        print(name)
        print('-' * len(name))
        print('\n' + get_template_text(name) + '\n')


def get_parser():
    """
    Instantiates an ArgumentParser object.
    """
    parser = argparse.ArgumentParser()
    megroup = parser.add_mutually_exclusive_group()
    megroup.add_argument("--history","--hist", 
                        help="Display the 5 most recent Nibabies calls, or n calls specified by --histlines",
                        action="store_true")
    megroup.add_argument("--long_history","--longhist", 
                        help="Display all Nibabies calls using the 'less' pager",
                        action="store_true")
    megroup.add_argument("--clear_history",
                        help="Clears the history file.",
                        action="store_true")
    megroup.add_argument("--edit_previous_run","-e", 
                         help=dedent("""
                         Use a previous Nibabies run as an editable scaffold by specifying
                         a run number. You can get the run number by running with the
                         --hist option.
                         """),
                         type=int)
    megroup.add_argument("--textwrap",
                         help="testing textwrap, arg should be index of history run",
                         type=int,
                         default=1
                         )
    megroup.add_argument("--list_templates",
                         help="List all templates you have defined.",
                         action='store_true')
    megroup.add_argument("--edit_config",
                         help="Opens a text editor on your config file (USE AT YOUR OWN RISK!)",
                         action='store_true')
    parser.add_argument("--histlines",
                        help="Specify the number of lines to print out with the --hist command. (default is 5)",
                        type=int,
                        default=5)
    parser.add_argument("--template", "-t",
                         help="Choose a template scaffold by name.",
                         type=str,
                         default="nibabies")
    return parser

def is_valid_json(filepath):
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        return True
    except ValueError:
        return False


def get_paths():
    home=os.path.expanduser("~")
    share=os.path.join(home, ".local/share/nibabies-scaffold")
    if not os.path.isdir(share):
        logger.info("share directory not found, creating at %s", share)
        os.makedirs(share, mode=0o777)
    templates = os.path.join(share, "templates")
    if not os.path.isdir(templates):
        logger.info("templates directory not found, creating at %s", templates)
        os.makedirs(templates, mode=0o777)
        nibabies_template = os.path.join(templates, "nibabies.txt")
        with open(nibabies_template, "w") as f:
            f.write(DEFAULT_SCAFFOLD_TEXT)
    config = os.path.join(share, "config.json")
    if not os.path.isfile(config):
        logger.info("config file not found, creating at %s", config)
        with open(config, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG_SETTINGS, f, ensure_ascii=False, indent=4)
    history=os.path.join(share, "history.json")
    if not os.path.isfile(history):
        logger.info("creating history file at %s", history)
        with open(history, 'w', encoding='utf-8') as f:
            json.dump({"history": []}, f, ensure_ascii=False, indent=4)
    elif not is_valid_json(history):
        logger.warning("history file corrupted, recreating at %s", history)
        with open(history, 'w', encoding='utf-8') as f:
            json.dump({"history": []}, f, ensure_ascii=False, indent=4)
    state=os.path.join(home, ".local/state/nibabies-scaffold")
    if not os.path.isdir(state):
        logger.info("state directory not found, creating at %s", state)
        os.makedirs(state, mode=0o777)
    paths = {
            "home": home,
            "share": share,
            "history": history,
            "state": state,
            "templates": templates,
            "config": config
            }
    return paths


def get_config(paths):
    with open(paths["config"], encoding='utf-8') as f:
        config = json.load(f)
    return config


def edit_config():
    paths = get_paths()
    config = get_config(paths)
    subprocess.run([config["editor"], paths["config"]], check=True)


def open_less_on_tempfile(lines_to_print):
    """
    Runs the UNIX command "less" to page through the transformed lines using a NamedTemporaryFile object.

    :param lines_to_print: Transformed lines, in bytearray form
    :type lines_to_print: list[byte]
    """
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.writelines(lines_to_print)
        temp_file.flush()
        subprocess.run(["less", "+G", temp_file.name], check=True)


def get_lines_to_print(runs):
    lines = []
    for idx, run in enumerate(runs):
        lines.append(f"{len(runs) - idx}) {run['timestamp']}\n") 
        lines.append('-' * len(lines[-1]) + '\n') # Print underline to above line
        lines.append(f"{wrap_cmd_txt(run['cmd'])}\n")
        if (idx + 1) != len(runs):
            lines.append("\n")
    lines_to_print = [str.encode(l) for l in lines]
    return lines_to_print


def get_template_text(template_name: str):
    paths = get_paths()
    template_file_path = os.path.join(paths["templates"], f"{template_name}.txt")
    if not os.path.isfile(template_file_path):
        logger.error("Specified template %s does not exist.", template_name)
        logger.error("(It should exist at %s)", template_file_path)
    with open(template_file_path, encoding='utf-8') as f:
        text = f.read()
    return text
 

def run_history(histlines: int):
    paths = get_paths()
    with open(paths["history"], encoding='utf-8') as f:
        history_dict = json.load(f)
    runs = history_dict["history"]
    if histlines <= len(runs):
        runs = runs[len(runs) - histlines:]  
    lines_to_print = get_lines_to_print(runs)
    open_less_on_tempfile(lines_to_print)


def run_long_history():
    paths = get_paths()
    with open(paths["history"], encoding='utf-8') as f:
        history_dict = json.load(f)
    runs = history_dict["history"]
    lines_to_print = get_lines_to_print(runs)
    open_less_on_tempfile(lines_to_print)


def run_clear_history():
    paths = get_paths()
    with open(paths["history"], "w", encoding='utf-8'):
        pass # Opening in write-mode will clear the file


def run_edit_previous_run(run_num: int):
    paths = get_paths()
    with open(paths["history"], encoding='utf-8') as f:
        history_dict = json.load(f)
    runs = history_dict["history"]
    index_of_run = len(runs) - run_num
    try:
        run = runs[index_of_run]
    except IndexError:
        logger.error("Index %d out of bounds", index_of_run)
        sys.exit(1)
    run_scaffold(wrap_cmd_txt(run["cmd"]))
    
        
def run_scaffold(text: str|None = None,
                 template: str|None = None):
    paths = get_paths()
    config = get_config(paths)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        if text == None and template == None:
            logger.error("No template specified. Exiting...")
            sys.exit(1)
        elif text == None:
            template_text = get_template_text(template)
            temp_file.write(str.encode(template_text))
        else:
            temp_file.write(str.encode(text))
        temp_file.flush()
        subprocess.run([config["editor"], temp_file.name], check=True)
        with open(temp_file.name, encoding='utf-8') as f:
            lines = f.readlines()
        save_template(lines)
        lines = [re.sub(r'(\n|\\)$', '', l) for l in lines if not re.match(r'\s*#', l) and not re.match(r'^\s*\n?$', l)]
        lines = [re.sub(r'\s+', ' ', l) for l in lines]
        cmd = (" "
               .join(lines)
               .split(" ")
              )
        cmd = list(filter(None, cmd))
        logger.info("Running command:\n\n%s\n", wrap_cmd_txt(" ".join(cmd)))
        timestamp = str(datetime.datetime.now())
        start = time.time()
        completed_process = subprocess.run(cmd, capture_output=True, text=True)
        end = time.time()
        elapsed_time_seconds = end - start
        report = create_run_report_obj(" ".join(cmd),
                                       completed_process,
                                       timestamp,
                                       elapsed_time_seconds)
        if completed_process.returncode != 0:
            logger.error("Process exited with return code %d", completed_process.returncode)
        with open(paths["history"], 'r') as f:
            data = json.load(f)
        data["history"].append(report)
        with open(paths["history"], 'w') as f:
            json.dump(data, f, indent=4)


def create_run_report_obj(cmd_string: str,
                          completed_process: subprocess.CompletedProcess,
                          timestamp: str,
                          elapsed_time_seconds: float):
    report = {}
    report["cmd"] = cmd_string
    report["returncode"] = completed_process.returncode
    report["stdout"] = str(completed_process.stdout)
    report["stderr"] = str(completed_process.stderr)
    report["success"] = str(completed_process.returncode == 0)
    report["timestamp"] = timestamp
    report["elapsed_time_seconds"] = elapsed_time_seconds
    return report
        

def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.history: 
        run_history(args.histlines)
    elif args.long_history:
        run_long_history()
    elif args.clear_history:
        run_clear_history()
    elif args.edit_previous_run:
        run_edit_previous_run(args.edit_previous_run)
    elif args.list_templates:
        list_templates()
    elif args.edit_config:
        edit_config()
    else:
        run_scaffold(template=args.template)

if __name__ == "__main__":
    main()
