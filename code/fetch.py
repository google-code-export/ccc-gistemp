#!/usr/bin/env python
# $URL$
# $Rev$
#
# fetch.py
#
# David Jones, Ravenbrook Limited, 2010-01-07
# Copyright (C) 2008-2010 Ravenbrook Limited.

"""
fetch.py [--help] [input-files] ...

Script to fetch (download from the internet) the inputs required for
the GISTEMP program.

Any input files passed as arguments will be fetched from their locations
on the internet.  If no arguments are supplied, nothing will be fetched.
"""

# http://www.python.org/doc/2.4.4/lib/module-getopt.html
import getopt
# http://www.python.org/doc/2.4.4/lib/module-sys.html
import sys
# http://www.python.org/doc/2.4.4/lib/module-urllib.html
import urllib

def fetch(files, prefix='input/', output=sys.stdout):
    """Download a bunch of files.  *files* is a list of the files to
    download (just the basename part, the bit after the last directory
    separator, with or without the compression suffix).  *prefix* (not
    normally changed from the default) is the location on the local
    file system where the files will be downloaded.  *output* (not
    normally changed from the default) is where progress messages
    appear.
    """

    import itertools
    import os

    # See
    # http://groups.google.com/group/ccc-gistemp-discuss/web/compiling-gistemp-source?hl=en
    # (But station_inventory.Z corrected to station.inventory.Z)

    # There appears to be an HTTP server for the NOAA data:
    # http://www1.ncdc.noaa.gov/pub/data/ghcn/v2/
    # drj can't find any documentation that says this is the right place to
    # use.  HTTP would be better because we can find out the length of
    # the file so we can show progress better (and possibly diagnose /
    # restart interrupted downloads).

    # We are moving from USHCNv1 (hcn_doe_mean_data.Z) to USHCNv2
    # (9641C_200907_F52.avg.gz).  It does no harm to remember how to
    # fetch the older file.
    noaa = """
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.mean.Z
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.temperature.inv
    ftp://ftp.ncdc.noaa.gov/pub/data/ushcn/hcn_doe_mean_data.Z
    ftp://ftp.ncdc.noaa.gov/pub/data/ushcn/v2/monthly/9641C_200907_F52.avg.gz
    ftp://ftp.ncdc.noaa.gov/pub/data/ushcn/station.inventory.Z
    """.split()

    giss = """
    ftp://data.giss.nasa.gov/pub/gistemp/SBBX.HadR2
    """.split()

    # This is all the inputs that are simple URLs
    all = noaa + giss

    # *place* is a dictionary that maps from short name to URL or some
    # other indicator of location.
    # The value can either be a string, in which case it is treated as a
    # URL, or a list of the form [handler, something else], in which
    # case *handler* will be used (as a key to find a function) to
    # handle downloads.
    place = dict((url.split('/')[-1], url) for url in all)

    # Add the things that come from tar files:
    step0inputs = """
    antarc1.list
    antarc1.txt
    antarc2.list
    antarc2.txt
    antarc3.list
    antarc3.txt
    t_hohenpeissenberg_200306.txt_as_received_July17_2003
    ushcn2.tbl
    ushcnV2_cmb.tbl
    """.split()

    step1inputs = """
    mcdw.tbl
    sumofday.tbl
    v2.inv
    """.split()

    gistemp_source_tar = \
      'http://data.giss.nasa.gov/gistemp/sources/GISTEMP_sources.tar.gz'

    for n in step0inputs:
        place[n] = ['tar', gistemp_source_tar,
          'GISTEMP_sources/STEP0/input_files/' + n]
    for n in step1inputs:
        place[n] = ['tar', gistemp_source_tar,
          'GISTEMP_sources/STEP1/input_files/' + n]

    # A "special" place is one that isn't just an ordinary URL.
    # Places are identified as being "special" when they are a list
    # whose first element is a key in this *special* dictionary.
    # Ordinary strings are assumed to be URLs and are not special.
    # But the first element of a string is a one character string, so
    # all *special* keys should be longer than 1 character.
    special = dict(tar=fetch_tar)
    def addurl(d):
        """Add 'url' handler to all plain strings."""
        for short, long in d.items():
            if long[0] in special:
                yield short, long
            else:
                # Ordinary URL.
                yield short, ['url', long]
    place = dict(addurl(place))
    # Now make the *place* dictionary have short names both with and
    # without the compression suffix.
    def removeZ(d):
        """For every short name that ends in '.Z' or '.gz' (case
        insensitive), then add a short name with the extension removed.
        So we can ask for either the compressed or uncompressed version
        (but in either case, the compressed version is fetched).
        """
        # *name* is a dictionary that maps from short name, with and
        # without compression suffix, to the URL.
        name = {}
        for short, long in d.items():
            split = short.split('.')
            if split[-1].lower() in ['z','gz']:
                yield '.'.join(split[:-1]), (long, short)
            yield short, (long, short)
    place = dict(removeZ(place))
    # *place* now maps from *name* to a (*long*, *short*) pair; only for
    # compression extensions are *name* and *short* different.

    # Check that we can fetch the requested files.
    for n in files:
        if n not in place:
            raise Error("Don't know how to fetch %s" % n)

    handler = dict(special, url=fetch_url)

    # Attempt to create the directories required for *prefix*.
    try:
        os.makedirs(prefix)
    except OSError:
        # Expected if the directories already exist.
        pass

    # Convert from list of files to list of (*place*, *local*) pairs.
    # *local* is the localfilename, which will include a compression
    # extension when the asked-for name might not; *place* is a list of
    # the form ['url', URL].
    files = [place[file] for file in files]
    # sort the list so that places with the same handler get grouped
    # together.  This is so that we can do multiple extracts from a tar
    # file in one pass.
    files.sort()
    for hname,group in itertools.groupby(files, key=lambda x: x[0][0]):
        handler[hname](group, prefix, output)

