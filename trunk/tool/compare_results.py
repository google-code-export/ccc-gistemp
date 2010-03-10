#!/usr/bin/env python
# $URL$
# $Id$
# 
# compare_results.py -- compare results from two runs of the GISTEMP algorithm
#
# Gareth Rees, 2009-12-17

"""compare_results.py [options] RESULTA RESULTB

Compare results from two runs of the GISTEMP algorithm.  Specify two
directories RESULTA and RESULTB on the command line: each should be a
directory containing the results of a run of the GISTEMP algorithm.  A
comparison of the two sets of results is output to the file index.html
in the current directory.

Options:
   --help          Print this text.
   --output=FILE   Write the output to this file (default: index.html).
   --labela=LABEL  Label for RESULTA (default: CCC).
   --labelb=LABEL  Label for RESULTB (default: GISTEMP).
"""

import datetime
# http://www.python.org/doc/2.4.4/lib/module-getopt.html
import getopt
# http://www.python.org/doc/2.4.4/lib/module-math.html
import math
# http://www.python.org/doc/2.4.4/lib/module-os.html
import os
# http://www.python.org/doc/2.4.4/lib/module-re.html
import re
# http://www.python.org/doc/2.4.4/lib/module-struct.html
import struct
# http://www.python.org/doc/2.4.4/lib/module-sys.html
import sys
# http://www.python.org/doc/2.4.4/lib/module-xml.sax.saxutils.html
import xml.sax.saxutils
# Clear Climate Code
sys.path.append(os.path.join(os.getcwd(),'code'))
import fort
import vischeck

class Fatal(Exception):
    def __init__(self, msg):
        self.msg = msg

def asann_values_only(f):
    """Wrapper for `vischeck.asann` which yields only values.

    Any tuple that contains ``None`` is simply discarded.

    :Param f:
        Input file as required by `vischeck.asann`.

    """
    for el in vischeck.asann(f):
        if None not in el:
            yield el

def box_series(f):
    """Convert the Fortran data file *f* into a sequence of monthly
    anomalies for the geographical boxes. The file must be a BX.* file
    generated by GISTEMP step 5. The return value is an iterable over a
    sequence of pairs ((box, year, month), datum) with month running
    from 0 to 11; when present the datum is an integer, when not present
    it appears as None. Normally the data can be interpreted as
    centi-Kelvin."""
    bos = '>'                   # Byte order and size (for struct.{un,}pack).
    f = fort.File(f, bos)

    # The first record of the file is a header (see step5.SBBXtoBX).
    l = f.readline()
    info = struct.unpack('%s8i' % bos, l[:8 * 4])
    nmonths = info[3]           # Number of months in data series.
    nfields = info[4]           # Number of fields in each record.
    year = info[5]              # First year in the series.
    missing = info[6]           # Value for a missing datum.
    assert nfields == nmonths * 2 + 5

    # Each successive record contains a temperature anomaly series for
    # one box: first, 'nmonths' fields giving the anomalies for each
    # month; then 'nmonths' fields giving the weights for that box for
    # each month, then the number of good months in the series (?), then
    # four values describing the box (see eqarea.grid).
    box = 0
    while 1:
        l = f.readline()
        if l is None:
            return
        assert len(l) == nfields * 4
        data = struct.unpack('%s%df' % (bos, nmonths), l[:4 * nmonths])
        for i in xrange(nmonths):
            if data[i] != missing:
                yield(((box, year + i / 12, i % 12), data[i]))
        box += 1

# This is derived from the similar function vischeck.asann.
def asmon(f, values_only=False):
    """Convert the text file *f* into a sequence of monthly anomalies.
    An input file is expected to be one of the NH.*, SH.*, or GLB.*
    files that are the results of GISTEMP step 5.  The return value is
    an iterable over a sequence of pairs ((year, month), datum) with
    month running from 0 to 11; when present the datum is an integer,
    when not present it appears as None.  Normally the data can be
    interpreted as centi-Kelvin.
    """

    # Proceed by assuming that a line contains data if and only if it
    # starts with a 4-digit year; other lines are assumed to be
    # header/footer or decorative documentation.
    # This allows this function to work with both the direct output of
    # step 5, and also with the GISS published table data (which
    # includes more decorative documentation).
    for l in f:
        if re.match(r'\d{4}', l):
            year = int(l[:4])
            for month in range(12):
                try:
                    yield(((year, month), int(l[(month + 1) * 5:(month + 2) * 5])))
                except ValueError:
                    if not values_only:
                        yield(((year, month), None))

