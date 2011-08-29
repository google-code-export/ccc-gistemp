#!/usr/bin/env python
# $URL$
# $Rev$
#
# series.py
#
# Nick Barnes, Ravenbrook Limited, 2010-03-08

import itertools
from giss_data import valid, invalid, MISSING

import numpy as np

"""
Shared series-processing code in the GISTEMP algorithm.
"""

def combine_array(composite, weight, new, new_weight, min_overlap):
    """Run the GISTEMP combining algorithm.  This combines the data
    in the *new* array into the *composite* array.  *new* has weight
    *new_weight*; *composite* has weights in the *weight* array.

    *new_weight* can be either a constant or an array of weights for
     each datum in *new*.

    For each of the 12 months of the year, track is kept of how many
    new data are combined.  This list of 12 elements is returned.

    Each month of the year is considered separately.  For the set of
    times where both *composite* and *new* have data the mean difference
    (a bias) is computed.  If there are fewer than *min_overlap* years
    in common the data (for that month of the year) are not combined.
    The bias is subtracted from the *new* record and it is point-wise
    combined into *composite* according to the weight *new_weight* and
    the existing weights for *composite*.

    NOTE: I'm calling function series.combine_array() because step5 also calls
          series.combine(). Once I check if this version works OK there as well
          I'll substitute series.combine() with this version.
    """

    if 0:
        # TODO: This must be fixed for step5. If step5 array is the same size
        # as new_mask nothing is needed.
        new_weight = ensure_array(weight, new_weight)

    # Convert all input to NumPy arrays. This won't be need once I convert
    # Series.series to array.
    #composite, weight, new, new_weight = map(np.asanyarray,
                                          #(composite, weight, new, new_weight))

    composite, weight, new, new_weight = map(np.array,
                                          (composite, weight, new, new_weight))
    # Reshape the arrays into months (12) by years (132 -- so far.).
    # If Series.series is padded by default this can be done there together
    # with the array conversion at Series.series.
    size = composite.size
    shape = (12, size / 12)
    composite, weight, new = map(lambda x: np.reshape(x, shape, order='F'),
                                                      (composite, weight, new))

    # Get *new* and *composite* missing values.
    new_mask = new == MISSING
    comp_mask = composite == MISSING

    # NOTE: Make *new_weight* an array of month by year with zeros at *new*
    # invalid points. This might be a problem for step5. It would be preferable
    # that new_weight comes as an array at the input.
    new_weight = new_weight * ~new_mask

    # Combined missing values from both *composite* and *new* into one mask.
    comp_mask[new_mask] = True
    # NOTE: mask[i] is True (1) when both composite and new are valid.
    mask = ~comp_mask

    count = np.sum(mask, axis=1)

    # NOTE: Zero divided warning.
    bias = np.sum((composite - new) * mask, axis=1) / count

    # Check for enough months (minimum overlap.)
    enough_months = count >= min_overlap

    new_month_weight = weight + new_weight

    composite = (weight * composite + new_weight *
                                   (new + bias[:, None])) / new_month_weight
    # FIXME: Zero divide here at points where both composite and new where
    # invalid. I guess it is safe to set them to zero.
    if 0:
        composite[np.isnan(composite)] = 0
    composite[new_mask] = 0
    new_count = np.array([np.count_nonzero(composite[i, :]) for i in range(12)])

    data_combined = (new_count * enough_months).tolist()

    return data_combined


def combine(composite, weight, new, new_weight, min_overlap):
    """Run the GISTEMP combining algorithm.  This combines the data
    in the *new* array into the *composite* array.  *new* has weight
    *new_weight*; *composite* has weights in the *weight* array.

    *new_weight* can be either a constant or an array of weights for
     each datum in *new*.

    For each of the 12 months of the year, track is kept of how many
    new data are combined.  This list of 12 elements is returned.

    Each month of the year is considered separately.  For the set of
    times where both *composite* and *new* have data the mean difference
    (a bias) is computed.  If there are fewer than *min_overlap* years
    in common the data (for that month of the year) are not combined.
    The bias is subtracted from the *new* record and it is point-wise
    combined into *composite* according to the weight *new_weight* and
    the existing weights for *composite*.
    """

    new_weight = ensure_array(weight, new_weight)

    # A count (of combined data) for each month.
    data_combined = [0] * 12

    # TODO: REMOVE
    #f = open('list.txt','w')

    for m in range(12):
        sum_new = 0.0  # Sum of data in new
        sum = 0.0  # Sum of data in composite
        count = 0  # Number of years where both new and composite are valid.

        for a, n in itertools.izip(composite[m::12], new[m::12]):
            if invalid(a) or invalid(n):
                continue
            count += 1
            sum += a
            sum_new += n
            #print >>f, "count: %s, sum: %s, sum_new: %s" % (count, sum, sum_new)
        if count < min_overlap:
            continue
        bias = (sum - sum_new) / count
        #print >>f, "m: %s" % m
        #print >>f, "count: %s, sum: %s, sum_new: %s, bias: %s" % (count, sum, sum_new, bias)

        # Update period of valid data, composite and weights.
        for i in range(m, len(new), 12):
            if invalid(new[i]):
                continue
            new_month_weight = weight[i] + new_weight[i]

            composite[i] = (weight[i] * composite[i] + new_weight[i] *
                                            (new[i] + bias)) / new_month_weight

            weight[i] = new_month_weight

            data_combined[m] += 1

    #print >>f, "new_month_weight: %s\n, data_combined: %s" % (new_month_weight, data_combined)
    return data_combined


