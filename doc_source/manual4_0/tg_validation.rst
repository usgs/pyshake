.. _sec-validation-4:

****************************
Validation
****************************

The results produced by the ShakeMap **model** module are the product of
an interpolation scheme based on the statistics of multivariate
normal distributions (MVN). See :ref:`Worden et al. (2018) <worden2018>`
for a discussion of this approach. The mathematical complexity of 
the MVN process makes 
it difficult to ever fully validate the software against all possible 
inputs, or to even assert with certainty that any particular result is
objectively correct (at least once the inputs exceed some minimum 
level of complexity). Here, we discuss a set of simplified validation
tests that provide some support for the belief that the software is
producing correct results that are consistent with our intuition. These 
tests
are not designed to fully test all of the features of the software --
that job is left to our unit tests and integration tests. Here we make
numerous simplifications in order to more easily interpret the results.

While the tests discussed in this section are one-dimensional (i.e.,
the results are computed for a line along which the sources are located), 
the computational process is agnostic to dimensionality and is only 
concerned
with the distances between locations. Again, out other testing considers
more complex models, and the results of those tests appear consistent
with the results presented here.

Various simplifying assumptions were made when producing these tests 
in order to better illuminate the behavior of the MVN process itself. 
In particular, the ground-motion prediction equation (GMPE) used
in these tests always returns 0 (in log space) for all locations, 
and reports a between-event standard deviation of 0.6 and a 
within-event standard deviation of 0.8 (making the total 
standard deviation a convenient 1.0). In addition, the 
cross-correlation function employed in these tests returns the product 
of the ratio of the
spectral periods (that is, ``Ts/Tl`` where ``Ts`` is the smaller period 
and ``Tl`` is the larger) and ``exp(-h/10)``, in which ``h`` is the 
separation distance. This model, while not the result of an empirical 
study, provides a smoother, more predictable behavior than other models
found in the literature and implemented in ShakeMap.

The validation tests may be run from the ShakeMap *bin* directory with 
the command **run_validation**. The command will run the tests and then
attempt to open a window displaying the plots. This last step might 
not work on all systems. The plots can be found in
*tests/data/eventdata/validation_test_XXXX/current/products* (where
"*XXXX*" is the number of the test).

Test 0001
====================

