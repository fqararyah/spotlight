#!/usr/bin/env python3

import os
import glob
import yaml
import re
from collections import defaultdict
import numpy as np

CONV_INPUT_DIMS = ['X', 'Y']
CONV_FILTER_DIMS = ['R', 'S', 'K']
CONV_OUT_DIMS = []

MATMUL_INPUT_DIMS = ['X']
MATMUL_FILTER_DIMS = ['K']
MATMUL_OUTPUT_DIMS = []

PARALLELISM_FIELDS = [
    "l0_filter_parallelism", "l0_input_parallelism", "l0_output_parallelism",
    "l1_filter_parallelism", "l1_input_parallelism", "l1_output_parallelism"
]

# Add num_simd_lane to the metrics tracked
ALL_METRICS = [
    "edp", "energy", "delay", "throughput", "area", "power", "dram_reads", "dram_writes", "AbsComputations",
    "FilterL2BufferRead", "InputL2BufferRead", "OutputL2BufferRead",
    "FilterL2BufferWrite", "InputL2BufferWrite", "OutputL2BufferWrite",
    "l2_writes",
    "FilterL1BufferRead", "InputL1BufferRead", "OutputL1BufferRead",
    "FilterL1BufferWrite", "InputL1BufferWrite", "OutputL1BufferWrite",
    "l1_buf_size", "l2_buf_size", "subclusters", "num_simd_lane"  # Added here
] + PARALLELISM_FIELDS

# Create a helper for hardware fields to keep code clean
HW_FIELDS = ("l1_buf_size", "l2_buf_size", "subclusters", "num_simd_lane")

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def infer_op_type(results_file):
    fname = results_file.lower()
    if "matmul" in fname:
        return "matmul"
    return "conv"

def get_parallelism(level, kind, sw_point, subclusters, op_type):
    # level: 'l0' or 'l1', kind: 'input', 'filter', 'output'
    spatial_dim_key = f"{level}_spatial_dim"
    dim = sw_point.get(spatial_dim_key)
    if not dim or not subclusters or not isinstance(subclusters, (list, tuple)) or len(subclusters) < 2:
        return 1
    idx = 0 if level == 'l0' else 1
    if kind == "input":
        valid_dims = MATMUL_INPUT_DIMS if op_type == "matmul" else CONV_INPUT_DIMS
    elif kind == "filter":
        valid_dims = MATMUL_FILTER_DIMS if op_type == "matmul" else CONV_FILTER_DIMS
    else:
        valid_dims = MATMUL_OUTPUT_DIMS if op_type == "matmul" else CONV_OUT_DIMS

    return subclusters[idx] if dim in valid_dims else 1

def extract_sw_point(line):
    # Try to extract a dict from a string like: point {'l0_input_spatial_dim':'C', ...}
    m = re.search(r"point\s+(\{.*\})", line)
    if m:
        try:
            # Replace single quotes with double quotes for safe eval
            import ast
            d = ast.literal_eval(m.group(1).replace("'", '"'))
            return d
        except Exception:
            return {}
    return {}

