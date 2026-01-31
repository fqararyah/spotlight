#!/usr/bin/env python3

import os
import glob
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
    "l2_buf_size",
    "subclusters"
]

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def read_results(results_file):
    # This should match your single model parser
    results = defaultdict(list)
    pending_layers = []

    OPT_LAYER_RE = re.compile(r"^(\d+)\s+opt_layer\b")
    INLINE_METRIC_RE = re.compile(
        r"\b("
        r"edp|energy|delay|latency|throughput|area|power|"
        r"dram_reads|dram_writes|l2_reads|l2_writes|l1_reads|l1_writes|"
        r"l1_buf_size|l2_buf_size|subclusters"
        r")\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\b"
    )
    INLINE_METRIC_RE2 = re.compile(
        r"'(l1_buf_size|l2_buf_size|subclusters)'\s*:\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    )
    HW_SAMPLE_RE = re.compile(r"^\d+\s+hw_sample\b")
    HW_BUF_RE = re.compile(
        r"'(l1_buf_size|l2_buf_size|subclusters|num_simd_lane)'\s*:\s*"
        r"("
        r"\[[^\]]*\]"  # list, e.g. [26,6]
        r"|"
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"  # number
        r")"
    )

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
                for k, v in HW_BUF_RE.findall(line):
                    if k == "subclusters":
                        hw[k] = [int(x) for x in v.strip("[]").split(",")]
                    else:
                        hw[k] = int(v)
                for rec in pending_layers:
                    for k, v in hw.items():
                        rec[k] = v
                    results[rec["layer_id"]].append(rec)
                pending_layers.clear()
    return results

def pick_best(records, metric):
    best = {}
    for layer_idx, recs in records.items():
        valid = [r for r in recs if metric in r]
        if not valid:
            continue
        # Use float for comparison
        best[layer_idx] = min(valid, key=lambda r: float(r[metric]))
    return best

def build_yaml(best_records, layer_reprs):
    out = {}
    for idx, record in best_records.items():
        layer_name = layer_reprs[idx]
        out[layer_name] = record
    return out

def build_yaml_all(best_records_list, layer_reprs):
    """
    For each layer, collect a list of best records (one per file).
    """
    out = {}
    for idx in range(len(layer_reprs)):
        layer_name = layer_reprs[idx]
        out[layer_name] = []
        for best_records in best_records_list:
            if idx in best_records:
                out[layer_name].append(best_records[idx])
    return out

import numpy as np

def build_yaml_all(best_records_list, layer_reprs):
    """
    For each layer, collect a list of best records (one per file).
    """
    out = {}
    for idx in range(len(layer_reprs)):
        layer_name = layer_reprs[idx]
        out[layer_name] = []
        for best_records in best_records_list:
            if idx in best_records:
                out[layer_name].append(best_records[idx])
    return out

def build_yaml_avg(best_records_list, layer_reprs, metric):
    """
    For each layer, compute the average of the best metric across all files.
    """
    out = {}
    for idx in range(len(layer_reprs)):
        layer_name = layer_reprs[idx]
        vals = []
        for best_records in best_records_list:
            if idx in best_records and metric in best_records[idx]:
                try:
                    vals.append(float(best_records[idx][metric]))
                except Exception:
                    pass
        if vals:
            avg_val = int(float(np.mean(vals)))
            # Use the first record as a template, but replace the metric with the average
            avg_record = dict(best_records_list[0][idx]) if idx in best_records_list[0] else {}
            avg_record[metric] = avg_val
            out[layer_name] = avg_record
    return out

def build_yaml_median(best_records_list, layer_reprs, metric):
    """
    For each layer, select the record with the median value of the targeted metric.
    """
    out = {}
    for idx in range(len(layer_reprs)):
        layer_name = layer_reprs[idx]
        records = []
        for best_records in best_records_list:
            if idx in best_records and metric in best_records[idx]:
                try:
                    records.append(best_records[idx])
                except Exception:
                    pass
        if records:
            # Sort records by the metric value
            records_sorted = sorted(records, key=lambda r: float(r[metric]))
            median_idx = len(records_sorted) // 2
            # If even number, pick the lower median
            median_record = records_sorted[median_idx]
            out[layer_name] = median_record
    return out


def main():
    # Read model names
    script_path = os.path.dirname(__file__)
    LAYER_IDS_PATH = os.path.join(script_path, "../inputs/unique_layers/layer_ids.out")
    UNIQUE_LAYERS_DIR = os.path.join(script_path, '../inputs/unique_layers/heda_shapes.out')
    with open(LAYER_IDS_PATH) as f:
        model_names = [line.strip() for line in f if line.strip()]

    shapes_root = os.path.join(script_path, '../outputs/unique_shapes/')
    out_path_template = os.path.join(script_path, '../outputs/layers_perf_records/')
    results_root_dir = 'outputs/'

    for model_name in model_names:
        # Find all out.txt files for this model
        raw_results_files = glob.glob(f"{results_root_dir}**/*{model_name}*/out.txt", recursive=True)
        if not raw_results_files:
            print(f"No out.txt found for model {model_name}")
            continue

        layer_reprs = []
        with open(UNIQUE_LAYERS_DIR, 'r') as f:
            for line in f:
                layer_reprs.append(line.replace(' ', '').replace('\n', ''))

        # For each out.txt, get best records for each metric
        for metric in ["edp", "energy", "delay"]:
            best_records_list = []
            for out_txt in raw_results_files:
                results = read_results(out_txt)
                best = pick_best(results, metric)
                best_records_list.append(best)

            # YAML with all best records per file
            yaml_data_all = build_yaml_all(best_records_list, layer_reprs)
            out_path = os.path.join(out_path_template, f"{metric.upper()}/{model_name}")
            os.makedirs(out_path, exist_ok=True)
            out_file_path_all = os.path.join(out_path, f"best_{metric}_all.yaml")
            with open(out_file_path_all, "w") as f:
                yaml.dump(yaml_data_all, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_all}")

            # YAML with average of best values
            yaml_data_avg = build_yaml_avg(best_records_list, layer_reprs, metric)
            out_file_path_avg = os.path.join(out_path, f"best_{metric}_avg.yaml")
            with open(out_file_path_avg, "w") as f:
                yaml.dump(yaml_data_avg, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_avg}")

            yaml_data_median = build_yaml_median(best_records_list, layer_reprs, metric)
            out_file_path_median = os.path.join(out_path, f"best_{metric}_median.yaml")
            with open(out_file_path_median, "w") as f:
                yaml.dump(yaml_data_median, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_median}")

if __name__ == "__main__":
    main()