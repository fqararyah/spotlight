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
    "dram_accesses",
    "l2_reads",
    "l2_writes",
    "l1_reads",
    "l1_writes",
    "l1_buf_size",
    "l2_buf_size"
]

def read_layer_representations(layer_file):
    layers = []
    with open(layer_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                layers.append(line)
    return layers


OPT_LAYER_RE = re.compile(r"^(\d+)\s+opt_layer\b")
INLINE_METRIC_RE = re.compile(
    r"\b("
    r"edp|energy|delay|latency|throughput|area|power|"
    r"dram_accesses|l2_reads|l2_writes|l1_reads|l1_writes|"
    r"l1_buf_size|l2_buf_size"
    r")\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\b"
)
COMPLETE_RECORD_RE = re.compile(
    r"^(.*?\bpower\s+[0-9eE.+-]+)"
)

INLINE_METRIC_RE2 = re.compile(
    r"'(l1_buf_size|l2_buf_size)'\s*:\s*"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)

HW_SAMPLE_RE = re.compile(r"^\d+\s+hw_sample\b")

HW_DICT_RE = re.compile(r"\{[^}]*\}")  # grabs {...}

HW_KV_RE = re.compile(
    r"'([a-zA-Z0-9_]+)'\s*:\s*"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|\[[^\]]*\])"
)

HW_BUF_RE = re.compile(
    r"'(l1_buf_size|l2_buf_size)'\s*:\s*"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)


def read_results(results_file):
    results = defaultdict(list)
    pending_layers = []

    with open(results_file, "r") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            m = OPT_LAYER_RE.match(line)
            if m:
                layer_idx = int(m.group(1))
                record = {"layer_id": layer_idx}

                for key, val in INLINE_METRIC_RE.findall(line):
                    record[key] = val

                for key, val in INLINE_METRIC_RE2.findall(line):
                    record[key] = val

                pending_layers.append(record)
                continue

            if HW_SAMPLE_RE.match(line):
                hw = {}

                # extract only what you care about
                for k, v in HW_BUF_RE.findall(line):
                    hw[k] = v

                # attach HW to pending layers
                for rec in pending_layers:
                    for k, v in hw.items():
                        rec[k] = v    # keep original names
                    results[rec["layer_id"]].append(rec)

                pending_layers.clear()

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
    results_root_dir = 'results'
    for metric in metrics:
        for dirpath, _, files in os.walk(shapes_path):
            for fn in files:
                if 'shapes.out' not in fn:
                    continue         
                input_file = os.path.join(dirpath, fn)
                layer_reprs = read_layer_representations(input_file)
                model_name = input_file.rsplit('/', 1)[0].rsplit('/', 1)[1]
                raw_results_file = \
                    os.path.join(os.path.dirname(__file__), '../outputs/{}/Edge/Spotlight/{}/{}/out.txt'.format(
                        results_root_dir, metric, model_name))
                if not os.path.exists(raw_results_file):
                    print(raw_results_file, 'DNE!!!!!')
                    continue
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
