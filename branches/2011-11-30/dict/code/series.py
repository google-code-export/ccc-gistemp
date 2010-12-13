#!/usr/bin/env python
# $URL$
# $Rev$
#
# series.py
#
# Nick Barnes, Ravenbrook Limited, 2010-03-08

import itertools
from giss_data import valid, invalid, MISSING

"""
Shared series-processing code in the GISTEMP algorithm.
"""


def combine(average, weight, new, new_weight, min_overlap):
    """Run the GISTEMP combining algorithm.  This combines the data
    in the *new* dict into the *average* dict.  *new* has associated
    weights in the *new_weight* dict, *average* has weights in the
    *weight* dict.

    *average* stores a time series as a dict that maps from "YYYY-MM"
    keys to temperature values.  Similarly for *new*.  The weight dicts,
    *weight* and *new_weight* store weights in a similar fashion.

    *new_weight* can be either a constant or an dict of weights for
     each datum in *new*.

    The number of month records combined is returned.  The *average* and
    *weight* dicts are mutated.

    Each month of the year is considered separately.  For the set of
    times where both *average* and *new* have data the mean difference
    (a bias) is computed.  If there are fewer than *min_overlap* years
    in common the data (for that month of the year) are not combined.
    The bias is subtracted from the *new* record and it is point-wise
    combined into *average* according to the weight *new_weight* and
    the existing weights for *average*.
    """

    assert 0 < min_overlap
    new_weight = ensure_container(weight, new_weight)

    months_combined = 0
    # Set of months (keys) in *average* (the reference series).
    ref_keys = set(average)
    # Group the months together, first all the januarys, then all the
    # februarys, and so on.
    for m,keys in itertools.groupby(sorted(new, key=key_month),
      key=key_month):
        kl = list(keys)
        common = set(kl) & set(average)
        if len(common) < min_overlap:
            continue
        # Differences for the common overlap.
        diff = [average[m]-new[m] for m in common]
        bias = sum(diff)/float(len(diff))

        # :todo: perhaps a bit faster (and maybe clearer) to store the
        # *average* series not divided by the weights; and then divide
        # by the weights at the end of combining.
        # Update period of valid data, averages and weights
        for k in keys:
            new_month_weight = weight.get(k, 0) + new_weight[k]
            average[k] = (weight.get(k, 0)*average.get(k, 0)
                          + new_weight[k]*(new[k]+bias))/new_month_weight
            weight[k] = new_month_weight
            months_combined += 1
    return months_combined

def ensure_container(exemplar, item):
    """Coerces *item* to be a container (a dict); if *item* is
    already a dict it is returned unchanged.  Otherwise, a dict
    containing the same keys as *exemplar* is created which contains
    *item* at every key.  The fresh dict is returned.
    """

    try:
        '0000-00' in item
        return item
    except TypeError:
        return dict((k,item) for k in exemplar)

def anomalize(data, reference_period=None):
    """Turn the series *data* into anomalies, based on monthly
    averages over the *reference_period*, for example (1951, 1980).
    If *reference_period* is None then the averages are computed
    over the whole series.  Similarly, If any month has no data in
    the reference period, the average for that month is computed
    over the whole series.

    A fresh dict is returned.
    """

    # :todo: consider not going via monthly_anomalies format.
    means_, anoms = monthly_anomalies(data, reference_period)
    result = {}
    for d in anoms:
        result.update(d)
    return result

def valid_mean(seq, min=1):
    """Takes a sequence, *seq*, and computes the mean of the valid
    items (using the valid() function).  If there are fewer than *min*
    valid items, the mean is MISSING."""

    count = 0
    sum = 0.0
    for x in seq:
        if valid(x):
            sum += x
            count += 1
    if count >= min:
        return sum/float(count)
    else:
        return MISSING

