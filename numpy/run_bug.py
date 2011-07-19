from CCCgistemp.code import eqarea
from CCCgistemp.code import earth
from CCCgistemp.code import giss_data
from CCCgistemp.code import parameters
from CCCgistemp.code import series
from CCCgistemp.code.giss_data import MISSING, valid

from CCCgistemp.tool import gio
from CCCgistemp.code import step3

# Rural station data for step3.
# http://code.google.com/p/ccc-gistemp/downloads/detail?name=v2.longrural-20100802&can=2&q=#makechanges
#data = gio.GHCNV2Reader('work/v2.longrural-20100802', meta=gio.v2meta())

# Modified step2.v2.
records = gio.GHCNV2Reader("work/step2.v2", meta=gio.v2meta())

"""
iter_subbox_grid
"""
radius=1200.0
max_months=1584
box_source = step3.iter_subbox_grid(records, 1584, 1880, radius=radius)
list(box_source)

arc = radius / earth.radius
regions = list(eqarea.gridsub())
region = regions[0]
box, subboxes_l = region[0], list(region[1])
subboxes = np.asanyarray(subboxes_l)

step3.sort(station_records, lambda x,y: y.good_count - x.good_count)

result = step3.step3(records)
list(gio.step3_output(result))


for k in range(len(regions)):
    region = regions[k]
    box, subboxes = region[0], list(region[1])
    subboxes_array = np.asanyarray(subboxes)
    n_empty_cells = 0
    for i in range(len(subboxes)):
        subbox = subboxes[i]
        centre = eqarea.centre(subbox)
        contributors = list(step3.incircle(station_records, arc, *centre))
        if contributors:
            print i, k
#i, k = 0, 8