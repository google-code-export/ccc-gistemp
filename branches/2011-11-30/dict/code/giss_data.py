#!/usr/bin/env python
# $URL$
# $Rev$

"""Classes for GISTEMP data.

Primarily, the classes herein support monthly temperature series.
Typically these are either for stations (station records) or subboxes
(subbox series).  In either case the same class is used, `Series`,
differing in what keyword arguments are supplied.

station records
    Stores a set of monthly averages associated with a particular monitoring
    `Station`.

subbox series
    Stores monthly averages for a subbox, typically synthesized by
    combining several station records together.

Both types of record can be grouped in collections, often (in the original
GISTEMP code) in files. Collections of records have associated metadata,
the `StationMetaData` and `SubboxMetaData` classes.

"""
__docformat__ = "restructuredtext"

import sys
# http://docs.python.org/release/2.4.4/lib/warning-functions.html
import warnings

import read_config

#: The base year for time series data. Data before this time is not
#: used in calculations.
BASE_YEAR = 1880

#: The value that is used to indicate a bad or missing data point.
MISSING = 9999.0

def invalid(v):
    return v == MISSING

def valid(v):
    return not invalid(v)


_v2_sources = None


class Station(object):
    """A station's metadata.

    This holds the information about a single (weather monitoring) station. Not
    all the attributes are used by the CCC code.  For a list of
    attributes and documentation, see the io.station_metadata() function.
    """
    def __init__(self, **values):
        self.__dict__.update(values)

    def __repr__(self):
        return "Station(%r)" % self.__dict__

def get_last_year():
    """Get the latest year of the data.

    We use today's date.  It's much simpler and more reliable than
    anything else.
    """

    # http://docs.python.org/release/2.4.4/lib/module-time.html
    import time
    return time.localtime().tm_year

def v2_sources():
    """Return (and cache) a sources dictionary that maps from 12-digit
    GHCN record ID to source.

    If the source files cannot be found (or read) then an empty
    dictionary is returned.
    """
    global _v2_sources
    if _v2_sources is None:
        try:
            _v2_sources = read_config.v2_get_sources()
        except IOError:
            _v2_sources = {}
            warnings.warn(
              "Could not load GHCN source metadata (mcdw.tbl) files.")
    return _v2_sources


def clear_cache(func):
    """A decorator, for `Series` methods that change the data.

    Any method that changes the underlying data series in a `Series`
    instance must clear the cached values used for some properties.
    This decorator takes care of this chore.

    """
    def f(self, *args, **kwargs):
        return func(self, *args, **kwargs)

    return f


class StationMetaData(object):
    """The metadata for a set of station records.

    :Ivar mo1:
        The number of months covered in the entire data set.
    :Ivar kq:
        The KQ quantity from the header record.
    :Ivar mavg:
        A code indicating the length of time each average value represents. The
        only supported by the CCC code is '6', which indicates that each entry
        is a monthly average. The effect of this having a different value is
        undefined.
    :Ivar monm:
        Maximum length of any time record.
    :Ivar monm4:
        This is the size of this record when written to a GISS Fortran
        unformatted file.

        TODO: This can probably be ditched and calculated as required
        in I/O code.
    :Ivar yrbeg:
        The year of first data.
    :Ivar missing_flag:
        The value used to indicate a missing value in the `series`. This is
        often referred to in other code as variously bad, BAD, XBAD.

        This should become unimportant over time in the CCC code, which should
        stick to always using the `MISSING` value.
    :Ivar precipitation_flag:
        Probably defines a special value that serves a similar purppose to
        the `missing_flag`. This does not seem to be used by any CCC code.
    :Ivar mlast:
        TODO
    :Ivar title:
        A title for this set of station records.
    """
    def __init__(self, **k):
        self.__dict__ = k

    def __repr__(self):
        return 'StationMetadata(%r)' % self.__dict__


