.. Step 5 also call series.combine (./code/step5.py)
.. Check URLs

NumPy Report
============

This report describes the different attempts made to create an
alternative implementation of ccc-gistemp using NumPy arrays.


The problem
-----------

#. The original ccc-gistemp is coded in pure python relying on list
   comprehensions and "for loops" for its algebra. That result is a slow code
   that takes approximately 30 minutes on a Intel(R) Core(TM)2 Duo CPU
   E8400@3.00GHz machine.
#. The code performs several checks for valid (good temperature records) and
   invalid (9999.0) entries. The significant amount of "missing values" checked
   via the valid() and invalid() function result in a call overhead that
   slows down the code.
#. Profiling of the whole code pointed to step3 (out of 6) as the most slow.
   More specifically series.combine() and the already mentioned overhead call
   on valid() and invalid() function calls from series.combine().


Masked array effort
'''''''''''''''''''

The first attempt was to remove the valid()/invalid() calls making use of
NumPy's masked_arrays while vectorizing the code.

The creation of the masked_array and its use to get valid and invalid values
is faster than the current design. For example, at

http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/step3.py?r=690#169

we have the following list comprehension

.. code-block:: python

    >>> weight = [wt*valid(v) for v in subbox_series]

that becomes:

http://code.google.com/p/ccc-gistemp/source/browse/branches/2011-07-12/numpy/CCCgistemp/code/step3.py?spec=svn928&r=928#181

.. code-block:: python

    >>> weight = wt * ~subbox_series_masked.mask

another examples at,

http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/step3.py?r=690#180

.. code-block:: python

    >>> l = [any(valid(v) for v in subbox_series[i::12])
    ...   for i in range(12)]

becomes:

http://code.google.com/p/ccc-gistemp/source/browse/branches/2011-07-12/numpy/CCCgistemp/code/step3.py?spec=svn928&r=928#197

.. code-block:: python

    >>> a = subbox_series_masked.reshape(12, subbox_series_masked.size/12, order='F')
    >>> l = np.any(~a.mask, axis=1)

In both examples the list comprehension was avoided and the result was
obtained directly, or almost directly after reshaping the array.

However, masked_array is known to have a bad performance [1] when used to
algebraic operations. That results in even slower code on series.combine().

A second attempt using masked_array and stripping the data and values from it
was implemented and later dropped. David recommend a masked_array "free"
implementation. It is virtually the same logic but without the masked_array
syntax (a little bit cleaner.)

Bottleneck
''''''''''

I also made a quick attempt with the 3rd party module bottleneck [2]. This
module deals with missing value operations much faster than NumPy.

In this implementation all missing values were converted to np.nan
(Not-a-Number) and the operations were carried out with bn.nansum() and etc.

http://code.google.com/p/ccc-gistemp/source/browse/branches/2011-07-12/numpy/CCCgistemp/code/series.py?spec=svn869&r=869#14

This attempt was also dropped after David's recommendation.

    .. code-block:: python

        """obs: The bottleneck module would be useless up to this part, since
        we still need to create the common mask. It became useful just as a
        substitute for operations like:"""

        >>> sum_new = np.sum((new * mask), axis=1)
        # would became,
        >>> sum_new = bn.nansum(new, axis=1)
        # but that would require changing MISSING values from 9999. to np.nan.

        # Some simple tests with an array A that has 1 missing value:

        >>> %timeit np.nansum(A, axis=1)
        10000 loops, best of 3: 25.6 us per loop
        >>> %timeit np.sum(A*mask, axis=1)
        100000 loops, best of 3: 12.3 us per loop
        >>> %timeit bn.nansum(A, axis=1)
        100000 loops, best of 3: 2.58 us per loop

        # Bottleneck is by far the fastest way to perform operations with
        # missing values.


Pure NumPy
'''''''''''

The current state implements a pure NumPy version of series.combine(), renamed
series.combine_array() to avoid disturbing step5. However, step5 should also be
calling the same series.combine_array() at a later implementation. There are no
changes on step3.py.

http://code.google.com/p/ccc-gistemp/source/browse/branches/2011-07-12/numpy/CCCgistemp/code/series.py

The first step is to convert all the inputs to arrays.

.. code-block:: python

    >>> composite, weight, new, new_weight = map(np.asanyarray,
    ...                               (composite, weight, new, new_weight))

Here we use np.asanyarray() instead of np.array, because it is faster if the
input is an array already, and make the code more "generic". It means that this
part of the code does not have to be changed later if a future ccc-gistemp
re-write already provide an array or a masked_array to series.combine_array().

There is some performance hit when converting lists to arrays. A future version
of the code should be all NumPy arrays to avoid this conversion (check the
profile numpy-step3.pstats).

