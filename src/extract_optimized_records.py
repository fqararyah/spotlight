#!/usr/bin/env python3

import os
import sys
import yaml
import re
from collections import defaultdict

METRICS_OF_INTEREST = [
    "edp",
    "energy",
    "delay",
    "latency",
    "throughput",
    "area",
    "power",
]

OPT_LAYER_RE = re.compile(r"^(\d+)\s+opt_layer\b")
KV_RE = re.compile(r"^\s*([a-zA-Z_]+)\s*:\s*([0-9eE.+-]+)\s*$")
INLINE_METRIC_RE = re.compile(
    r"\b(edp|energy|delay|latency|throughput|area|power)\s+([0-9eE.+-]+)"
)
COMPLETE_RECORD_RE = re.compile(
    r"^(.*?\bpower\s+[0-9eE.+-]+)"
)



def read_layer_representations(layer_file):
    layers = []
    with open(layer_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                layers.append(line)
    return layers


def read_results(results_file):
    """
    Returns:
      results[layer_index] = list of metric dicts
    """
    results = defaultdict(list)

    with open(results_file, "r") as f:
        for line in f:
            raw_line = line.rstrip("\n")
            line = raw_line.strip()
            if not line:
                continue

            m = OPT_LAYER_RE.match(line)
            if not m:
                continue

            layer_idx = int(m.group(1))
            record = {}

            # Keep layer id
            record["layer_id"] = layer_idx

            # Extract metrics (KEEP STRING FORMATTING)
            for key, val in INLINE_METRIC_RE.findall(line):
                record[key] = val

            # Extract full performance record string (up to power)
            m_full = COMPLETE_RECORD_RE.match(line)
            if m_full:
                record["complete_performance_record_str"] = "{}".format(">> " + str(m_full.group(1)))

            if record:
                results[layer_idx].append(record)

    return results

def pick_best(results, metric):
    """
    Pick the best (minimum) record per layer for a given metric.
    """
    best = {}

    for layer_idx, records in results.items():
        valid = [r for r in records if metric in r]
        if not valid:
            continue
        best[layer_idx] = min(valid, key=lambda r: r[metric])

    return best


def build_yaml(best_records, layer_reprs):
    out = {}
    for idx, record in best_records.items():
        layer_name = layer_reprs[idx]
        out[layer_name] = record
    return out


def main():
    shapes_path = os.path.join(os.path.dirname(__file__), '../outputs/unique_shapes/')
    out_path_template = os.path.join(os.path.dirname(__file__), '../outputs/layers_perf_records/')
    metrics = ['EDP']
    results_root_dir = '26_01_09_18'
    for metric in metrics:
        for dirpath, _, files in os.walk(shapes_path):
            for fn in files:
                if '.out' not in fn:
                    continue         
                input_file = os.path.join(dirpath, fn)
                layer_reprs = read_layer_representations(input_file)
                model_name = input_file.rsplit('/', 1)[0].rsplit('/', 1)[1]
                raw_results_file = \
                    os.path.join(os.path.dirname(__file__), '../outputs/{}/results/Edge/Spotlight/{}/{}/out.txt'.format(
                        results_root_dir, metric, model_name))
                results = read_results(raw_results_file)
                best_edp = pick_best(results, "edp")
                best_energy = pick_best(results, "energy")
                best_latency = pick_best(results, "delay")  # latency == delay
                
                outputs = {
                    "best_edp.yaml": build_yaml(best_edp, layer_reprs),
                    "best_energy.yaml": build_yaml(best_energy, layer_reprs),
                    "best_latency.yaml": build_yaml(best_latency, layer_reprs),
                }
                out_path = out_path_template + '{}/{}/'.format(metric, model_name)
                os.makedirs(out_path, exist_ok= True)
                for fname, data in outputs.items():
                    out_file_path = os.path.join(out_path, fname)
                    with open(out_file_path, "w") as f:
                        yaml.dump(data, f, sort_keys=False)
                    print(f"Wrote {out_file_path}")


if __name__ == "__main__":
    main()
