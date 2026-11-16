import sys, time
from PIL import Image
import part2, compose
part2.init()
times = [float(x) for x in sys.argv[1:]]
ims = []
for t in times:
    t0=time.time()
    im = compose.compose(2, part2, t, int(t*30))
    print(t, round(time.time()-t0,2))
    ims.append(im.resize((360,640)))
sheet = Image.new("RGB",(360*len(ims),640))
for i,im in enumerate(ims): sheet.paste(im,(i*360,0))
sheet.save("frames/p2_sheet_%s.png" % "_".join(str(int(x)) for x in times[:2]))
