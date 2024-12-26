#!/usr/bin/env python3
from glob import glob
from textwrap import dedent, wrap
import threading
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
import sqlite3

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
# Edit this file to fit your needs, then save and quit.
#
# To save this command as a template, make this first line
# in this file, keeping the hash in front as well as the quotes around the
# template name:
#
# template_name="<template-name-here>"
#
# The template name can only contain letters, numbers, underscores, or hyphens.
#
# Below, write out the shell command you wish to save as a scaffold, without
# hash characters in front. If it spans multiple lines, add a backslash '\\' at the end.

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
    wrapped_txt_lines[-1] = re.sub(r'\\', '', wrapped_txt_lines[-1])
    wrapped_txt = "\n".join(wrapped_txt_lines)
    return wrapped_txt

def delete_template(template_name):
    env = get_environment()
    template_path = os.path.join(env["templates"], f"{template_name}.txt")
    os.remove(template_path)
    logger.info(f"Removed template {template_name}.")

def save_template(cmd_lines):
    if template_match := re.match(r'^#\s*template_name\s*=\s*\"([\w\-_\d]+)\"', cmd_lines[0]):
        try:
            template_name = template_match.group(1)
        except AttributeError:
            logger.error("Invalid template name. Exiting...")
            sys.exit(1)
        env = get_environment()
        template_path = os.path.join(env["templates"], f"{template_name}.txt")
        # TODO: add a config option to allow for this incremental template creation if one exists already
        # i = 0
        # new_template_path = None
        # while template_path_exists:
            # new_template_path = re.sub(r'\.txt$', '', template_path) + f"_template_{i}.txt"
            # template_path_exists = os.path.exists(new_template_path)
        # if new_template_path:
            # template_path = new_template_path
        if os.path.exists(template_path):
            logger.info("Overriding template %s", template_path)
        else:
            logger.info("Saving template to %s", template_path)
        with open(template_path, "w", encoding='utf-8') as f:
            f.writelines(cmd_lines[1:])
    else:
        logger.debug("Will not be saved as a template.")
        # env = get_environment()


def list_templates():
    env = get_environment()
    template_paths = [os.path.basename(p) for p in glob(f"{env['templates']}/*.txt")]
    template_names = [re.sub(r'\.txt', '', p) for p in template_paths]
    for name in template_names:
        print(name)


def get_parser():
    """
    Instantiates an ArgumentParser object.
    """
    parser = argparse.ArgumentParser()
    megroup = parser.add_mutually_exclusive_group()
    megroup.add_argument("--history","--hist",
                        help="Display the 5 most recent calls, or n calls specified by --histlines",
                        action="store_true")
    megroup.add_argument("--clear_history",
                        help="Clears the history file.",
                        action="store_true")
    megroup.add_argument("--edit_previous_run","-e",
                         help=dedent("""
                         Use a previous run as an editable scaffold by specifying
                         a run number. You can get the run number by running with the
                         --hist option.
                         """),
                         type=int)
    megroup.add_argument("--list_templates", "-ls",
                         help="List all templates you have defined.",
                         action='store_true')
    megroup.add_argument("--display_template",
                         help="Display the contents of a given template.")
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
                         default="default")
    parser.add_argument("--delete_template", "-dt",
                         help="Choose a template scaffold by name.",
                         type=str)
    return parser


def display_template(template: str):
    env = get_environment()
    if os.path.isfile(template_path:=os.path.join(env["templates"], f"{template}.txt")):
        subprocess.run(["less", "+G", template_path], check=True)
    else:
        logger.error("Specified template \"%s\" doesn't exist. Exiting...", template)
        sys.exit(1)


def is_valid_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except ValueError:
        return False


def get_environment():
    home=os.path.expanduser("~")
    share=os.path.join(home, ".local/share/scaffold")
    if not os.path.isdir(share):
        logger.info("share directory not found, creating at %s", share)
        os.makedirs(share, mode=0o777)
    templates = os.path.join(share, "templates")
    if not os.path.isdir(templates):
        logger.info("templates directory not found, creating at %s", templates)
        os.makedirs(templates, mode=0o777)
        default_template = os.path.join(templates, "default.txt")
        with open(default_template, "w", encoding='utf-8') as f:
            f.write(DEFAULT_SCAFFOLD_TEXT)
    if not os.path.isfile(default_template:=os.path.join(templates, "default.txt")):
        logger.info("default template not found, creating at %s", default_template)
        with open(default_template, "w", encoding='utf-8') as f:
            f.write(DEFAULT_SCAFFOLD_TEXT)
    config = os.path.join(share, "config.json")
    if not os.path.isfile(config):
        logger.info("config file not found, creating at %s", config)
        with open(config, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG_SETTINGS, f, ensure_ascii=False, indent=4)
    state=os.path.join(home, ".local/state/scaffold")
    if not os.path.isdir(state):
        logger.info("state directory not found, creating at %s", state)
        os.makedirs(state, mode=0o777)
    history_db = os.path.join(share, "history.db")
    conn = sqlite3.connect(history_db)
    cur = conn.cursor()
    query = """SELECT name FROM sqlite_master WHERE type='table' AND name='history'"""
    cur.execute(query)
    if len(cur.fetchall()) == 0: # Create history table if nonexistent
        query = """CREATE TABLE history(cmd, returncode, stdout, stderr, success, timestamp, elapsed_time_seconnds, template_used)"""
        cur.execute(query)
        conn.commit()
    conn.close()
    env = {
            "home": home,
            "share": share,
            "state": state,
            "templates": templates,
            "history_db": history_db,
            "config": config
            }
    return env