def ensure_array(exemplar, item):
    """Coerces *item* to be an array (linear sequence); if *item* is
    already an array it is returned unchanged.  Otherwise, an array of
    the same length as exemplar is created which contains *item* at
    every index.  The fresh array is returned.
    """

    try:
        item[0]
        return item
    except TypeError:
        return (item,) * len(exemplar)


def anomalize(data, reference_period=None, base_year=-9999):
    """Turn the series *data* into anomalies, based on monthly
    averages over the *reference_period*, for example (1951, 1980).
    *base_year* is the first year of the series.  If *reference_period*
    is None then the averages are computed over the whole series.
    Similarly, If any month has no data in the reference period,
    the average for that month is computed over the whole series.

    The *data* sequence is mutated.
    """

    means, anoms = monthly_anomalies(data, reference_period, base_year)
    # Each of the elements in *anoms* are the anomalies for one of the
    # months of the year (for example, January).  We need to splice each
    # month back into a single linear series.
    for m in range(12):
        data[m::12] = anoms[m]


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
        return sum / float(count)
    else:
        return MISSING


def monthly_anomalies(data, reference_period=None, base_year=-9999):
    """Calculate monthly anomalies, by subtracting from every datum
    the mean for its month.  A pair of (monthly_mean, monthly_anom) is
    returned.  *monthly_mean* is a 12-long sequence giving the mean for
    each of the 12 months; *monthly_anom* is a 12-long sequence giving
    the anomalized series for each of the 12 months.

    If *reference_period* is supplied then it should be a pair (*first*,
    *last) and the mean for a month is taken over the period (an example
    would be reference_period=(1951,1980)).  *base_year* specifies the
    first year of the data.

    The input data is a flat sequence, one datum per month.
    Effectively the data changes shape as it passes through this
    function.
    """

    years = len(data) // 12
    if reference_period:
        base = reference_period[0] - base_year
        limit = reference_period[1] - base_year + 1
    else:
        # Setting base, limit to (0,0) is a bit of a hack, but it
        # does work.
        base = 0
        limit = 0
    monthly_mean = []
    monthly_anom = []
    for m in range(12):
        row = data[m::12]
        mean = valid_mean(row[base:limit])
        if invalid(mean):
            # Fall back to using entire period
            mean = valid_mean(row)
        monthly_mean.append(mean)
        if valid(mean):
            def asanom(datum):
                """Convert a single datum to anomaly."""
                if valid(datum):
                    return datum - mean
                return MISSING
            monthly_anom.append(map(asanom, row))
        else:
            monthly_anom.append([MISSING] * years)
    return monthly_mean, monthly_anom


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
                   [8, 9, 10], ]:
        # Need at least two valid months for a valid season.
        seasonal_mean.append(valid_mean((monthly_mean[m] for m in months),
                                        min=2))
        # A list of 3 data series, each being an extract for a
        # particular month.
        month_in_season = []
        for m in months:
            row = monthly_anom[m]  # the list of anomalies for month m
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
                           min=2)
            seasonal_anom_row.append(m)
        seasonal_anom.append(seasonal_anom_row)

    # Average seasonal means to make annual mean,
    # and average seasonal anomalies to make annual anomalies
    # (note: annual anomalies are December-to-November).
    annual_mean = valid_mean(seasonal_mean, min=3)
    annual_anom = []
    for n in range(years):
        annual_anom.append(valid_mean((data[n] for data in seasonal_anom),
                                      min=3))
    return (annual_mean, annual_anom)
