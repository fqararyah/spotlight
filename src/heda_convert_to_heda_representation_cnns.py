#!/usr/bin/env python3

import ast
import os
import sys

# ----------------------------
# Dimension mappings
# ----------------------------
MAIN_MAP = [
    ("C", "C"),
    ("R", "FH"),
    ("S", "FW"),
    ("X", "IH"),
    ("Y", "IW"),
    ("K", "NF"),
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
    for src, dst in MAIN_MAP:
        if src in dims:
            parts.append(f"{dst}_{dims[src]}")

    # Strides / reductions
    for src, dst in STRIDE_MAP:
        if src in strides:
            parts.append(f"{dst}_{strides[src]}")

    return "_".join(parts)

def main():
    cnns_list = ['RESNET', 'VGG16']
    path = os.path.join(os.path.dirname(__file__), '../outputs/unique_shapes/')
    for dirpath, _, files in os.walk(path):
        is_cnn = any(cnn in dirpath for cnn in cnns_list)
        for fn in files:
            if 'shapes' not in fn or '.txt' not in fn or not is_cnn:
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
                    fout.write(converted + "\n")

            print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