def stats(seq):
    """Return the zero count, length, mean, and standard deviation of
    the numbers in the non-empty sequence *seq*."""
    assert seq
    n = float(len(seq))
    mean = sum(seq) / n
    variance = sum(map(lambda x: (x - mean) ** 2, seq)) / n
    return seq.count(0), n, mean, math.sqrt(variance)

def difference(seqs, scale):
    """Return a sequence of differences between the second (data) items
    of the pairs in the two sequences *seqs*, multiplied by *scale*."""
    assert len(seqs) == 2
    seqs = map(iter, seqs)
    newa = True
    newb = True
    while 1:
        if newa:
            try:
                a = seqs[0].next()
            except StopIteration:
                a = None
            newa = False
        if newb:
            try:
                b = seqs[1].next()
            except StopIteration:
                b = None
            newb = False
        if a is None and b is None:
            return
        elif a is not None and (b is None or a[0] < b[0]):
            #print >>sys.stderr, "Missing datum for %s" % str(a[0])
            yield((a[0], 0))
            newa = True
        elif b is not None and (a is None or b[0] < a[0]):
            #print >>sys.stderr, "Missing datum for %s" % str(b[0])
            yield((b[0], 0))
            newb = True
        else:
            assert a[0] == b[0]
            yield((a[0], (a[1] - b[1]) * scale))
            newa = True
            newb = True

def distribution_url(d):
    """Return the URL of a Google chart showing the distribution of the
    values in the sequence *d*, collected into bins."""

    d_range = max(d) - min(d)
    w = 0.01

    # Reduce the number of bins by increasing the bin width, so that the
    # chart can be drawn even if the range is very large.
    while 100*w < d_range:
        w *= 10

    # Increase the number of bins by decreasing the bin width, so that the
    # chart still looks interesting even if the range is tiny.
    while len(d) > 0 and d_range > 0 and 10*w > d_range:
        w /= 10

    # Now we have between 10 and 100 bins.  100 bins is too many.
    if d_range > 25*w:
        w *= 5

    # Now either 10w < d_range < 25w, and w = 10^k,
    # Or 5w < d_range < 20w, and w = 5*10^k
    # Or d_range = 0 and w = 0.01.

    # Map from integer multiple of w to number of values in that bin.
    bins = {}
    for v in d:
        b = int(math.floor(0.5 + v / w))
        bins[b] = bins.get(b, 0) + 1
    bin_min = min(bins.keys())
    bin_max = max(bins.keys())

    # Number of values in each bin.
    d = map(lambda x: bins.get(x, 0), range(bin_min, bin_max + 1))
    dmax = max(d)

    # Google chart documentation at http://code.google.com/apis/chart/
    rx = '|'.join(map(lambda x: '%d' % x, range(bin_min, bin_max + 1)))
    bin_count = bin_max - bin_min + 1
    notex = '|'*(bin_count/2) + '(bin size %g)' % w
    ry = '0,%d,%d' % (dmax, 10 ** math.floor(math.log10(dmax)))
    chart = [
        'chs=600x300', # Chart size (pixels).
        'cht=bvg',     # Chart type: Horizontal bar chart, stacked bars.
        'chbh=a',        # Automatically resize bars to fit.
        'chd=t:' + ','.join(map(str, d)),     # Data.
        'chds=0,%d' % dmax,                   # Data scaling. 
        'chxt=x,y,r,x',                       # Axes to label.
        'chxl=0:|%s|3:|%s' % (rx, notex),     # Text labels on x axis
        'chxr=1,%s|2,%s' % (ry, ry),          # Axis ranges.
        'chm=N,000000,0,-1,11'                # Data labels
        ]

    return 'http://chart.apis.google.com/chart?' + '&'.join(chart)