def fetch_url(l, prefix, output):
    """(helper function used by :meth:`fetch`)

    *l* is a list of (*place*,*name*) pairs.  Each *name* is a short name,
    each *place* is a triple ('url',*url*,*local*).
    """

    import os

    for (handler, place), name in l:
        assert handler == 'url'
        # Make a local filename.
        local = os.path.join(prefix, name)
        output.write(name + ' ' + place + '\n')
        urllib.urlretrieve(place, local, progress_hook(output))
        output.write('\n')
        output.flush()

def fetch_tar(l, prefix, output):
    """(helper function used by :meth:`fetch`)

    *l* is a list of (*place*,*name*) pairs.  Each *name* is a short name,
    each *place* is a pair ('tar',*url*,*member*).
    """

    import itertools
    
    # Group by URL so that we process all the members from the same tar
    # file together.
    for url,group in itertools.groupby(l, key=lambda x: x[0][1]):
        u = urllib.urlopen(url)
        members = map(lambda x: x[0][2], group)
        print >>output, 'Extracting members from', url, '...'
        fetch_from_tar(u, members, prefix, output)
        print >>output, "  ... finished extracting"

def fetch_from_tar(inp, want, prefix='input', log=sys.stdout):
    """Fetch a list of files from a tar file.  *inp* is an open file
    object, *want* is the list of names that are required.  Each file
    will be stored in the directory *prefix* using just the last
    component of its name.

    Because of the way Python's tarfile module works, *inp* can be a tar
    file or a compressed tar file.
    """

    import os

    # http://www.python.org/doc/2.4.4/lib/module-tarfile.html
    import tarfile
    # The first argument, an empty string, is a dummy which works around
    # a bug in Python 2.5.1.  See
    # http://code.google.com/p/ccc-gistemp/issues/detail?id=26
    tar = tarfile.open('', mode='r|*', fileobj=inp)
    for info in tar:
        if info.name in want:
            short = info.name.split('/')[-1]
            local = os.path.join(prefix, short)
            out = open(local, 'wb')
            print >>log, "  ... %s from %s." % (short, info.name)
            out.writelines(tar.extractfile(info))

def progress_hook(out):
    """Return a progress hook function, suitable for passing to
    urllib.retrieve, that writes to the file object *out*.
    """

    def it(n, bs, ts):
        got = n*bs
        if ts < 0:
            outof = ''
        else:
            # On the last block n*bs can exceed ts, so we clamp it
            # to avoid awkward questions.
            got = min(got, ts)
            outof = '/%d [%d%%]' % (ts, 100*got//ts)
        out.write("\r  %d%s" % (got, outof))
        out.flush()
    return it

class Error(Exception):
    """Some sort of problem with fetch."""

# Guido's main, http://www.artima.com/weblogs/viewpost.jsp?thread=4829
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "", ["help"])
            for o,a in opts:
                if o in ('--help',):
                    print __doc__
                    return 0
        except getopt.error, msg:
             raise Usage(msg)
        fetch(args)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
