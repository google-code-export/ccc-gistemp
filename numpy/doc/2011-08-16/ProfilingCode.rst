.. Notes on how profiling code.

Profiling Code
--------------

Before trying to speed-up the code we need first to find where the bottlenecks
are.

The python cProfile [1] (formerly known as lsprof) module is recommended for the
task. The underlying module is written in C, which means a much smaller
performance hit while profiling.

To start profiling just type:
>>> python -m cProfile -o output.pstats path/to/your/script args

Visualizing Profiling Results
-----------------------------

The program kcachegrind [2] is a good cross platform profile visualization
program. Before visualizing one must convert the pstats (or pyprof) file first
to a calltree with pyprof2calltree [3].

>>> pyprof2calltree -i output.pstats -k

There is also the module Gprof2Dot [4], a python based tool that can transform
the profiling results output into a graph.

>>> gprof2dot.py -f pstats output.pstats | dot -Tpng -o output.png

[1] http://docs.python.org/library/profile.html
[2] http://kcachegrind.sourceforge.net/html/Home.html
[3] http://pypi.python.org/pypi/pyprof2calltree/
[4] http://jrfonseca.googlecode.com/svn/trunk/gprof2dot/gprof2dot.py