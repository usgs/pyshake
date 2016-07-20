import numpy as np


class GodaAtkinson2010(object):
    def getSpatialCorrelation(self, dists, imt):
        """
        Put some documentation here
        """
        if 'PGA' in imt:
            alpha = 0.060
            beta  = 0.283
            gamma = 5.0
        elif 'PGV' in imt:
            # Here we use the average values because there is no PGV in G&A
            alpha = 0.054
            beta  = 0.319
            gamma = 5.0
        elif 'SA' in imt:
            pp = imt.period
            if pp == 0.1:
                alpha = 0.062
                beta  = 0.276
                gamma = 5.0
            elif pp == 0.2:
                alpha = 0.073
                beta  = 0.248
                gamma = 5.0
            elif pp == 0.3:
                alpha = 0.086
                beta  = 0.219
                gamma = 5.0
            elif pp == 0.5:
                alpha = 0.073
                beta  = 0.248
                gamma = 5.0
            elif pp == 1.0:
                alpha = 0.051
                beta  = 0.329
                gamma = 5.0
            elif pp == 2.0:
                alpha = 0.061
                beta  = 0.421
                gamma = 3.035
            elif pp == 3.0:
                alpha = 0.092
                beta  = 0.671
                gamma = 1.189
            elif pp == 5.0:
                alpha = 0.071
                beta  = 0.741
                gamma = 1.201
            else:
                # Here we use the average values because we don't have terms for
                # this period
                alpha = 0.054
                beta  = 0.319
                gamma = 5.0
        else:
            # Again we use the average values because we don't know the IMT
            alpha = 0.054
            beta  = 0.319
            gamma = 5.0
            pass
        return np.sqrt(1.0 - np.max(gamma *
            np.exp(-1.0 * alpha * np.power(dists, beta)) - gamma + 1, 0))

