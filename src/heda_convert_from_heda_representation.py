#!/usr/bin/env python3

import os
import re

# ----------------------------
# Dimension mappings
# ----------------------------
CONV_MAP_INV = {
    "C": "C",
    "FH": "R",
    "FW": "S",
    "IH": "X",
    "IW": "Y",
    "NF": "K",
}

MATMUL_MAP_INV = {
    "IR": "K",
    "WR": "X",
    "C": "Y", 
}

STRIDE_MAP_INV = {
    "IH_REDUCTION": "Y",
    "IW_REDUCTION": "X",
    "NF_REDUCTION": "K",
}

def parse_string(line):
    """Parses underscore-separated string into key-value pairs."""
    parts = line.split('_')
    data = {}
    i = 0
    while i < len(parts):
        if re.search('[a-zA-Z]', parts[i]):
            key = parts[i]
            # Check for REDUCTION triplet: [KEY] [REDUCTION] [VAL]
            if i + 2 < len(parts) and parts[i+1] == "REDUCTION":
                if parts[i+2].isdigit():
                    data[f"{key}_REDUCTION"] = int(parts[i+2])
                    i += 3
                    continue
            # Check for standard pair: [KEY] [VAL]
            if i + 1 < len(parts) and parts[i+1].isdigit():
                data[key] = int(parts[i+1])
                i += 2
            else:
                i += 1
        else:
            i += 1
    return data

def convert_line(line, counter):
    """Converts a single line string into the target tuple format."""
    if not line.strip():
        return None
    
    parsed_data = parse_string(line)
    
    # Defaults
    dims = {'N': 1, 'K': 1, 'C': 1, 'R': 1, 'S': 1, 'X': 1, 'Y': 1}
    strides = {'N': 1, 'K': 1, 'C': 1, 'R': 1, 'S': 1, 'X': 1, 'Y': 1}
    
    # Logic to identify Op Type
    is_conv = any(k in parsed_data for k in ["FH", "FW", "NF", "IH", "IW"])
    
    if is_conv:
        op_name = f"CONV{counter:02d}"
        for k, v in parsed_data.items():
            if k in CONV_MAP_INV:
                dims[CONV_MAP_INV[k]] = v
            if k in STRIDE_MAP_INV:
                strides[STRIDE_MAP_INV[k]] = v
        op_type = "CONV"
    else:
        # MatMul naming and logic
        op_name = f"MatMul{counter:02d}"
        dims['K'] = parsed_data.get('IR', 1)
        dims['X'] = parsed_data.get('WR', 1)
        dims['Y'] = parsed_data.get('C', 1)
        dims['R'] = parsed_data.get('C', 1)
        op_type = "MatMul"

    return (op_name, dims, strides, op_type)

def main():
    # Adjusted path logic to match your structure
    base_path = os.path.join(os.path.dirname(__file__), '../outputs/unique_shapes/')
    
    for dirpath, _, files in os.walk(base_path):
        # --- RESTART COUNTER FOR EACH DIRECTORY ---        
        # Filter for your specific input files      
        # Open output file in write mode ('w') to refresh it for this directory
        for fn in files:
            if 'heda_shapes.out' not in fn:
                continue 
            layer_counter = 0
            input_file_path = os.path.join(dirpath, fn)
            output_file_path = os.path.join(dirpath, "shapes_verify.out")
            results_list = []
            with open(input_file_path, "r") as fin:
                for line in fin:
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                        
                    result = convert_line(clean_line, layer_counter)
                    if result:
                        results_list.append(result)
                        layer_counter += 1
            if results_list:            
                with open(output_file_path, "w") as fout:
                    for res in results_list:
                        fout.write(str(res) + '\n')
        
if __name__ == "__main__":
    main()