def monthly_anomalies(data, reference_period=None):
    """Calculate monthly anomalies, by subtracting from every datum
    the mean for its month.  A pair of (monthly_mean, monthly_anom) is
    returned.  *monthly_mean* is a 12-long sequence giving the mean for
    each of the 12 months; *monthly_anom* is a 12-long sequence giving
    the anomalized series for each of the 12 months.

    If *reference_period* is supplied then it should be a pair (*first*,
    *last) and the mean for a month is taken over the period (an example
    would be reference_period=(1951,1980)).
    
    The input data is a dict that maps from "YYYY-MM" to temperature
    values.
    """

    if reference_period:
        base = reference_period[0]
        limit = reference_period[1] + 1
    else:
        # Setting base, limit to (0,9999) is a bit of a hack.
        base = 0
        limit = 9999
    # Convert base and limit to 4 digit strings, we will be comparing
    # them lexicographically.
    base = "%04d" % base
    limit = "%04d" % limit
    # *mean_dict* and *anom_dict* are each dicts storing that
    # calendar month's mean and anomaly series.  The keys in each case
    # are 2 digit strings of the form "MM" ("02" for February, and so on).
    mean_dict = {}
    anom_dict = {}
    for m, keys in itertools.groupby(sorted(data, key=key_month),
      key=key_month):
        kl = list(keys)
        base_temps = [data[k] for k in kl if base <= k < limit]
        if not base_temps:
            # Fall back to using entire period
            base_temps = [data[k] for k in kl]
        mean = sum(base_temps)/float(len(base_temps))
        mean_dict[m] = mean
        # Convert to anomalies.
        anom_dict[m] = dict((k, data[k]-mean) for k in kl)
    # Conver to 12-element lists, noting that not all months may be
    # present in the dicts.
    mean_list = [mean_dict.get("%02d" % (i+1), MISSING) for i in range(12)]
    anom_list = [anom_dict.get("%02d" % (i+1), {}) for i in range(12)]
    return mean_list, anom_list

def key_month(s):
    """Return the month part of a key used in a series dict."""
    return s[5:7]

# Originally from step1.py
def monthly_annual(data):
    """From a sequence of monthly data, compute an annual mean and
    sequence of annual anomalies.  This has a particular algorithm
    (via monthly and then seasonal means and anomalies), which must
    be maintained for bit-for-bit compatibility with GISTEMP; maybe
    we can drop it later.  A pair (annual_mean, annual_anomalies) is
    returned.
    """
    
    years = len(data) // 12
    monthly_mean, monthly_anom = monthly_anomalies(data)

    # :todo:
    # The seasonal calculation shoud be abstracted into a function.
    # inputs: years, monthly_anom, monthly_mean
    # outputs: seasonal_anom, seasonal_mean
    # Average monthly means to make seasonal means,
    # and monthly anomalies to make seasonal anomalies.
    seasonal_mean = []
    seasonal_anom = []
    # Compute seasonal anomalies; each season consists of 3 months.
    for months in [[11, 0, 1],
                   [2, 3, 4],
                   [5, 6, 7],
                   [8, 9, 10],]:
        # Need at least two valid months for a valid season.
        seasonal_mean.append(valid_mean((monthly_mean[m] for m in months),
                                        min = 2))
        # A list of 3 data series, each being an extract for a
        # particular month.
        month_in_season = []
        for m in months:
            row = monthly_anom[m] # the list of anomalies for month m
            if m == 11:
                # For December, we take the December of the previous
                # year.  Which we do by shifting the array, and not
                # using the most recent December.
                row[1:] = row[:-1]
                row[0] = MISSING
            month_in_season.append(row)
        seasonal_anom_row = []
        for n in range(years):
            m = valid_mean((data[n] for data in month_in_season),
                           min = 2)
            seasonal_anom_row.append(m)
        seasonal_anom.append(seasonal_anom_row)

    # Average seasonal means to make annual mean,
    # and average seasonal anomalies to make annual anomalies
    # (note: annual anomalies are December-to-November).
    annual_mean = valid_mean(seasonal_mean, min = 3)
    annual_anom = []
    for n in range(years):
        annual_anom.append(valid_mean((data[n] for data in seasonal_anom),
                                      min = 3))
    return (annual_mean, annual_anom)

