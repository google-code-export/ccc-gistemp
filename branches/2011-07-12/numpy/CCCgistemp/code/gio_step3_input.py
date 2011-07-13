def v2meta():
    """Return the GHCN v2 metadata.  Loading it (from the modified
    version of the file supplied by GISS) if necessary.
    """

    # It's important that this file be opened lazily, and not at module
    # load time (if "input/" hasn't been populated yet, it won't be
    # found).
    # See http://code.google.com/p/ccc-gistemp/issues/detail?id=88

    global _v2meta

    v2inv = os.path.join('input', 'v2.inv')
    if not _v2meta:
        _v2meta = augmented_station_metadata(v2inv, format='v2')
    return _v2meta

def augmented_station_metadata(path=None, file=None, format='v2'):
    """Reads station metadata just like augmented_station_metadata() but
    additionally augments records with metadata obtained from another
    file, specified by parameters.augment_metadata.
    """

    meta = station_metadata(path=path, file=file, format=format)
    augments = parameters.augment_metadata
    if augments:
        path,columns = augments.split('=')
        columns = columns.split(',')
        assert 'uid' in columns
        for row in open(path):
            row = row.strip().split(',')
            d = dict(zip(columns,row))
            uid = d['uid']
            if uid in meta:
                meta[uid].__dict__.update(d)
    return meta

def station_metadata(path=None, file=None, format='v2'):
    """Read station metadata from file, return it as a dictionary.
    *format* specifies the format of the metadata can be:
    'v2' for GHCN v2 (with some GISTEMP modifications);
    'v3' for GHCN v3;
    'ushcnv2' for USHCN v2.

    GHCN v2

    For GHCN v2 the input file is nearly in the same format as the
    GHCN v2 file v2.temperature.inv (it has extra fields for satellite
    brightness and extra records for 1 US station and several Antarctic
    stations that GHCN doesn't have).

    Descriptions of that file's format can be found in the Fortran programs:
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.read.inv.f
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.read.data.f

    Here are two typical lines, with a record diagram

    id---------xname--------------------------xlat---xlon----x1---2----34----5-6-7-8-910grveg-----------GU--11
    0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345
    40371148001 ALMASIPPI,MA                    49.55  -98.20  274  287R   -9FLxxno-9x-9COOL FIELD/WOODSA1   0
    42572530000 CHICAGO/O'HARE, ILLINOIS        42.00  -87.90  205  197U 6216FLxxno-9A 1COOL CROPS      C3 125

       uid                 40371148001          42572530000
          The unique ID of the station. This is held as an 11 digit string.
       name                ALMASIPPI,MA         CHICAGO/O'HARE, ILLINOIS
        The station's name.
       lat                 49.55                42.00
        The latitude, in degrees (two decimal places).
       lon                 -98.20               -87.90
        The longitude, in degrees (two decimal places).
    1  stelev              274                  205
        The station elevation in metres.
    2  grelev              287                  197
        The grid elevation in metres (value taken from gridded dataset).
    3  popcls              R                    U
        'R' for rural,  'S' for semi-urban, 'U' for urban.
    4  popsiz              -9                   6216
        Population of town in thousands.
    5  topo                FL                   FL
        The topography.
    6  stveg               xx                   xx
    7  stloc               no                   no
        Whether the station is near a lake (LA) or ocean (OC).
    8  ocndis              -9                   -9
    9  airstn              x                    A
    10 towndis             -9                   1
       grveg               COOL FIELD/WOODS     COOL CROPS
        An indication of vegetation, from a gridded dataset. For example,
        'TROPICAL DRY FOR'.
    G  popcss              A                    C
        Population class based on satellite lights (GHCN value).
    U  us_light            1                    3
        Urban/Rural flag based on satellite lights for US stations
        (' ' for non-US stations).  '1' is dark, '3' is bright.
    11 global_light        0                    125
    Global satellite nighttime light value.  Range 0-186 (at
    least).

    The last two fields (us_light and global_light) are specific to the
    version of the v2.inv file supplied by GISS with GISTEMP.
    """

    # Do not supply both arguments!
    assert not (file and path)

    assert format in ('v2', 'v3', 'ushcnv2')
    if path:
        try:
            file = open(path)
        except IOError:
            warnings.warn("Could not load %s metadata file: %s" %
              (format, path))
            return {}
    assert file

    # With the beta GHCN V3 metadata, several fields are blank for some
    # stations.  When processed as ints, these will get converted to
    # None."""
    def blank_int(s):
        """Convert a field to an int, or if it is blank, convert to
        None."""

        if s.isspace():
            return None
        return int(s)

    # Fields are named after the designators used in the GHCN v3
    # documentation (even for the USHCN v2 and GHCN v2 fields, which
    # have slightly different names in their respective documentation)
    # except for:
    # uid (GHCN: ID), lat (GHCN: latitude), lon (GHCN: longitude),
    # us_light (GISTEMP specific field for nighttime satellite
    # brightness over the US, see Hansen et al 2001), global_light
    # (GISTEMP specific field for global nighttime satellite
    # brightness).
    #
    # GISTEMP only uses some of the fields: uid, lat, lon, popcls (for
    # old-school rural/urban designation), us_light (for old-school
    # rural/urban designation in the US), global_light (for
    # 2010-style rural/urban designation).

    v2fields = dict(
        uid=         (0,   11,  str),
        name=        (12,  42,  str),
        lat=         (43,  49,  float),
        lon=         (50,  57,  float),
        stelev=      (58,  62,  int),
        grelev=      (62,  67,  blank_int),
        popcls=      (67,  68,  str),
        popsiz=      (68,  73,  blank_int),
        topo=        (73,  75,  str),
        stveg=       (75,  77,  str),
        stloc=       (77,  79,  str),
        ocndis=      (79,  81,  blank_int),
        airstn=      (81,  82,  str),
        towndis=     (82,  84,  blank_int),
        grveg=       (84,  100, str),
        popcss=      (100, 101, str),
        us_light=    (101, 102, str),           # GISTEMP only
        global_light=(102, 106, blank_int),     # GISTEMP only
    )
    # See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
    # of metadata file.
    v3fields = dict(
        uid=    (0,    11, str),
        lat=    (12,   20, float),
        lon=    (21,   30, float),
        stelev= (31,   37, float),
        name=   (38,   68, str),
        grelev= (69,   73, blank_int),
        popcls= (73,   74, str),
        popsiz= (75,   79, blank_int),
        topo=   (79,   81, str),
        stveg=  (81,   83, str),
        stloc=  (83,   85, str),
        ocndis= (85,   87, blank_int),
        airstn= (87,   88, str),
        towndis=(88,   90, blank_int),
        grveg=  (90,  106, str),
        popcss= (106, 107, str),
    )
    ushcnv2fields = dict(
        uid=     (0,  6, str),
        lat=     (7, 15, float),
        lon=     (16,25, float),
        stelev=  (26,32, float),
        us_state=(33,35, str),
        name=    (36,66, str),
    )

    if 'v2' == format:
        fields = v2fields
    elif 'v3' == format:
        fields = v3fields
    elif 'ushcnv2' == format:
        fields = ushcnv2fields

    result = {}
    for line in file:
        d = dict((field, convert(line[a:b]))
                  for field, (a,b,convert) in fields.items())
        result[d['uid']] = giss_data.Station(**d)

    return result