# TODO: Needs some review. Among things to think about:
#
# 1. Might it be seen as too complicated? It is complicated for a reason; to
#    make the code that manipulates temperature series more readable.
# 2. Should we use properties or convert the properties to methods?
# 3. Some of the names are open to improvement.
class Series(object):
    """Monthly temperature Series.

    An instance contains a series of monthly data (in ccc-gistemp
    the data are average monthly temperature values in degrees
    Celsius), accessible via the `series` property.  This property
    should **always** be treated as read-only; the effect of modifying
    elements is undefined.

    The series coveres the months from `first_month` to `last_month` month
    inclusive. Months are counted from a non-existant year zero. So January,
    1 AD has a month number of 13, February is 14, etc.

    The GISTEMP/CCC code only uses data that starts from `BASE_YEAR` (1880).
    Some code works on data series that start from this base year. So it is
    convenient to be able to work in terms of years and months relative to this
    base year. There are a number of properties with names that start with
    `rel_` that provide values using this alternative reference.

    Note that most of the series metadata is provided by properties, which
    are effectively read-only. All the instance variables should also be
    treated as read-only and you should only set values in the data series
    using the provided methods.

    There are no subclasses of this class.  Some instances represent
    station records, other instances represent subbox series.

    For station records there can be multiple series for a single `Station`.
    The `station` property provides the associated `Station` instance.
    For a given station the different series are called "duplicates" in
    GHCN terminology; they have a 12-digit uid that is made up of an
    11-digit station identifier and a single extra digit to distinguish
    each of the station's series.

    Generally a station record will have its uid supplied as a keyword
    argument to the constructor (accessing the `station` property relies
    on this):

    :Ivar uid:
        An integer that acts as a unique ID for the time series. This
        is generally a 12-digit identifier taken from the GHCN file; the
        first 11 digits comprise an identifier for the station.
	The last digit distinguishes this series from other series
	from the same station.

    A first year can be supplied to the constructor which will base the
    series at that year:

    :Ivar first_year:
        Set the first year of the series.  Data that are
        subsequently added using add_year will be ignored if they
        precede first_year (a typical use is to set first_year to 1880
        for all records, ensuring that they all start at the same year).

    When used to hold a series for a subbox, for example a record of data
    as stored in the ``input/SBBX.HadR2`` file, then the following
    keyword arguments are traditionally supplied to the constructor:

    :Ivar lat_S, lat_N, lon_W, lon_E:
        Coordinates describing the box's area.
    :Ivar stations:
        The number of stations that contributed to this sub-box.
    :Ivar station_months:
        The number of months that contributed to this sub-box.
    :Ivar d:
        Characteristic distance to station closest to centre.

    """
    def __init__(self, **k):
        self._series = []
        self.ann_anoms = []
        series = None
        assert 'first_year' not in k
        if 'series' in k:
            series = k['series']
            del k['series']
            self.set_series(series)
        self.__dict__.update(k)

        if hasattr(self, 'uid'):
            # Generally applies to station records
            self.source = v2_sources().get(self.uid, "UNKNOWN")
        elif hasattr(self, 'box'):
            # Generally applies to subbox series.
            self.uid = boxuid(self.box)

    def __repr__(self):
        # A bit ugly, because it tries to do something sensible for both
        # station records and subbox series.
        if hasattr(self, 'box'):
            return ('Series(box=(%+06.2f,%+06.2f,%+07.2f,%+07.2f))' %
              tuple(self.box))
        else:
            # Assume it is a station record with a uid.
            return "Series(uid=%r)" % self.uid

    @property
    def series(self):
        """The series of values (conventionally in degrees Celsius)."""
        return self._series

    def __len__(self):
        """The length of the series."""
        return len(self._series)

    @property
    def first_year(self):
        """The year of the first value in the series."""
        return int(min(self._series)[:4])

    @property
    def last_year(self):
        """The year of the last value in the series."""
        return int(max(self._series)[:4])

    @property
    def good_count(self):
        """The number of good values in the data."""
        return len(self._series)

    def get_monthly_valid_counts(self):
        """Get number of good values for each month.

        :Return:
            A list of 12 entries. Entry zero is the number of good entries
            for January, entry 1 for February, etc.

        """
        d = dict((m,len(list(x)))
          for m,x in itertools.groupby(sorted(k[5:7] for k in self._series)))
        monthly_valid = [d.get("%02d" % i+1, 0) for i in range(12)]
        return monthly_valid

    # Year's worth of missing data
    missing_year = [MISSING]*12

    def has_data_for_year(self, year):
        """Return true if record has any valid data for the calendar year
        *year*, false otherwise."""
        for m in range(1,13):
            k = "%04d-%02d" % (year,m)
            if k in self._series:
                return True
        return False

    def _get_a_month(self, month):
        """Get the value for a single month."""
        idx = month - self.first_month
        if idx < 0:
            return MISSING
        try:
            return self.series[month - self.first_month]
        except IndexError:
            return MISSING

    def get_a_year(self, year):
        """Get the time series data for a year."""
        return [self._series.get("%04d-%02d" % (year,m), MISSING)
          for m in range(1,13)]

    def get_set_of_years(self, first_year, last_year):
        """Get a set of year records.

        :Return:
            A list of lists, where each sub-list contains 12 temperature values
            for a given year. This works for any range of years, missing years
            are filled with the MISSING value.

        """
        return [self.get_a_year(y) for y in range(first_year, last_year + 1)]

    def set_ann_anoms(self, ann_anoms):
        self.ann_anoms = dict(ann_anoms)

    def ann_anoms_good_count(self):
        """Number of good values in the annual anomalies"""
        return len(self.ann_anoms)

    @property
    def station_uid(self):
        """The unique ID of the corresponding station."""
        return self.uid[:11]

    def linear(self, begin):
        """Return the series as a linear sequence (list).  *begin*
        specifies the first year of the result sequence; the first entry
        of the result is for January.
        """

        import series

        if not self._series:
            return []
        year_max = int(max(self._series)[:4])
        assert "%04d" % begin < min(self._series)
        return series.aslist(self._series, begin, year_max+1)

    # Mutators below here

    def set_series(self, series):
        """*series* should be a dict that maps from "YYYY-MM" to
        (floating point) temperature."""

        self._series = dict(series)

    def set_value(self, idx, value):
        while idx >= len(self.series):
            self._series.append(MISSING)
        self._series[idx] = value
    set_value = clear_cache(set_value)


class SubboxMetaData(object):
    """The metadata for a set of sub-box records.

    :Ivar mo1:
       TBD
    :Ivar kq:
       TBD
    :Ivar mavg:
       TBD
    :Ivar monm:
       TBD
    :Ivar monm4:
       TBD
    :Ivar yrbeg:
       TBD
    :Ivar missing_flag:
       TBD
    :Ivar precipitation_flag:
       TBD
    :Ivar title:
       TBD
    """
    def __init__(self, mo1, kq, mavg, monm, monm4, yrbeg,
            missing_flag, precipitation_flag, title):
        self.mo1 = mo1
        self.kq = kq
        self.mavg = mavg
        self.monm = monm
        self.monm4 = monm4
        self.yrbeg = yrbeg
        self.missing_flag = missing_flag
        self.precipitation_flag = precipitation_flag
        self.title = title

    def __repr__(self):
        return 'SubboxMetadata(%r)' % self.__dict__

def boxuid(box):
    """Synthesize a uid attribute based on the box's centre."""
    import eqarea
    lat,lon = eqarea.centre(box)
    return "%+05.1f%+06.1fC" % (lat,lon)