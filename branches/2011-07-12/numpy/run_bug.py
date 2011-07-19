from CCCgistemp.tool import gio
from CCCgistemp.code import step3

#01
#data = gio.GHCNV2Reader('work/v2.longrural-20100802', meta=gio.v2meta())
data = gio.GHCNV2Reader("work/step2.v2", meta=gio.v2meta())
result = step3.step3(data)
list(gio.step3_output(result))