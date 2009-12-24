#!/usr/bin/env python
# $URL$
# $Id$
# 
# run.py -- run steps of the GISTEMP algorithm
#
# Gareth Rees, 2009-12-08

"""run.py [options] -- run steps of the GISTEMP algorithm.
Options:
   --help         Print this text.
   --steps=STEPS  Specify which steps to run, as a comma-separated list of
                  numbers from 0 to 5.  For example, --steps=2,3,5
                  The steps are run in the order you specify.
                  If this option is omitted, run all steps in order.
"""

# http://www.python.org/doc/2.4.4/lib/module-getopt.html
import getopt
# http://www.python.org/doc/2.4.4/lib/module-os.html
import os
# http://www.python.org/doc/2.4.4/lib/module-sys.html
import sys

class Fatal(Exception):
    def __init__(self, msg):
        self.msg = msg

# Record the original standard output so we can log to it; in steps 2 and 5
# we'll be changing the value of sys.stdout before calling other modules that
# use "print" to generate their output.
logfile = sys.stdout

def log(msg):
    print >>logfile, msg

def mkdir(path):
    """mkdir(PATH): create the directory PATH, and all intermediate-level
    directories needed to contain it, unless it already exists."""
    if not os.path.isdir(path):
        log("... creating directory %s" % path)
        os.makedirs(path)

def run_step0():
    log("====> STEP 0 ====")
    import step0
    step0.main()
    log("... sorting the output of step 0")
    f = open(os.path.join('work', 'v2.mean_comb.unsorted'), 'r')
    v2_mean_data = f.readlines()
    f.close()
    v2_mean_data.sort()
    f = open(os.path.join('work', 'v2.mean_comb'), 'w')
    f.writelines(v2_mean_data)
    f.close()

def run_step1():
    log("====> STEP 1 ====")
    import step1
    step1.main()

def run_step2():
    log("====> STEP 2 ====")

    # Save standard output so we can restore it when we're done with this step.
    old_stdout = sys.stdout

    log("... converting text to binary file")
    year = open(os.path.join('work', 'GHCN.last_year'), 'r').read().strip()
    log("... last year = %s" % year)
    import text_to_binary
    text_to_binary.main([year])

    log("... breaking up Ts.bin into 6 zonal files")
    import split_binary
    split_binary.main([])

    log("... trimming Ts.bin1-6")
    import trim_binary
    trim_binary.main([])

    log("... Making station list")
    import invnt
    sys.stdout = open(os.path.join('log', 'Ts.GHCN.CL.station.list'), 'w')
    invnt.main([os.path.join('work', 'Ts.GHCN.CL')])
    sys.stdout.close()

    log("... Creating annual anomalies")
    import toANNanom
    toANNanom.main([])
    import PApars
    sys.stdout = open(os.path.join('log', 'PApars.GHCN.CL.1000.20.log'), 'w')
    PApars.main(['1000', '20'])
    import flags
    flags.main([])
    sys.stdout.close()

    log("... Applying peri-urban adjustment")
    import padjust
    sys.stdout = open(os.path.join('log', 'padjust.log'), 'w')
    padjust.main([])
    sys.stdout.close()

    log("... Making station list")
    sys.stdout = open(os.path.join('log', 'Ts.GHCN.CL.PA.station.list'), 'w')
    invnt.main([os.path.join('work', 'Ts.GHCN.CL.PA')])
    sys.stdout.close()

    # Restore standard output.
    sys.stdout = old_stdout

def run_step3():
    log("====> STEP 3 ====")
    import step3
    step3.main()

def run_step4():
    log("====> skipping STEP 4; see code/STEP4_5/do_comb_step4.sh ====")

def run_step5():
    log("====> STEP 5 ====")
    # Save standard output so we can restore it when we're done with this step.
    old_stdout = sys.stdout

    import step5
    step5.main([])

    log("... running vischeck")
    import vischeck
    sys.stdout = open(os.path.join('result', 'google-chart.url'), 'w')
    vischeck.main(['', os.path.join('result', 'GLB.Ts.ho2.GHCN.CL.PA.txt')])
    sys.stdout.close()

    log("See result/google-chart.url")

    # Restore standard output.
    sys.stdout = old_stdout

def main(argv = None):
    if argv is None:
        argv = sys.argv
    try:
        # By default, run all steps.
        steps = '0,1,2,3,4,5'
        
        # Parse command-line arguments.
        try:
            opts, args = getopt.getopt(argv[1:], 'hs:',
                                       ['help', 'step=', 'steps='])
            for o, a in opts:
                if o in ('-h', '--help'):
                    print __doc__
                    return 0
                elif o in ('-s', '--step', '--steps'):
                    steps = a
                else:
                    raise Fatal("Unsupported option: %s" % o)
        except getopt.error, msg:
            raise Fatal(str(msg))

        try:
            step_list = map(int, steps.split(','))
        except ValueError:
            raise Fatal("--steps must be a comma-separated list of numbers, "
                        "not '%s'." % steps)

        if 5 in step_list and not os.environ.get('FC'):
            raise Fatal("Set the environment variable FC to the FORTRAN 90 "
                        "compiler command,\ne.g. FC=gfortran42")

        rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.getcwd() != rootdir:
            raise Fatal("The GISTEMP procedure must be run from the root "
                        "directory of the project.\nPlease change directory "
                        "to %s and try again." % rootdir)

        # Carry out preflight checks and fetch missing files.
        import preflight
        preflight.checkit(sys.stderr)

        # Create all the temporary directories we're going to use.
        for d in ['bin', 'log', 'result', 'work']:
            mkdir(d)

        step_fn = {
            0: run_step0,
            1: run_step1,
            2: run_step2,
            3: run_step3,
            4: run_step4,
            5: run_step5,
        }
        for s in step_list:
            if not step_fn.has_key(s):
                raise Fatal("Can't run step %d" % s)
            step_fn[s]()

        return 0
    except Fatal, err:
        sys.stderr.write(err.msg)
        sys.stderr.write('\n')
        return 2

if __name__ == '__main__':
    sys.exit(main())
