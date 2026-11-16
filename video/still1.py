import sys, time
from PIL import Image
import part1, compose
part1.init()
times = [float(x) for x in sys.argv[1:]]
ims = []
for t in times:
    t0=time.time()
    im = compose.compose(1, part1, t, int(t*30))
    print(t, round(time.time()-t0,2))
    ims.append(im.resize((360,640)))
sheet = Image.new("RGB",(360*len(ims),640))
for i,im in enumerate(ims): sheet.paste(im,(i*360,0))
sheet.save("frames/p1_sheet_%s.png" % "_".join(str(int(x)) for x in times[:2]))
