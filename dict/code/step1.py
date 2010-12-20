#! /usr/bin/env python
# $URL$
# $Rev$
#
# step1.py
#
# Nick Barnes, Ravenbrook Limited, 2008-08-06
# David Jones, Climate Code Foundation, 2010-09-22

"""
Python code reproducing the Step 1 part of the GISTEMP algorithm.  In
this step: duplicate records from the same station (a GHCN v2 feature)
are combined into a single record, if possible; certain records (or
parts) are adjusted or dropped, under the control of configuration
files.

Requires the following files in the input/ directory,
from GISTEMP STEP1/input_files/:

mcdw.tbl
ushcn2.tbl
sumofday.tbl
v2.inv

Do not be tempted to replace v2.inv with the apparently similar
v2.temperature.inv file available from NOAA,
ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.temperature.inv .  The
NOAA file has been treated for GISTEMP's use by, for example, adding
records corresponding to Antarctic stations that are not used in GHCN
but are used in the GISTEMP analysis.  Step 1 (this step) expects to
find a record in v2.inv for every station it has a time series for.

Requires the following files in the config/ directory,
from GISTEMP STEP1/input_files/:

combine_pieces_helena.in
Ts.strange.RSU.list.IN
Ts.discont.RS.alter.IN

Also requires the existence of writeable work/ and log/ directories.
"""

import math
import itertools

# Clear Climate Code
import read_config
from giss_data import valid, invalid, MISSING, BASE_YEAR
import parameters
import series


comb_log = open('log/comb.log','w')
pieces_log = open('log/pieces.log','w')

def comb_records(stream):
    """Combine records for the same station (the same id11) where
    possible.  Records are combined by offsetting based on the average
    difference over their common period, then averaged.  Each combined
    record is yielded.
    """

    return do_combine(stream, comb_log, get_best, combine)

def comb_pieces(stream):
    """comb_pieces() attempts to further combine the records produced
    by comb_records() - which have shorter overlaps - by comparing the
    annual anomalies of the years in which they do overlap, and
    finding ones for which the temperatures (in years which they do
    have in common) are on average closer together than the standard
    deviation of the combined record."""

    return do_combine(stream, pieces_log, get_longest, pieces_combine)

def do_combine(stream, log, select_func, combine_func):
    """Drive record combination.

    This is a filter driver function used by ``comb_records`` and
    ``comb_pieces``.

    :Param stream:
        The stream of records to filter.
    :Param log:
        Open log file file.
    :Param select_func:
        A function to call to select the 'best' record from a collection
        of records (belonging to the same station).
    :Param combine_func:
        A function to call to perform the data combining.

    """
    for id11, record_set in itertools.groupby(stream, lambda r: r.station_uid):
        log.write('%s\n' % id11)
        records = set()
        for record in record_set:
            records.add(record)
            ann_mean, ann_anoms = series.monthly_annual(record.series)
            record.set_ann_anoms(ann_anoms)
            record.ann_mean = ann_mean
        # reduce the collection of records (by combining) until there
        # are none (or one) left.
        while records:
            if len(records) == 1:
                # Just one left, yield it.
                yield records.pop()
                break
            record = select_func(records)
            records.remove(record)
            sums, wgts = fresh_series(record)
            log.write("\t%s %s %s -- %s\n" % (record.uid,
                record.first_year, record.last_year,
                record.source))
            combine_func(sums, wgts, records, log, record.uid)
            final_data = average(sums, wgts)
            record.set_series(final_data)
            yield record

def combine(sums, wgts, records, log, new_id_):
    while records:
        record, diff, overlap = get_longest_overlap(average(sums, wgts),
                                                    records)
        if overlap < parameters.station_combine_min_overlap:
            log.write("\tno other records okay\n")
            return
        records.remove(record)
        offset_and_add(sums, wgts, diff, record)
        log.write("\t %s %d %d %f\n" % (record.uid,
            record.first_year, record.last_year, diff))

def get_best(records):
    """Given a set of records, return the "best" one.
    "best" considers the source of the record, preferring MCDW over
    USHCN over SUMOFDAY over UNKNOWN.

    (this is passed to do_combine() as a select_func argument)
    """

    ranks = {'MCDW': 4, 'USHCN2': 3, 'SUMOFDAY': 2, 'UNKNOWN': 1}
    best = 1
    longest = 0
    for record in sorted(records, key=lambda r: r.uid):
        length = record.ann_anoms_good_count()
        rank = ranks[record.source]
        if rank > best:
            best = rank
            best_rec = record
        elif length > longest:
            longest = length
            longest_rec = record
    if best > 1:
        return best_rec
    return longest_rec