def differences_url(anns):
    """Return the URL of a Google chart showing the difference between
    the two sequences of annual anomalies in the sequence *anns*."""
    assert len(anns) == 2

    # Take difference.
    d = map(lambda a: a[1], list(difference(anns, 0.01)))

    # List of years
    years = map(lambda a: a[0], anns[0])
    assert years == map(lambda a: a[0], anns[1])

    # Google chart documentation at http://code.google.com/apis/chart/
    dmin = min(d)
    dmax = max(d)
    ry = '%.2f,%.2f,.01' % (dmin, dmax)
    rx = '%d,%d,10' % (min(years), max(years))
    chart = [
        'chs=600x200',   # Chart size (pixels).
        'cht=bvg',       # Chart type: Horizontal bar chart, stacked bars.
        'chbh=a',        # Automatically resize bars to fit.
        'chd=t:%s' % ','.join(map(str, d)),   # Data values.
        'chds=%.2f,%.2f' % (dmin, dmax),      # Data scaling. 
        'chxt=x,y,r',                         # Axes to label.
        'chxr=0,%s|1,%s|2,%s' % (rx, ry, ry), # Axes ranges.
        ]

    return 'http://chart.apis.google.com/chart?' + '&'.join(chart)

def top(diffs, n, o, title, fmt = str):
    """Output a list of the top at-most-*n* largest differences (in
    magnitude) from the list *diffs* to the stream *o*, using *fmt* to
    format the results.  Does not output any zeroes."""
    topn = sorted(diffs, key = lambda a: abs(a[1]), reverse = True)[:n]
    if topn[0][1] != 0:
        print >>o, '<h3>%s</h3>' % title
    print >>o, "<ol>"
    for k, v in topn:
        if v == 0:
            break
        print >>o, "<li>" + fmt(k, v)
    print >>o, "</ol>"

