


import argparse
from multiprocessing.dummy import freeze_support

from gpuops.cmd.start import setup_start_cmd


def main():
    parser = argparse.ArgumentParser(
        description="GPUOps",
        conflict_handler="resolve",
        add_help=True,
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=55, indent_increment=2, width=200
        )
    )
    subparsers = parser.add_subparsers(
        help="sub-command help",
        metavar='{start}'
    )
    
    setup_start_cmd(subparsers)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        if isinstance(args.func, type):
            args.func(args).run()
        else:
            args.func(args)
    else:
        parser.print_help()
        
if __name__ == "__main__":
    # When using multiprocessing with 'spawn' mode, freeze_support() must be called in the main module
    # to ensure the main process environment is correctly initialized when child processes are spawned.
    # See: https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods
    freeze_support()
    main()