def read_results(results_file):
    results = defaultdict(list)
    pending_layers = []

    OPT_LAYER_RE = re.compile(r"^(\d+)\s+opt_layer\b")
    METRIC_RE = re.compile(
        r"\b("
        r"edp|energy|delay|latency|throughput|area|power|dram_reads|dram_writes|AbsComputations|"
        r"FilterL2BufferRead|InputL2BufferRead|OutputL2BufferRead|"
        r"FilterL2BufferWrite|InputL2BufferWrite|OutputL2BufferWrite|"
        r"l2_writes|"
        r"FilterL1BufferRead|InputL1BufferRead|OutputL1BufferRead|"
        r"FilterL1BufferWrite|InputL1BufferWrite|OutputL1BufferWrite"
        r")\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    )
    HW_SAMPLE_RE = re.compile(r"^\d+\s+hw_sample\b")
    # Inside read_results function:
    HW_BUF_RE = re.compile(
        r"'(l1_buf_size|l2_buf_size|subclusters|num_simd_lane)'\s*:\s*" # Added num_simd_lane
        r"("
        r"\[[^\]]*\]"  # list
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
                for key, val in METRIC_RE.findall(line):
                    record[key] = val
                # Try to extract sw_point if present
                sw_point = extract_sw_point(line)
                if sw_point:
                    record["sw_point"] = sw_point
                pending_layers.append(record)
                continue

            if HW_SAMPLE_RE.match(line):
                hw = {}
                for k, v in HW_BUF_RE.findall(line):
                    if k == "subclusters":
                        hw[k] = [int(x) for x in v.strip("[]").split(",") if x.strip()]
                    else:
                        try:
                            hw[k] = int(v)
                        except Exception:
                            hw[k] = v
                for rec in pending_layers:
                    for k, v in hw.items():
                        rec[k] = v
                    # Ensure all hardware fields are present, even if missing
                    for field in ("l1_buf_size", "l2_buf_size", "subclusters"):
                        if field not in rec:
                            rec[field] = ""
                    results[rec["layer_id"]].append(rec)
                pending_layers.clear()
    return results

def extract_record_fields(record, op_type):
    out = {}
    sw_point = record.get("sw_point", {})
    subclusters = record.get("subclusters", [1, 1])
    if isinstance(subclusters, str):
        try:
            subclusters = eval(subclusters)
        except Exception:
            subclusters = [1, 1]
    for metric in ALL_METRICS:
        if metric in PARALLELISM_FIELDS:
            # e.g., l0_input_parallelism
            parts = metric.split("_")
            level = parts[0]
            kind = parts[1]
            out[metric] = get_parallelism(level, kind, sw_point, subclusters, op_type)
        else:
            out[metric] = record.get(metric, "")
    return out

def pick_best(records, metric):
    best = {}
    for layer_idx, recs in records.items():
        valid = [r for r in recs if metric in r]
        if not valid:
            continue
        best[layer_idx] = min(valid, key=lambda r: float(r[metric]))
    return best

# Define this globally to ensure consistency across all functions
HW_FIELDS = ("l1_buf_size", "l2_buf_size", "subclusters", "num_simd_lane")

def build_yaml_all(best_records_list, layer_reprs):
    out = {}
    for idx in range(len(layer_reprs)):
        layer_name = layer_reprs[idx]
        out[layer_name] = []
        for best_records in best_records_list:
            if idx in best_records:
                out[layer_name].append(best_records[idx])
    return out

def build_yaml_avg(best_records_list, layer_reprs, metric):
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
            avg_val = float(np.mean(vals))
            # Use the first record as a template
            avg_record = dict(best_records_list[0][idx]) if idx in best_records_list[0] else {}
            avg_record[metric] = avg_val
            
            # Use HW_FIELDS to ensure num_simd_lane and others are preserved
            for hw_field in HW_FIELDS + tuple(PARALLELISM_FIELDS):
                hw_vals = [
                    best_records[idx].get(hw_field, "") 
                    for best_records in best_records_list 
                    if idx in best_records and best_records[idx].get(hw_field, "") not in ("", None, [])
                ]
                avg_record[hw_field] = hw_vals[0] if hw_vals else ""
            out[layer_name] = avg_record
    return out

def build_yaml_median(best_records_list, layer_reprs, metric):
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
            # Sort by the primary metric (e.g., EDP) to find the median record
            records_sorted = sorted(records, key=lambda r: float(r[metric]))
            median_idx = len(records_sorted) // 2
            median_record = records_sorted[median_idx]
            
            # Ensure hardware fields (including num_simd_lane) are consistent
            for hw_field in HW_FIELDS + tuple(PARALLELISM_FIELDS):
                hw_vals = [
                    r.get(hw_field, "") 
                    for r in records_sorted 
                    if r.get(hw_field, "") not in ("", None, [])
                ]
                median_record[hw_field] = hw_vals[0] if hw_vals else ""
            out[layer_name] = median_record
    return out

def main():
    # Adjust these paths as needed
    script_path = os.path.dirname(__file__)
    LAYER_IDS_PATH = os.path.join(script_path, "../inputs/unique_layers/layer_ids.out")
    UNIQUE_LAYERS_DIR = os.path.join(script_path, '../inputs/unique_layers/heda_shapes.out')
    model_names = []
    with open(LAYER_IDS_PATH) as f:
        for line in f:
            if '=' in line:
                continue
            line = line.strip().replace('(', '').replace(')', '')
            if line:
                model_names.append(line)

    out_path_template = os.path.join(script_path, '../outputs/layers_perf_records/')
    results_root_dir = 'outputs/'

    layer_reprs = []
    with open(UNIQUE_LAYERS_DIR, 'r') as f:
        for line in f:
            layer_reprs.append(line.replace(' ', '').replace('\n', ''))

    for i, model_name in enumerate(model_names):
        layer_repr = layer_reprs[i]
        raw_results_files = glob.glob(f"{results_root_dir}**/*{model_name}*/out.txt", recursive=True)
        if not raw_results_files:
            print(f"No out.txt found for model {model_name}")
            continue

        for metric in ["edp", "energy", "delay"]:
            best_records_list = []
            for out_txt in raw_results_files:
                op_type = infer_op_type(out_txt)
                results = read_results(out_txt)
                best = pick_best(results, metric)
                # Extract new fields for each best record
                best_new = {}
                for idx, rec in best.items():
                    best_new[idx] = extract_record_fields(rec, op_type)
                best_records_list.append(best_new)

            yaml_data_all = build_yaml_all(best_records_list, [layer_repr])
            out_path = os.path.join(out_path_template, f"{metric.upper()}/{model_name}")
            os.makedirs(out_path, exist_ok=True)
            out_file_path_all = os.path.join(out_path, f"best_{metric}_all.yaml")
            with open(out_file_path_all, "w") as f:
                yaml.dump(yaml_data_all, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_all}")

            yaml_data_avg = build_yaml_avg(best_records_list, [layer_repr], metric)
            out_file_path_avg = os.path.join(out_path, f"best_{metric}_avg.yaml")
            with open(out_file_path_avg, "w") as f:
                yaml.dump(yaml_data_avg, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_avg}")

            yaml_data_median = build_yaml_median(best_records_list, [layer_repr], metric)
            out_file_path_median = os.path.join(out_path, f"best_{metric}_median.yaml")
            with open(out_file_path_median, "w") as f:
                yaml.dump(yaml_data_median, f, sort_keys=False, Dumper=NoAliasDumper)
            print(f"Wrote {out_file_path_median}")

if __name__ == "__main__":
    main()