The next step we reshape the arrays into months by years. The order='F' means
FORTRAN (column-major) order.

.. code-block:: python

    >>> size = composite.size
    >>> shape = (12, size/12)
    >>> composite, weight, new = map(lambda x: np.reshape(x, shape, order='F'),
    ...                                               (composite, weight, new))

At this point the original code performs a loop over all months, and in a second
inner loop (over the elements of a month) it checks for valid values of both
*composite* and *new*. If both *composite* and *new* are valid it updates the
values of *sum_new* (Sum of data in new), *sum* (Sum of data in composite), and
*count* (Number of years where both new and composite are valid.)

http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/series.py#46

To compute all these qunaities without looping we must first get a mask where
both *composite* and *new* have missing points.

.. code-block:: python

    >>> new_mask = new == MISSING  # get *new* MISSING values
    >>> comp_mask = composite == MISSING  # get composite missing values
    >>> comp_mask[new_mask] = True  # get a common mask
    >>> mask = ~comp_mask
    # mask[i] is True (1) when both *composite* and *new* are valid.

The variable *new_weight* became an array with zeros at invalid values after
this point,

.. code-block:: python

    >>> new_weight = new_weight * ~new_mask

    """obs: If we chose to do this before calling series.combine(), that way
    *weight* would have the missing information for *composite* while
    *new_weight* would have the same information but for *new*. We must check
    later how this implementation would affect step5.py."""

Now *count*, *sum*, and *sum_new* is just:

.. code-block:: python

    >>> count = np.array([np.count_nonzero(mask[i, :]) for i in range(12)])
    >>> sum = np.sum((composite * mask), axis=1)
    >>> sum_new = np.sum((new * mask), axis=1)

    """obs: np.count_nonzero() does not have an axis keyword, hence the list
    comprehension there."""

After this step the original code checks if *count* is less than *min_overlap*.
There must be a minimum overlap of 20 months (this value is can be changed.) If
this statement is true the code compute *bias* using only the points where
*composite* and *new* are both valid.

Original code:

.. code-block:: python

    >>> bias = (sum-sum_new)/count

http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/series.py#55

NumPy array:

.. code-block:: python

    >>> bias = np.sum((composite - new) * mask, axis=1) / count

http://code.google.com/p/ccc-gistemp/source/browse/branches/2011-07-12/numpy/CCCgistemp/code/series.py#79

Since we did not checked for count < min_overlap, we now create a variable
*enough_months*,

.. code-block:: python

    >>> enough_months = count >= min_overlap

that is used to zero out *new_count* that were updated even when *count* was
>= min_overlap. However, that still does not resolve the issue of updating
composite when *count < min_overlap*. This current implementation returns the
right *data_combined* but the WRONG updated values from *composite*!

Now we can update *composite* and *new_weight*:

.. code-block:: python

    >>> new_month_weight = weight + new_weight
    >>> composite = (weight * composite + new_weight *
    ...                             (new + bias[:, None])) / new_month_weight

    # Here we get some zero divide at the points where both composite and new
    # where invalid. I believe it is safe to set them to zero.
    if 0:
        >>> composite[np.isnan(composite)] = 0

    # and finally the *new_count*,
    >>> new_count = np.array([np.count_nonzero(composite[i, :]) for i in
    ...                                                            range(12)])

    # that ultimately became the *data_combined*,
    >>> data_combined = (new_count * enough_months).tolist()

Conclusion
----------

The NumPy implementation did not speed-up the code a lot, actually it just
matches the speed when we removed the function call overhead by changing
the calls to invalid()/valid() to direct comparisons to  MISSING (9999.0).

The computation of *data_combined* is correct, but series.combine_array()
returns a bad *composite* and *weight* by modifying them wrongly. My suspicious
That happens because the are are not updated iteratively when *count <
min_overlap* like in the original code. Another possibility is the conversion
to arrays.

Future
------

#. Load the data and convert it to NumPy array (and store at Series.series).
#. Pad the series inside Series.series and make them all the same size
   so a "reshaped array" can be stored.
#. Fix the *composite* and *weight* update.
#. The function step3.incircle() is the second bottleneck of step3, re-write it
   to use NumPy arrays.

References:
-----------
[1] http://mail.scipy.org/pipermail/numpy-discussion/2009-May/042425.html
[2] http://pypi.python.org/pypi/Bottleneck

Appendix
--------
URLs for the profiling:
    * full run of the original code:

    * step3 of the original code:

    * step3 using NumPy:


OBS: The NumPy version cannot be run twice on the same project directory or it will yield the wrong data_combined