def get_config(env):
    with open(env["config"], encoding='utf-8') as f:
        config = json.load(f)
    return config


def edit_config():
    env = get_environment()
    config = get_config(env)
    subprocess.run([config["editor"], env["config"]], check=True)


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
    env = get_environment()
    template_file_path = os.path.join(env["templates"], f"{template_name}.txt")
    if not os.path.isfile(template_file_path):
        logger.error("Specified template %s does not exist.", template_name)
        logger.error("(It should exist at %s)", template_file_path)
    with open(template_file_path, encoding='utf-8') as f:
        text = f.read()
    return text


def run_history():
    env = get_environment()
    conn = sqlite3.connect(env["history_db"])
    cur = conn.cursor()
    runs = list(reversed([{"cmd": cmd, "timestamp": timestamp}
            for cmd, timestamp in cur.execute("SELECT cmd, timestamp FROM history ORDER BY timestamp DESC;").fetchall()]))
    conn.close()
    lines_to_print = get_lines_to_print(runs)
    open_less_on_tempfile(lines_to_print)


def run_clear_history():
    env = get_environment()
    conn = sqlite3.connect(env["history_db"])
    cur = conn.cursor()
    cur.execute("DELETE FROM history;")
    conn.commit()
    conn.close()


def run_edit_previous_run(run_num: int):
    env = get_environment()
    conn = sqlite3.connect(env["history_db"])
    cur = conn.cursor()
    cmd_str = (
        cur
        .execute("SELECT cmd FROM history ORDER BY timestamp DESC")
        .fetchmany(run_num)[-1][0]
    )
    conn.close()
    run_scaffold(wrap_cmd_txt(cmd_str))


def capture_and_print_process_output(process):
    def print_and_capture_output(pipe, output_list):
        for line in iter(pipe.readline, b''):
            decoded_line = line.decode('utf-8')
            print(decoded_line, end='')
            output_list.append(decoded_line)
        pipe.close()
    stdout_output, stderr_output = [], []
    stdout_thread = threading.Thread(target=print_and_capture_output, args=(process.stdout, stdout_output))
    stderr_thread = threading.Thread(target=print_and_capture_output, args=(process.stderr, stderr_output))
    stdout_thread.start()
    stderr_thread.start()
    stdout_thread.join()
    stderr_thread.join()
    process.wait()
    stdout_text = ''.join(stdout_output)
    stderr_text = ''.join(stderr_output)
    return (stdout_text, stderr_text)


def run_scaffold(text: str|None = None,
                 template: str|None = None):
    env = get_environment()
    config = get_config(env)
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
        if len(cmd) == 0:
            logger.error("No command found. Exiting...")
            sys.exit(1)
        logger.info("Running command:\n\n%s\n", wrap_cmd_txt(" ".join(cmd)))
        timestamp = str(datetime.datetime.now())
        start = time.time()
        process = subprocess.Popen(" ".join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout_text, stderr_text = capture_and_print_process_output(process)
        end = time.time()
        elapsed_time_seconds = end - start
        insert_run_into_db(" ".join(cmd).split("\\")[0],
                           process,
                           stdout_text,
                           stderr_text,
                           template,
                           timestamp,
                           elapsed_time_seconds)
        if process.returncode != 0:
            logger.error("Process exited with return code %d", process.returncode)


def insert_run_into_db(cmd_string: str,
                       completed_process: subprocess.CompletedProcess,
                       stdout_text: str,
                       stderr_text: str,
                       template: str,
                       timestamp: str,
                       elapsed_time_seconds: float):
    env = get_environment()
    try:
        conn = sqlite3.connect(env["history_db"])
        cur = conn.cursor()
        report = {}
        report["cmd"] = cmd_string
        report["returncode"] = completed_process.returncode
        report["stdout"] = str(stdout_text)
        report["stderr"] = str(stderr_text)
        report["success"] = str(completed_process.returncode == 0)
        report["timestamp"] = timestamp
        report["elapsed_time_seconds"] = elapsed_time_seconds
        report["template_used"] = template if template else "None"
        query = """
        INSERT INTO history (cmd,
                             returncode,
                             stdout,
                             stderr,
                             success,
                             timestamp,
                             elapsed_time_seconds,
                             template_used)
        VALUES(:cmd,
               :returncode,
               :stdout,
               :stderr,
               :success,
               :timestamp,
               :elapsed_time_seconds,
               :template_used)
        """
        cur.execute(query, report)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(e)
        sys.exit(1)


def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.history:
        run_history()
    elif args.clear_history:
        run_clear_history()
    elif args.edit_previous_run:
        run_edit_previous_run(args.edit_previous_run)
    elif args.list_templates:
        list_templates()
    elif args.edit_config:
        edit_config()
    elif args.display_template:
        display_template(args.display_template)
    elif args.delete_template:
        delete_template(args.delete_template)
    else:
        run_scaffold(template=args.template)

if __name__ == "__main__":
    main()
