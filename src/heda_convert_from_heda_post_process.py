import ast
import os

def convert_line(line):
    # Safely evaluate the string as a Python tuple
    # Input: ('NAME', {params}, {strides}, 'TYPE')
    data = ast.literal_eval(line.strip())
    
    name = data[0]
    params = data[1]
    strides = data[2]
    
    # Construct the new dictionary
    # We combine the original params and add the 'Stride' key
    output_dict = params.copy()
    if strides['X'] > 1 or strides['Y'] > 1:
        output_dict['Stride'] = {'X': strides['X'], 'Y': strides['Y']}
    
    # Format as a string: 'NAME': {dict}
    return name, f"'{name}': {output_dict}"

def process_file(input_path, output_path, out_path_ids):
    try:
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile, open(out_path_ids, 'w') as outfile_ids:
            outfile_ids.write('MODELS=(\n')
            for line in infile:
                if line.strip():  # Skip empty lines
                    name, converted = convert_line(line)
                    outfile.write(converted + ',\n')
                    outfile_ids.write('  ' + name + '\n')
            outfile_ids.write(')\n')
        print(f"Successfully converted data to {output_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Usage
def main():
    in_path = os.path.join(os.path.dirname(__file__), '../inputs/unique_layers/shapes_verify.out')
    out_path_full = os.path.join(os.path.dirname(__file__), '../inputs/unique_layers/final_shapes.out')
    out_path_ids = os.path.join(os.path.dirname(__file__), '../inputs/unique_layers/layer_ids.out')
    process_file(in_path, out_path_full, out_path_ids)

if __name__ == "__main__":
    main()