def pieces_combine(sums, wgts, records, log, new_id):
    """The combine_func (passed to do_combine()) for comb_pieces().

    Combines remaining records that have insufficient overlap.
    """

    while records:
        record, diff_, overlap_ = get_longest_overlap(average(sums, wgts),
                                                      records)
        log.write("\t %s %d %d\n" % (record.uid,
           record.first_year, record.last_year))

        is_okay = find_quintuples(sums, wgts, record, new_id, log)

        if is_okay:
            records.remove(record)
            offset_and_add(sums, wgts, 0.0, record)
        else:
            log.write("\t***no other pieces okay***\n")
            return

def get_longest(records):
    """Considering the records in the *records* set, return the longest
    one.  This is the select_func (passed to do_combine()) used by
    comb_pieces."""

    def length(rec):
        """Length of a record, according to the number of valid annual
        anomalies."""

        return rec.ann_anoms_good_count()

    # :todo: If two records have the same "length", then which one is
    # chosen depends on an implementation dependent order (and the order
    # can change the result, by a tiny little bit).  To get the
    # exact same order as previous versions we create a temporary dict
    # here.  Going forwards, we should define the order more carefully.

    t = dict((record.uid, record) for record in records)
    return max(t.values(), key=length)

def find_quintuples(sums, wgts, record, new_id, log):
    """*sums* and *wgts* are each a dict.  As is *record*.
    Returns a boolean."""

    # An identifier common to all the log output.
    logid = "%s %s" % (new_id, record.uid)

    # Get the first and last valid years.
    rec_begin = record.first_year
    rec_end = record.last_year

    actual_begin, actual_end = get_actual_endpoints(wgts)

    max_begin = max(actual_begin, rec_begin)
    min_end = min(actual_end, rec_end)
    # Since max_begin and min_end are integers, this rounds fractional
    # middle years up.
    middle_year = int(.5 * (max_begin + min_end) + 0.5)
    log.write("max begin: %s\tmin end: %s\n" % (max_begin, min_end))

    new_data = average(sums, wgts)
    new_ann_mean, new_ann_anoms = series.monthly_annual(new_data)
    ann_std_dev = sigma(new_ann_anoms)
    log.write("ann_std_dev = %s\n" % ann_std_dev)

    rec_ann_anoms = record.ann_anoms
    rec_ann_mean = record.ann_mean

    # Whether we have an "overlap" or not.  We have an "overlap" if
    # within *rad* years either side of *middle_year* both records have
    # *parameters.station_combine_min_mid_year* valid annnual anomalies.
    ov_success = False
    # The overlap is "okay" when the difference in annual temperature is
    # below a certain threshold.
    okay_flag = False
    for rad in range(1, parameters.station_combine_bucket_radius + 1):
        # For the two series, get data from from -rad to rad (inclusive)
        # around the middle year.
        base = middle_year - rad
        limit = middle_year + rad+1
        new_middle = [new_ann_anoms[x]
          for x in xrange(base, limit) if x in new_ann_anoms]
        rec_middle = [rec_ann_anoms[x]
          for x in xrange(base, limit) if x in rec_ann_anoms]
        if (len(new_middle) >= parameters.station_combine_min_mid_years
            and len(rec_middle) >= parameters.station_combine_min_mid_years):
            log.write("overlap success: %s\n" % logid)
            ov_success = True
            avg1 = sum(anom+new_ann_mean for anom in new_middle) / float(
              len(new_middle))
            avg2 = sum(anom+rec_ann_mean for anom in rec_middle) / float(
              len(rec_middle))
            diff = abs(avg1 - avg2)
            log.write("diff = %s\n" % diff)
            if diff < ann_std_dev:
                okay_flag = True
                log.write("combination success: %s\n" % logid)
            else:
                log.write("combination failure: %s\n" % logid)
            break
    if not ov_success:
        log.write("overlap failure: %s\n" % logid)
    log.write("counts: %d %d\n" % (len(new_middle), len(rec_middle)))
    return okay_flag


def adjust_helena(stream):
    """Modifies records as specified in config/combine_pieces_helena.in,
    by adding the delta to every datum for that station prior to the
    specified month.
    """
    helena_ds = read_config.get_helena_dict()
    for record in stream:
        id = record.uid
        if helena_ds.has_key(id):
            series = record.series
            this_year, month, summand = helena_ds[id]
            begin = record.first_year
            # Dict key for the month specified in the config file.
            M = "%04d-%02d" % (this_year, month)
            # All valid data up to and including M get adjusted
            for k in series:
                if k <= M:
                    series[k] += summand
            record.set_series( series)
            del helena_ds[id]
        yield record

