.. Step 5 also call series.combine!!! ./code/step5.py

NumPy Report
============

This report describes the different attempts made to create an
alternative implementation of ccc-gistemp using NumPy arrays.


The problem
-----------
#. The original ccc-gistemp is is pure python and make use of list
   comprehension and loops for its algebra. That result in a very slow code,
   approximately 30 minutes on a Intel(R) Core(TM)2 Duo CPU E8400 @ 3.00GHz
   machine.
#. The code relies on several checks for valid and invalid (9999.0) entries.
   The significant amount of "missing values" checked via the valid() and
   invalid() function result in a call overhead that slows down the code.
#. Profiling of the whole code pointed to step3 as the most slow. More
   specifically series.combine() and the function overhead call on valid()
   and invalid() functions there.


Masked array effort
-------------------
The first attempt was to remove the valid()/invalid() calls making use of
NumPy's masked_arrays while vectorizing the code.

It turns out that the creation of the masked_array and its use to get valid
and invalid values are faster than the current design. For example, at

http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/step3.py?r=690#169

we have the following list comprehension 
>>> weight = [wt*valid(v) for v in subbox_series]

that becomes:
>>> weight = wt * ~subbox_series_masked.mask

or,

>>> l = [any(valid(v) for v in subbox_series[i::12])
...   for i in range(12)]

become:

>>> a = subbox_series_masked.reshape(12, subbox_series_masked.size/12, order='F')
>>> l = np.any(~a.mask, axis=1)

In both examples the list comprehension was avoided and the result was
obtained directly or almost directly after reshaping the array.


However, masked_array is known to have a bad performance [1] when used to
algebraic operations. That result in even slower code on series.combine().

A second attempt using masked_array and stripping the data and values from it
was implemented and later dropped. David recommend a masked_array "free"
implementation.

Bottleneck
----------

I also made a quick attempt with the 3rd party module bottleneck [2]. This
module deals with missing value operations much faster than NumPy. 

In this implementation all missing values were converted to np.nan
(Not-a-Number) and the operations were carried out with bn.nansum() and etc.

This attempt was also dropped after David's recommendation.


Pure NumPy
----------
The current state implements only a pure NumPy version of series.combine(),
renamed to series.combine_array() to avoid disturbing step5. However, step5
should also be calling the same series.combine_array() at a later
implementation.

The first step is to convert all the inputs to arrays.
>>> composite, weight, new, new_weight = map(np.asanyarray,
...                                 (composite, weight, new, new_weight))

Here we use np.asanyarray() instead of np.array, because it is faster if the
input is an array already, making the code more "generic".

The next step we reshape the arrays into months x years. The order='F' is
FORTRAN (column-major) order.

>>> size = composite.size
>>> shape = (12, size/12)
>>> composite, weight, new = map(lambda x: np.reshape(x, shape, order='F'),
...                                                  (composite, weight, new))

At this point the original code performs a loop over all months. In a second
inner loop over the elements of a month it checks for valid values of both
*composite* and *new* , if both are valid it calculates *sum_new* (Sum of data
in new), *sum* (Sum of data in composite), and *count* (Number of years where
both new and composite are valid.)

To compute all these without looping we must first get a mask where both
*composite* and *new* have missing points.
>>> new_mask = new == MISSING  # get *new* MISSING values
>>> comp_mask = composite == MISSING  # get composite missing values
>>> comp_mask[new_mask] = True  # get a common mask
>>> mask = ~comp_mask # mask[i] is True (1) when both *composite* and *new* are valid.

The variable *new_weight* became an array with zeros at invalid values after
this point,

>>> new_weight = new_weight * ~new_mask

we must check later how this implementation will affect step5.

Now *count*, *sum*, and *sum_new* is just:
>>> count = np.array([np.count_nonzero(mask[i,:]) for i in range(12)])
>>> sum = np.sum((composite * mask), axis=1)
>>> sum_new = np.sum((new * mask), axis=1)

Note 1: np.count_nonzero() does not have an axis keyword, hence the list
        comprehension there.
Note 2: The bottleneck module would be useless up to this part, since we still
        need to create the common mask.

After this step the original code checks if *count* is less than *min_overlap*,
there must be min_overlap of 20 months. If this statement is true the code
compute the *bias*. *bias* is computed using only the points where composite
and new are both valid.

Original code:
>>> bias = (sum-sum_new)/count  

NumPy array (this does not use *sum_new*:
>>> bias = np.nansum((composite - new) * mask, axis=1) / np.sum(mask, axis=1)

Since we did not checked for count < min_overlap, we now create a variable
*enough_months* 

>>> enough_months = count >= min_overlap

that is used to zero out the *new_count* that were updated even when *count*
was >= min_overlap. However, that still does not resolve the issue of updating
composite when *count < min_overlap*. This current implementation returns the
right *data_combined* but the wrong values from composite.

Now we can update *composite* and *new_weight*

>>> new_weight \*= enough_months[:,None]
>>> new_month_weight = weight + new_weight
>>> composite = (weight * composite + new_weight *
...                               (new + bias[:,None])) / new_month_weight

Here we get some zero divide at the points where both composite and new where
invalid. I believe it is safe to set them to zero.
>>> composite[np.isnan(composite)] = 0

and finally the *new_count*
>>> new_count = np.array([np.count_nonzero(composite[i,:]) for i in range(12)])

That ultimately became the *data_combine*,
>>> data_combined = (new_count * enough_months).tolist()

Conclusion
----------
The NumPy implementation did not speed-up the code a lot, actually it just
matches the version where we removed the functions call overhead by changing
the calls to invalid()/valid() to direct comparisons to  MISSING (9999.).

The computation of *data_combined* is correct, but it "returns" the wrong
*composite* and *weight* by modifying them wrongly, since we did not update
them iteratively when *count < min_overlap* like in the original code.

Future
------
#. Pad the series inside Series.series and make them a "reshaped array".
#. Fix the *composite* and *weight* modification.

References:
[1] http://mail.scipy.org/pipermail/numpy-discussion/2009-May/042425.html
[2] http://pypi.python.org/pypi/Bottleneck
NumPy.
