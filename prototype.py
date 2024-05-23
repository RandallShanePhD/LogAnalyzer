import csv
import numpy as np
from sktime.clustering.dbscan import TimeSeriesDBSCAN
from sktime.dists_kernels import FlatDist, ScipyDist

# PROTOTYPING ONLY - NOT implemented in operations


X = np.array(model_data)
eucl_dist = FlatDist(ScipyDist())
clst = TimeSeriesDBSCAN(distance=eucl_dist, eps=2)
clst.fit(X)

clst.get_fitted_params()
output = clst.get_fitted_params()
# clustered_data = [["date", "time", "lat", "lon", "alt", "heading", "indicator", "cluster"]]
clustered_data = [["datetime", "alt", "climb_sink", "indicator", "cluster"]]
for i, entry in enumerate(model_data):
    indicator = "G"
    try:
        if entry[1] < model_data[i - 1][1]:
            indicator = "S"
        elif entry[1] > model_data[i - 1][1]:
            indicator = "C"
    except:
        pass
    entry.append(indicator)
    entry.append(output['dbscan__labels'][i])
    clustered_data.append(entry)


with open('prototype.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerows(clustered_data)

""" 
No success! 
Attempted to restructure data - clustering no bueno!!
"""