def drop_strange(data):
    """Drops station records, or parts of records, under control of
    the file 'config/Ts.strange.RSU.list.IN' file.
    """

    changes_dict = read_config.get_changes_dict()
    for record in data:
        changes = changes_dict.get(record.uid, [])
        series = record.series
        begin = record.first_year
        end = record.last_year
        for (kind, year, x) in changes:
            if kind == 'years':
                # omit all the data from year1 to year2, inclusive
                year1 = year
                year2 = x
                if year1 <= begin and year2 >= end:
                    # Drop this whole record.  Note: avoids "else:"
                    # clause at end of "for" loop.
                    break
                base = str(year1)
                limit = str(year2+1)
                # Because we are going to delete items in the *series*
                # dict, we must take a copy of keys when iterating.
                for k in series.keys():
                    if base <= k < limit:
                        del series[k]

            else: # remove a single month
                k = "%04d-%02d" % (year, x)
                if k in series:
                    del series[k]
                else:
                    print "drop strange: %s %s is missing anyway" % (
                      record.uid, k)
        else:
            record.set_series(series)
            yield record


def alter_discont(data):
    """Modifies records as specified in config/Ts.discont.RS.alter.IN,
    by adding the delta to every datum for that station prior to the
    specified month.  Yes, this is very similar to adjust_helena().
    """

    alter_dict = read_config.get_alter_dict()
    for record in data:
        if alter_dict.has_key(record.uid):
            series = record.series
            (a_month, a_year, a_num) = alter_dict[record.uid]
            # Dict key for the month specified in the config file.
            M = "%04d-%02d" % (a_year, a_month)
            # Every (valid) month up to and not including the month in
            # question is adjusted.
            for k in series:
                if k < M:
                    series[k] += a_num
            record.set_series(series)

        yield record


def average(sums, counts):
    """Divide *sums* by *counts* to make a series of averages.
    Return an dict with values sums[k]/counts[k] (for every k in
    *sums*).
    """

    # We assume something stronger than our assert: that the set
    # of keys in *sums* is the same as the set of keys in *counts*.
    assert len(sums) == len(counts)

    return dict((k,float(v)/counts[k]) for k,v in sums.iteritems())

def offset_and_add(sums, wgts, diff, record):
    """Add the data from *record* to the *sums* and *wgts* arrays, first
    shifting it by subtracting *diff*.  The arrays and *record* are
    assumd to start with the same year.
    """

    for k,datum in record.series.iteritems():
        sums[k] = sums.get(k, 0.0) + datum - diff
        wgts[k] = wgts.get(k, 0) + 1

def get_longest_overlap(target, records):
    """Find the record in the *records* set that has the longest
    overlap with the *target* by considering annual anomalies.  *target*
    is a dict of monthly values.

    A triple (record, diff, overlap) is returned; *diff* is the average
    difference in annual anomalies between *record* and *target*
    (positive when *record* is higher); *overlap* is the number of years
    in the overlap.  Even when there is no overlap _some_ record is
    returned and in that case *diff* is None and *overlap* is 0.
    """

    # Annual mean, and annual anomaly sequence.
    mean, anoms = series.monthly_annual(target)
    overlap = 0
    diff = None
    # :todo: the records are consulted in an essentially arbitrary
    # order (which depends on the implementation), but the order
    # may affect the result.  Tie breaks go to the last record consulted.
    # For exact compatiblity with previous versions, we create a
    # temporary dict.
    t = dict((record.uid, record) for record in records)
    for record in t.values():
        common_years = set(record.ann_anoms) & set(anoms)
        common = [(record.ann_anoms[k],anoms[k]) for k in common_years]
        if len(common) < overlap:
            continue
        overlap = len(common)
        best_record = record
        S = sum((record.ann_mean+rec_anom) - (mean+anom)
                for rec_anom, anom in common)
        if common:
            diff = S / len(common)
    return best_record, diff, overlap

def fresh_series(record):
    """Make and return a fresh copy of the series.  A pair of
    (*series*,*weight*) is returned; each is a dict.
    """

    series = dict(record.series)
    weight = dict((k,1) for k in series)

    return series,weight

def sigma(d):
    """Compute and return the standard deviation, sigma, for the values
    in the dict *d*.
    """

    l = d.values()
    if not l:
        return MISSING
    # Two pass method ensures argument to sqrt is always positive.
    mean = sum(l) / len(l)
    sigma_squared = sum((x-mean)**2 for x in l)
    return math.sqrt(sigma_squared/len(l))

def get_actual_endpoints(wgts):
    """For the dict of weights in *wgts* return the first and last
    calendar years that have some weight.  Assumes that any present key
    in the dict is associated with non-zero weight.
    """

    minyear = int(min(wgts)[:4])
    maxyear = int(max(wgts)[:4])
    return minyear, maxyear

def step1(record_source):
    """An iterator for step 1.  Produces a stream of
    `giss_data.Series` instances.

    :Param record_source:
        An iterable source of `giss_data.Series` instances (which it
        will assume are station records).

    """
    records = comb_records(record_source)
    helena_adjusted = adjust_helena(records)
    combined_pieces = comb_pieces(helena_adjusted)
    without_strange = drop_strange(combined_pieces)
    for record in alter_discont(without_strange):
        yield record
