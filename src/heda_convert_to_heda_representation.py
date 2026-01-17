#!/usr/bin/env python3

import ast
import os
import sys

# ----------------------------
# Dimension mappings
# ----------------------------
CONV_MAP = [
    ("C", "C"),
    ("R", "FH"),
    ("S", "FW"),
    ("X", "IH"),
    ("Y", "IW"),
    ("K", "NF"),
]

MATMUL_MAP = [
    ("K", "IR"),
    ("X", "WR"),
    ("Y", "C"),
    #("R", "C"),
]

FF_MAP = [
    ("N", "IR"),
    ("K", "WR"),
    ("S", "C"),
    #("X", "C"),
]

STRIDE_MAP = [
    ("X", "IW_REDUCTION"),
    ("Y", "IH_REDUCTION"),
    ("K", "NF_REDUCTION"),
]


def convert_line(line):
    """
    Convert one input line into the desired string.
    """
    # Safely parse the tuple
    name, dims, strides, op_type = ast.literal_eval(line.strip())
    parts = []

    # Main dimensions
    strides_map = []
    if 'conv' in name.lower():
        target_map = CONV_MAP
        strides_map = STRIDE_MAP
    elif 'matmul' in name.lower():
        target_map = MATMUL_MAP
    elif 'ff' in name.lower():
        target_map = FF_MAP
    else:
        return None
        
    for src, dst in target_map:
        if src in dims:
            parts.append(f"{dst}_{dims[src]}")

    # Strides / reductions
    for src, dst in strides_map:
        if src in strides:
            parts.append(f"{dst}_{strides[src]}")

    return "_".join(parts)

def main():
    path = os.path.join(os.path.dirname(__file__), '../outputs/unique_shapes/')
    for dirpath, _, files in os.walk(path):
        for fn in files:
            if 'shapes' not in fn or '.txt' not in fn:
                continue         
            input_file = os.path.join(dirpath, fn)
            output_file = os.path.join(
                dirpath, "heda_shapes.out"
            )

            with open(input_file, "r") as fin, open(output_file, "w") as fout:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue
                    converted = convert_line(line)
                    if converted is None:
                        continue
                    fout.write(converted + "\n")

            print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