:num:`Figure #validation-test-one` shows the results of Test 0001. This
test places two observation points along a line. 
As discussed above, the GMPE evaluates to 0 (in log units) everywhere.  
Each observation in this test also has an amplitude of 0.0 (in log units), 
so the computed bias of the event is 0.
Thus, the conditional mean amplitude evaluates to 0 everywhere. The standard 
deviation is 0 at the location of the observations, and at great distances
from the observations it asymptotes to a value somewhat less than 1 (but
still greater than the GMPE's within-event standard deviaiton of 0.8). 
These are the expected results, and provide some confidence that the
MVN implementation is not introducing a bias or other anomalies.


.. _validation-test-one:

.. figure:: _static/validation_test_0001_PGA.*
   :width: 700
   :align: left

   Validation Test 0001. Two observations along a line have 
   amplitudes of 0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.


Test 0002
====================

Test 0002 is shown in :num:`Figure #validation-test-two`. In this test,
one observation has an amplitude of +1.0, the other is --1.0. Because of
the offsetting observations, the bias is again 0. The figure shows that
the conditional amplitudes reach the expected value (+/-- 1.0) at the 
observation points, and approach 0 at distances far from the 
observations. As with Test 0001, the standard deviation is 0 at 
the observations and reaches a maximum somewhere between 0.8 and 1.0
at great distance from the observations.


.. _validation-test-two:

.. figure:: _static/validation_test_0002_PGA.*
   :width: 700
   :align: left

   Validation Test 0002. Two observations along a line have 
   amplitudes of +1.0 and --1.0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.

Test 0003
====================

Validation Test 0003 has a single observation with an amplitude of +1.0
along a line (see :num:`Figure #validation-test-three`). Given the GMPE 
within-event standard deviation of 0.8 and
the between-event standard deviation of 0.6 (and mean of 0), the bias
is 0.36, as expected (see equation 11 in 
:ref:`Worden et al. (2018) <worden2018>`). Thus, the ground motion 
approaches this value at distance from the observation. The 
standard deviation of the bias is 0.48, also as expected (see equation
12 of :ref:`Worden et al. (2018) <worden2018>`). This result means 
that the conditional
standard deviation at great distance from an observation will be 
about 0.93, as seen in :num:`Figure #validation-test-three`. 


.. _validation-test-three:

.. figure:: _static/validation_test_0003_PGA.*
   :width: 700
   :align: left

   Validation Test 0003. A single observation along a line with 
   an amplitude of +1.0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.

Test 0004
====================

Test 0004 uses an identical set up to Test 0003, except there
are two observations (of amplitude +1.0) at the same location.
Because the observations are co-located and of the same period,
their correlation is 1.0. This means that they will have the
effect of a single observation. The result, illustrated in
:num:`Figure #validation-test-four` confirms this. Note that
:num:`Figure #validation-test-four` (which has two observations)
is identical to :num:`Figure #validation-test-three` (which
has only one observation).


.. _validation-test-four:

.. figure:: _static/validation_test_0004_PGA.*
   :width: 700
   :align: left

   Validation Test 0004. Two observations at the same 
   location along a line, both with 
   amplitudes of +1.0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation. Compare with :num:`Figure #validation-test-three`.


Test 0005
====================

Test 0005 also has two co-located observations (see Validation
Test 0004, above), but here they have
opposite amplitudes of +1.0 and --1.0. The result, shown in
:num:`figure #validation-test-five`, is that the conditional mean
and standard deviation behave as if there were only a single
observation with the mean amplitude of the two observations (i.e.,
0).


.. _validation-test-five:

.. figure:: _static/validation_test_0005_PGA.*
   :width: 700
   :align: left

   Validation Test 0005. Two observations at the same 
   location along a line, with amplitudes of +1.0 and --1.0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.


Test 0006
====================

:num:`Figure #validation-test-six` illustrates Validation Test 0006. 
Forty evenly-spaced observations, all with amplitudes of +1.0 are used. 
Most of the observations are to the left of center of the plot (and
extend some ways off the left edge of the plot). Here we note that 
the bias has moved significantly toward the mean of the data (as 
compared with a single observation as in 
:num:`Figure #validation-test-three`), and the conditional
standard deviation at distance has decreased toward the within-event
value of 0.8.


.. _validation-test-six:

.. figure:: _static/validation_test_0006_PGA.*
   :width: 700
   :align: left

   Validation Test 0006. Forty evenly-space observations along 
   a line, with amplitudes of +1.0 (note that the observations
   extend some distance off the left edge of the figure).
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.

Test 0007
====================

Validation Test 0007 uses a single observation with an amplitude
of +1.0. The observation is of spectral acceleration (SA) at a 
period of 1.0 s. The conditional mean SA was 
conputed for the location of the observation at a variety of 
periods ranging from 0.1 s to 10.0
s. A separate bias is computed for each period, and the
correlation between the observation and the amplitude being
computed decreases as the ratio of the two periods decreases,
thus the amplitude tends toward zero as the ratio of the periods
decreases. At periods far from the observation period, the 
bias approaches 0 and its standard deviation approaches the
between-event standard deviation, thus the conditional standard
deviation approaches the combined between-event and within-event
standard deviation (which, in our tests is 1.0).


.. _validation-test-seven:

.. figure:: _static/validation_test_0007_spectra_plot.*
   :width: 700
   :align: left

   Validation Test 0007. A single observation of spectral
   acceleration (with an amplitude of 1.0) at a period of
   1.0 s, and the conditional spectral acceleration
   at periods from 0.1 s to 10.0 s.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.

Test 0008
====================

Validation Test 0008 has a single observation with an amplitude of 1.0,
as in Test 0003, however the point is given a non-zero uncertainty.
In this case the stanard deviation is 0.5 (in natural log units). Thus,
in :num:`Figure #validation-test-eight` we see the maximum amplitude 
is somewhat lesss than 1.0 (0.84472) and the minimum standard deviation 
is somewhat 
less than 0.5 (0.44212, to be exact, which is less than the lesser 
of 0.5 and 0.8, the standard deviations 
of the observation and the prediction, respectively). See Equations 42
and 43 of :ref:`Worden et al. (2018) <worden2018>`) for additional
discussion. Note also that the bias (0.28800) is less than that of
Test 0003, and the maximum uncertainty (0.94674) is greater. These
features are consistent with the uncertainty of the observation and
with the findings of :ref:`Worden et al. (2018) <worden2018>`.
:num:`Figure #validation-test-eight` may be compared with 
:num:`Figure #validation-test-three`.


