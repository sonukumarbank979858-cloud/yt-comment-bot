"""Smart Exam Academy style thumbnail: navy board, yellow channel name, red badge,
big Hindi headline, bullet points, AI illustration on the right, Like/Share/Subscribe strip."""
import io, os, json, time, base64, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D=os.path.dirname(os.path.abspath(__file__))
F=lambda n,s: ImageFont.truetype(os.path.join(D,"fonts",n),s,layout_engine=ImageFont.Layout.RAQM)
W,H=1280,720

def ai_image(prompt, key=None):
    """Try Gemini image models first (needs API credits), then free Pollinations."""
    if key:
        for m in ["gemini-3.1-flash-image","gemini-2.5-flash-image","gemini-3.1-flash-lite-image"]:
            try:
                r=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
                  data=json.dumps({"contents":[{"parts":[{"text":prompt+". Square illustration, no text, no letters, no watermark."}]}],
                  "generationConfig":{"responseModalities":["IMAGE"],"imageConfig":{"aspectRatio":"1:1"}}}).encode(),headers={"Content-Type":"application/json"})
                j=json.load(urllib.request.urlopen(r,timeout=120))
                for p in j["candidates"][0]["content"]["parts"]:
                    if "inlineData" in p: print("img gemini",m); return Image.open(io.BytesIO(base64.b64decode(p["inlineData"]["data"]))).convert("RGB")
            except Exception as e: print("img",m,str(e)[:60])
    q=urllib.parse.quote(prompt+", detailed digital painting, vibrant, no text")
    for i in range(6):
        for mdl in ["flux","turbo"]:
            try:
                b=urllib.request.urlopen(f"https://image.pollinations.ai/prompt/{q}?width=768&height=768&nologo=true&model={mdl}&seed={int(time.time())%9999}",timeout=120).read()
                im=Image.open(io.BytesIO(b)).convert("RGB"); print("img pollinations",mdl); return im
            except Exception as e: print("pollinations",mdl,str(e)[:60]); time.sleep(48)
    return None

def wrap(d,text,font,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t,font=font)<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def rr(d,box,r,fill=None,outline=None,width=1): d.rounded_rectangle(box,r,fill=fill,outline=outline,width=width)

def make(info, art=None):
    """info: badge, headline, sub, points[list], corner"""
    im=Image.new("RGB",(W,H))
    g=ImageDraw.Draw(im)
    for y in range(H):  # navy gradient
        t=y/H; g.line([(0,y),(W,y)],fill=(int(14+10*t),int(28+12*t),int(78-20*t)))
    d=ImageDraw.Draw(im)
    rr(d,(10,10,W-10,H-10),28,outline=(36,70,150),width=4)
    # header
    d.text((40,26),"Smart Exam Academy",font=F("Hind-Bold.ttf",40),fill=(255,205,40))
    bf=F("Hind-Bold.ttf",28); badge=info.get("badge","")[:40]
    if badge:
        x0=40+d.textlength("Smart Exam Academy",font=F("Hind-Bold.ttf",40))+20; bw=d.textlength(badge,font=bf)+36
        rr(d,(x0,30,x0+bw,74),22,fill=(220,38,38)); d.text((x0+18,32),badge,font=bf,fill="white")
    corner=info.get("corner","")[:22]
    if corner:
        cf=F("Hind-Bold.ttf",28); d.text((W-40-d.textlength(corner,font=cf),32),corner,font=cf,fill="white")
    # right art panel
    px0,py0,px1,py1=820,110,1240,560
    if art:
        a=art.copy(); a=a.crop((0,0,a.width,int(a.height*0.93))); s=max((px1-px0)/a.width,(py1-py0)/a.height); a=a.resize((int(a.width*s)+1,int(a.height*s)+1))
        l=(a.width-(px1-px0))//2; tp=(a.height-(py1-py0))//2; a=a.crop((l,tp,l+px1-px0,tp+py1-py0))
        m=Image.new("L",a.size,0); ImageDraw.Draw(m).rounded_rectangle((0,0,a.width-1,a.height-1),24,fill=255)
        im.paste(a,(px0,py0),m)
    rr(d,(px0,py0,px1,py1),24,outline=(255,205,40),width=5)
    # headline
    maxw=740; size=86
    head=info.get("headline","")
    while size>46:
        hf=F("Mukta-ExtraBold.ttf",size); lines=wrap(d,head,hf,maxw)
        if len(lines)<=2: break
        size-=6
    y=110
    for i,l in enumerate(lines[:3]):
        d.text((44+3,y+3),l,font=hf,fill=(0,0,0)); d.text((44,y),l,font=hf,fill=(255,214,10) if i==0 else "white"); y+=int(size*1.12)
    y+=12
    sub=info.get("sub","")
    if sub:
        sf=F("Hind-Bold.ttf",36); sl=wrap(d,sub,sf,maxw)[:1]
        if sl:
            sw=d.textlength(sl[0],font=sf)+40; rr(d,(40,y+8,40+sw,y+62),14,fill=(22,163,74)); d.text((60,y+10),sl[0],font=sf,fill="white"); y+=82
    pf=F("Hind-SemiBold.ttf",32)
    for p in info.get("points",[])[:4]:
        if y>560: break
        l=wrap(d,p,pf,maxw-50)[:1]
        if not l: continue
        d.ellipse((46,y+14,66,y+34),fill=(255,205,40)); d.text((80,y),l[0],font=pf,fill=(230,236,255)); y+=50
    # bottom strip
    rr(d,(40,600,W-40,672),20,fill=(15,23,60),outline=(36,70,150),width=2)
    ff=F("Hind-Bold.ttf",32)
    items=info.get("footer") or ["संपूर्ण व्याख्या","महत्वपूर्ण प्रश्न","परीक्षा उपयोगी"]
    tot=sum(d.textlength(t,font=ff)+50 for t in items)+60*(len(items)-1); x=(W-tot)/2
    for i,t in enumerate(items):
        d.ellipse((x,618,x+36,654),fill=(22,163,74)); d.line([(x+9,636),(x+16,644),(x+28,627)],fill="white",width=5)
        d.text((x+50,612),t,font=ff,fill="white"); x+=d.textlength(t,font=ff)+50
        if i<len(items)-1: d.text((x+22,612),"|",font=ff,fill=(120,140,200)); x+=60
    d.text((W-300,684),"Like • Share • Subscribe",font=F("Hind-SemiBold.ttf",22),fill=(200,210,240))
    out=io.BytesIO(); im.save(out,"JPEG",quality=90); return out.getvalue()

if __name__=="__main__":
    art=Image.open(os.path.join(D,"test_art.jpg")) if os.path.exists(os.path.join(D,"test_art.jpg")) else None
    open("/tmp/t.jpg","wb").write(make({"badge":"BA 1st Semester • हिंदी","corner":"LNMU 2026","headline":"स्वामी रामानंद के शिष्य","sub":"भक्तिकाल MCQ","points":["कबीर, रैदास, पीपा कौन थे?","राम-कृष्ण काव्य","PYQ आधारित 50 प्रश्न"]},art))
