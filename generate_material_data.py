# Author: Guanxiong, Ganidhu
# Generate .json files for simulating rollouts, then call ARCSim binary
# to simulate each rollout, sample data and save to an h5 file


import argparse
import yaml
import json
import os
import subprocess
import threading
import shutil
from tqdm import tqdm
from datetime import datetime
from pathlib import Path
from src_python.json import build_jsons
from src_python.h5 import set_marker_types

def run_subprocess(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        '--master_config',
        type=str, help='master config',
        required=True)
    args = p.parse_args()

    # load the assembly config
    with open(args.master_config) as f:
        master_config = yaml.load(f, Loader=yaml.FullLoader)

    # define the output directory and create it if it does not exist
    exp_name = "generate_material_data"
    config_name = Path(args.master_config).stem
    time_curr = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    project_dir = os.path.join(
        "outputs",
        exp_name,
        config_name)
    out_dir = os.path.join(
        project_dir,
        time_curr)
    out_train_dir = os.path.join(
        out_dir,
        "train")
    out_test_dir = os.path.join(
        out_dir,
        "test")
    os.makedirs(out_train_dir, exist_ok=True)
    os.makedirs(out_test_dir, exist_ok=True)

    # move master config to output file
    shutil.copy(args.master_config, f'{out_dir}/dgen_config.yaml')

    # build json's from the extracted options, and save
    # them to the output directory
    jsons = build_jsons(master_config, out_dir)
    for rollout_idx, json_config in enumerate(jsons):
        out_json_dir = json_config['h5_output']
        json_path = os.path.join(
            out_json_dir, f'{json_config["name"]}.json')
        with open(json_path, 'w') as f:
            json.dump(json_config, f, indent=4)

    cmds = []
    for rollout_idx, config in enumerate(jsons):
        out_json_dir = config['h5_output']
        json_path = os.path.join(
            out_json_dir, f'{config["name"]}.json')
         
        cmds.append(['bin/arcsim', 'simulateoffline', json_path])

    for cmd in tqdm(cmds):
        run_subprocess(cmd)


    # Add additional info to rollout h5 files.
    set_marker_types(jsons)


if __name__ == '__main__':
    main()