def compare(dirs, labels, o):
    """Compare results from the two directories in the sequence *dirs*,
    which are labelled by the two strings in the sequence *labels*. Write a
    comparison document in HTML to the stream *o*."""
    assert len(dirs) == 2
    assert len(labels) == 2

    # XML-encode meta-characters &,<,>
    escape = xml.sax.saxutils.escape
    labels = map(escape, labels)

    # Version of ``asmon`` that avoids yielding ``None``.
    asmon_values_only = lambda f: asmon(f, values_only=True)

    title = "Comparison of %s and %s" % tuple(dirs)
    print >>o, """<!doctype HTML>
<html>
<head>
<title>%s</title>
</head>
<body>
<h1>%s</h1>
<p>Generated: %s</p>
""" % (title, title, datetime.datetime.now())

    anomaly_file = '%s.Ts.ho2.GHCN.CL.PA.txt'
    box_file = 'BX.Ts.ho2.GHCN.CL.PA.1200'
    for region, code in [
        ('global',              'GLB'), 
        ('northern hemisphere', 'NH'),
        ('southern hemisphere', 'SH'),
    ]:
        # Annual series
        fs = map(lambda d: open(os.path.join(d, anomaly_file % code), 'r'), dirs)
        anns = map(list, map(asann_values_only, fs))
        url = vischeck.asgooglechartURL(anns)
        print >>o, '<h2>%s annual temperature anomaly</h2>' % region.capitalize()
        print >>o, '<p>%s in red, %s in black.</p>' % tuple(labels) 
        print >>o, '<img src="%s">' % escape(url)
        print >>o, ('<h3>%s annual residues (%s - %s)</h3>'
                    % (region.capitalize(), labels[0], labels[1]))
        print >>o, '<img src="%s">' % escape(differences_url(anns))

        diffs = list(difference(anns, 0.01))
        d = map(lambda a: a[1], diffs)
        print >>o, '<h3>%s annual residue distribution</h3>' % region.capitalize()
        print >>o, '<img src="%s">' % escape(distribution_url(d))
        print >>o, '<h3>%s annual residue summary</h3>' % region.capitalize()
        print >>o, '<ul>'
        print >>o, '<li>Min = %g<li>Max = %g' % (min(d), max(d))
        print >>o, '<li>Zeroes: %d/%d<li>Mean = %g<li>Standard deviation = %g' % stats(d)
        print >>o, '</ul>'
        top(diffs, 10, o, 'Largest %s annual residues' % region,
            lambda k, v: "%04d: %g" % (k, v))

        # Monthly series
        fs = map(lambda d: open(os.path.join(d, anomaly_file % code), 'r'), dirs)
        mons = map(asmon_values_only, fs)
        diffs = list(difference(mons, 0.01))
        d = map(lambda a: a[1], diffs)
        print >>o, '<h3>%s monthly residue distribution</h3>' % region.capitalize()
        print >>o, '<img src="%s">' % escape(distribution_url(d))
        print >>o, '<h3>%s monthly residue summary</h3>' % region.capitalize()
        print >>o, '<ul>'
        print >>o, '<li>Min = %g<li>Max = %g' % (min(d), max(d))
        print >>o, '<li>Zeroes: %d/%d<li>Mean = %g<li>Standard deviation = %g' % stats(d)
        print >>o, '</ul>'
        top(diffs, 10, o, 'Largest %s monthly residues' % region,
            lambda k, v: "%04d-%02d: %g" % (k[0], k[1] + 1, v))

    # Box series
    fs = map(lambda d: open(os.path.join(d, box_file), 'r'), dirs)
    boxes = map(list, map(box_series, fs))
    diffs = list(difference(boxes, 0.01))
    box_table = {}
    for d in diffs:
        box = d[0][0]
        box_table[box] = box_table.get(box,[])
        box_table[box].append(d[1])
    box_std_devs = []
    max_std_dev = 0.0
    for (box, box_diffs) in box_table.items():
        box_table[box] = stats(box_diffs)
        std_dev = box_table[box][3]
        max_std_dev = max(max_std_dev, std_dev)
        box_std_devs.append((box, std_dev))
    
    d = map(lambda a: a[1], diffs)
    print >>o, '<h3>Per-box monthly residue distribution</h3>'
    print >>o, '<img src="%s">' % escape(distribution_url(d))
    print >>o, '<h3>Per-box monthly residue summary</h3>'
    print >>o, '<ul>'
    print >>o, '<li>Min = %g<li>Max = %g' % (min(d), max(d))
    print >>o, '<li>Zeroes: %d/%d<li>Mean = %g<li>Standard deviation = %g' % stats(d)
    print >>o, '</ul>'
    top(diffs, 10, o,'Largest per-box monthly residues',
        lambda k, v: "Box %02d, %04d-%02d: %g" % (k[0], k[1], k[2] + 1, v))

    top(box_std_devs, 10, o,'Largest per-box standard deviations',
        lambda k, v: "Box %02d: %g" % (k, v))

    print >>o, '<h3>Geographic distribution of per-box monthly residue statistics</h3>'
    print >>o, '<table border=1 style="border-collapse:collapse; border-width:1px; border-color:#cccccc; border-style:solid; font-size:small">'
    box = 0
    for band in range(8):
        print >>o, '<tr>'
        boxes_in_band = 18 - 2 * (abs(7 - 2*band)) # silly hack to get 4,8,12,16,16,12,8,4
        box_span = 48 / boxes_in_band
        for i in range(boxes_in_band):
            std_dev = box_table[box][3]
            if std_dev == 0 or max_std_dev == 0:
                gb_level = 0xff
            else:
                gb_level = 0xff - int(0x80 * std_dev / max_std_dev)
            color = "#ff%02x%02x" % (gb_level, gb_level)
            print >>o, '<td align="center" colspan="%d" bgcolor = "%s">' % (box_span, color)
            print >>o, '%d%%<br/>%.2g</td>' % (100 * box_table[box][0]/box_table[box][1], box_table[box][3])
            box += 1
        print >>o, '</tr>'
    print >>o, '</table>'

    print >>o, "</body>"
    print >>o, "</html>"
    o.close()

def main(argv = None):
    if argv is None:
        argv = sys.argv
    try:
        # Parse command-line arguments.
        output = 'index.html'
        labels = ['CCC', 'GISS']
        try:
            opts, args = getopt.getopt(argv[1:], 'ho:l:m:',
                                       ['help', 'output=', 'labela=', 'labelb='])
            for o, a in opts:
                if o in ('-h', '--help'):
                    print __doc__
                    return 0
                elif o in ('-o', '--output'):
                    output = a
                elif o in ('-l', '--labela'):
                    labels[0] = a
                elif o in ('-m', '--labelb'):
                    labels[1] = a
                else:
                    raise Fatal("Unsupported option: %s" % o)
            if len(args) != 2:
                raise Fatal("Expected two result directories, but got '%s'"
                            % ' '.join(args))
        except getopt.error, msg:
            raise Fatal(str(msg))

        # Do the comparison.
        compare(args, labels, open(output, 'w'))
        return 0
    except Fatal, err:
        sys.stderr.write(err.msg)
        sys.stderr.write('\n')
        return 2

if __name__ == '__main__':
    sys.exit(main())
