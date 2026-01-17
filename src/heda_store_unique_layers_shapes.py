import search
import options
import layers
import sys
import os

def main():
    args = options.get_args()

    print(' '.join(sys.argv[1:]))

    if args.output_to_file:
        out_file = open(os.path.join(args.output_dir, args.output_filename), 'w')
    else:
        out_file = None

    shapes = layers.get_shapes(args.layers, args.ignore_stride, True, args.remove_duplicate_layers)

    if out_file:
        print(out_file)
        for shape in shapes:
            out_file.write(str(shape) + '\n')
        out_file.close()

if __name__ == '__main__':
    main()