def GHCNV2Reader(path="work/step2.v2", file=None, meta=None, year_min=None):
    """Reads a file in GHCN v2.mean format and yields each station.

    If a *meta* dict is supplied then the Series instance will have its
    "station" attribute set to value corresponding to the 11-digit ID in
    the *meta* dict.

    If `year_min` is specified, then only years >= year_min are kept
    (the default, None, keeps all years).

    Traditionally a file in this format was the output of Step 0 (and
    of course the format used by the GHCN source), but modern ccc-gistemp
    produces this format for the outputs of Steps 0, 1, and 2."""

    if path:
        f = open(path)
    else:
        f = file

    def id12(l):
        """Extract the 12-digit station record identifier."""
        return l[:12]

    def v2_float(s):
        """Convert a single datum from string to float; converts missing
        values from their V2 representation, "-9999", to internal
        representation, giss_data.MISSING; scales temperatures to
        convert them from integer tenths to fractional degrees C.
        """

        if "-9999" == s:
            return giss_data.MISSING
        else:
            return float(s) * 0.1

    # The Series.add_year protocol assumes that the years are in
    # increasing sequence.  This is so in the v2.mean file but does not
    # seem to be documented (it seems unlikely to change either).

    # Group the input file into blocks of lines, all of which share the
    # same 12-digit ID.
    for (id, lines) in itertools.groupby(f, id12):
        key = dict(uid=id, first_year=year_min)
        # 11-digit station ID.
        stid = id[:11]
        if meta and meta.get(stid):
            key['station'] = meta[stid]
        record = giss_data.Series(**key)
        prev_line = None
        for line in lines:
            if line != prev_line:
                year = int(line[12:16])
                temps = [v2_float(line[a:a+5]) for a in range(16, 16+12*5, 5)]
                record.add_year(year, temps)
                prev_line = line
            else:
                print ("NOTE: repeated record found: Station %s year %s;"
                       " data are identical" % (line[:12],line[12:16]))

        if len(record) != 0:
            yield record

    f.close()