.. _validation-test-eight:

.. figure:: _static/validation_test_0008_PGA.*
   :width: 700
   :align: left

   Validation Test 0008. A single observation with an
   amplitude of +1.0, and a standard deviation of 0.5.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation. Compare with :num:`Figure #validation-test-three`.

Test 0009
====================

Test 0009 (see :num:`Figure #validation-test-nine`) has a single 
observation with an amplitude of 1.0, as with Test 0008, but here
the standard deviation of the observation is 10.0. This large 
uncertainty ('large' relative to the GMPE's within-event standard
deviation of 0.8) causes the observation to be downweighted to the 
point that it has very little effect on the conditional mean and 
standard deviation. Despite the downweighting, the conditional 
standard deviation is still somewhat less than 1.0 at the location
of the observation, as expected.


.. _validation-test-nine:

.. figure:: _static/validation_test_0009_PGA.*
   :width: 700
   :align: left

   Validation Test 0009. A single observation with an
   amplitude of +1.0, and a standard deviation of 10.0.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation. Compare with :num:`Figure #validation-test-three`
   and :num:`Figure #validation-test-eight`.

Test 0010
====================

As with Tests 0008 and  0009, Test 0010 (see 
:num:`Figure #validation-test-ten`) has a single observation
with an amplitude of 1.0, but here the standard deviation of the 
observation is a small value (0.05), relative to the GMPE's 
intra-event standard deviation. In this case, we see that the
values of the bias and conditional mean and standard deviation are
almost the same as in Test 0003, in which the standard deviation
of the observation was 0. 


.. _validation-test-ten:

.. figure:: _static/validation_test_0010_PGA.*
   :width: 700
   :align: left

   Validation Test 0010. A single observation with an
   amplitude of +1.0, and a standard deviation of 0.05.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation. Compare with :num:`Figure #validation-test-three`,
   :num:`Figure #validation-test-eight`, and 
   :num:`Figure #validation-test-nine`.

Test 0011
====================

Test 0011 (see 
:num:`Figure #validation-test-eleven`) has five observations:
the central observation has an amplitude of 0.75, while the 
other four observations have amplitudes of 1.0. All five have 
a standard 
deviation of 0.2. The spacing of the higher amplitudes was 
chosen to exert a strong influence on the amplitude at the 
location of the central observation,
but despite that influence its conditional mean should approach 
the observational amplitude (0.75) from below, but not reach or 
exceed it.


.. _validation-test-eleven:

.. figure:: _static/validation_test_0011_PGA.*
   :width: 700
   :align: left

   Validation Test 0011. Five observations: the central
   observation has an amplitude of 0.75, while the other
   four have amplitudes of 1.0. All five observations have
   a standard deviation of 0.2.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation.

Test 0012
====================

Like Test 0011, Test 0012 (see 
:num:`Figure #validation-test-twelve`) has five observations:
the central observation has an amplitude of 0.75, while the 
other four observations have amplitudes of 1.0. All five have 
a standard 
deviation of 0.2. Here, though, he spacing of the higher 
amplitudes was chosen so that the conditional amplitude at 
the location of
the central observation would approach the assigned amplitude
from above. The amplitude should not (quite) reach the 
observational value (0.75), or go below it.


.. _validation-test-twelve:

.. figure:: _static/validation_test_0012_PGA.*
   :width: 700
   :align: left

   Validation Test 0012. Five observations: the central
   observation has an amplitude of 0.75, while the other
   four have amplitudes of 1.0. All five observations have
   a standard deviation of 0.2.
   The black line shows the conditional mean, the blue lines
   show the conditional mean +/-- the conditional standard
   deviation, and the red line shows the conditional standard
   deviation. Compare with :num:`Figure #validation-test-eleven`.
