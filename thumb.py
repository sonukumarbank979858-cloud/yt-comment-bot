"""Smart Exam Academy thumbnail v2 - matches the channel's style:
dark blue glow, red top banner, huge yellow-orange subject, yellow chapter pill,
maroon topic pill, white checklist card left, art + fact card right, red bottom bar."""
import io, os, json, time, base64, random, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
D=os.path.dirname(os.path.abspath(__file__))
def F(n,s): return ImageFont.truetype(os.path.join(D,"fonts",n),s,layout_engine=ImageFont.Layout.RAQM)
B="Mukta-ExtraBold.ttf"; HB="Hind-Bold.ttf"; HS="Hind-SemiBold.ttf"
W,H=1280,720
STYLE_REFS=[os.path.join(D,"style",f) for f in ("ref1.jpg","ref2.jpg","ref3.jpg")]

def _gem(key,parts,aspect="16:9"):
    for m in ["gemini-3-pro-image","gemini-3.1-flash-image","gemini-2.5-flash-image"]:
        try:
            r=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
              data=json.dumps({"contents":[{"parts":parts}],"generationConfig":{"responseModalities":["IMAGE"],"imageConfig":{"aspectRatio":aspect}}}).encode(),
              headers={"Content-Type":"application/json"})
            j=json.load(urllib.request.urlopen(r,timeout=180))
            for p in j["candidates"][0]["content"]["parts"]:
                if "inlineData" in p: print("img gemini",m); return Image.open(io.BytesIO(base64.b64decode(p["inlineData"]["data"]))).convert("RGB")
        except Exception as e: print("img",m,str(e)[:50])
    return None

def gemini_full(key,info):
    """Whole thumbnail by Gemini image model, copying the channel's reference style. Needs API credits."""
    if not key: return None
    parts=[]
    for f in STYLE_REFS:
        if os.path.exists(f): parts.append({"inline_data":{"mime_type":"image/jpeg","data":base64.b64encode(open(f,"rb").read()).decode()}})
    txt=("ऊपर दिए Smart Exam Academy के thumbnails जैसी ही शैली में (गहरा नीला चमकदार background, ऊपर लाल banner, बड़ा पीला-नारंगी शीर्षक, "
         "पीला अध्याय pill, लाल-मैरून विषय pill, बाएँ सफ़ेद checklist card लाल ✔ के साथ, दाएँ विषय से जुड़ा चित्र और सूत्र/तथ्य card, नीचे लाल पट्टी में 3 हरे ✔) "
         "एक नया 16:9 YouTube thumbnail बनाओ। सारे हिंदी शब्द बिल्कुल सही वर्तनी में साफ़ लिखो। सामग्री: "+json.dumps(info,ensure_ascii=False))
    parts.append({"text":txt})
    im=_gem(key,parts)
    return im.resize((W,H)) if im else None

def ai_image(prompt, key=None):
    if key:
        im=_gem(key,[{"text":prompt+". Vibrant illustration for an Indian education YouTube thumbnail, dark blue background, no text, no letters."}],"1:1")
        if im: return im
    q=urllib.parse.quote(prompt+", vibrant detailed digital illustration, dark blue background, no text")
    for i in range(5):
        for mdl in ["flux","turbo"]:
            try:
                b=urllib.request.urlopen(f"https://image.pollinations.ai/prompt/{q}?width=768&height=768&nologo=true&model={mdl}&seed={random.randint(1,9999)}",timeout=120).read()
                im=Image.open(io.BytesIO(b)).convert("RGB"); print("img pollinations",mdl); return im
            except Exception as e: print("pollinations",mdl,str(e)[:50]); time.sleep(47)
    return None

def fit(d,text,font_name,maxw,start,minsize=20):
    s=start
    while s>minsize:
        f=F(font_name,s)
        if d.textlength(text,font=f)<=maxw: return f
        s-=4
    return F(font_name,minsize)

def pill(im,box,fill,outline=None,ow=4,r=None,grad=None):
    x0,y0,x1,y1=box; r=r or (y1-y0)//2
    sh=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle((x0+4,y0+6,x1+4,y1+6),r,fill=(0,0,0,140))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    layer=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(layer)
    if grad:
        g=Image.new("RGBA",(x1-x0,y1-y0)); gd=ImageDraw.Draw(g)
        for y in range(y1-y0):
            t=y/(y1-y0); c=tuple(int(grad[0][i]*(1-t)+grad[1][i]*t) for i in range(3))
            gd.line([(0,y),(x1-x0,y)],fill=c+(255,))
        m=Image.new("L",g.size,0); ImageDraw.Draw(m).rounded_rectangle((0,0,g.width-1,g.height-1),r,fill=255)
        layer.paste(g,(x0,y0),m)
    else: d.rounded_rectangle(box,r,fill=fill)
    if outline: d.rounded_rectangle(box,r,outline=outline,width=ow)
    im.alpha_composite(layer)

def ctext(im,cx,y,text,font,fill="white",stroke=0,sc=(0,0,0),grad=None,shadow=True):
    d=ImageDraw.Draw(im); w=d.textlength(text,font=font); x=int(cx-w/2)
    if shadow:
        sh=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(sh).text((x+5,y+6),text,font=font,fill=(0,0,0,170),stroke_width=stroke,stroke_fill=(0,0,0,170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    if grad:
        d.text((x,y),text,font=font,fill=sc,stroke_width=stroke,stroke_fill=sc)
        m=Image.new("L",im.size,0); ImageDraw.Draw(m).text((x,y),text,font=font,fill=255)
        bb=m.getbbox() or (0,0,1,1); g=Image.new("RGBA",im.size,(0,0,0,0)); gd=ImageDraw.Draw(g)
        for yy in range(bb[1],bb[3]+1):
            t=(yy-bb[1])/max(1,bb[3]-bb[1]); c=tuple(int(grad[0][i]*(1-t)+grad[1][i]*t) for i in range(3))
            gd.line([(bb[0],yy),(bb[2],yy)],fill=c+(255,))
        im.paste(g,(0,0),m)
    else: d.text((x,y),text,font=font,fill=fill,stroke_width=stroke,stroke_fill=sc)
    return w

def check(d,x,y,s,color=(220,38,38),box=True):
    if box: d.rounded_rectangle((x,y,x+s,y+s),5,outline=color,width=3)
    d.line([(x+s*0.2,y+s*0.5),(x+s*0.42,y+s*0.75),(x+s*0.95,y-s*0.05)],fill=color,width=max(4,s//6))

def gcheck(d,x,y,s):
    d.ellipse((x,y,x+s,y+s),fill=(22,163,74),outline="white",width=3)
    d.line([(x+s*0.25,y+s*0.52),(x+s*0.43,y+s*0.72),(x+s*0.77,y+s*0.32)],fill="white",width=max(4,s//7))

def background():
    im=Image.new("RGBA",(W,H),(4,10,40,255))
    g=Image.new("L",(W,H),0); gd=ImageDraw.Draw(g)
    gd.ellipse((260,40,1020,620),fill=255); g=g.filter(ImageFilter.GaussianBlur(160))
    glow=Image.new("RGBA",(W,H),(30,80,200,255)); im=Image.composite(glow,im,g).convert("RGBA")
    d=ImageDraw.Draw(im); rnd=random.Random(7)
    for _ in range(140):
        x,y=rnd.randint(0,W),rnd.randint(0,H); r=rnd.choice([1,1,1,2]); d.ellipse((x,y,x+r,y+r),fill=(200,220,255,rnd.randint(90,220)))
    return im

def soft_art(art,box):
    x0,y0,x1,y1=box; a=art.convert("RGB"); a=a.crop((0,0,a.width,int(a.height*0.94)))
    s=max((x1-x0)/a.width,(y1-y0)/a.height); a=a.resize((int(a.width*s)+1,int(a.height*s)+1))
    l=(a.width-(x1-x0))//2; t=(a.height-(y1-y0))//2; a=a.crop((l,t,l+x1-x0,t+y1-y0)).convert("RGBA")
    m=Image.new("L",a.size,0); ImageDraw.Draw(m).ellipse((10,10,a.width-10,a.height-10),fill=255); m=m.filter(ImageFilter.GaussianBlur(28))
    a.putalpha(m); return a

def make(info, art=None, logo=None):
    """info keys: top, subject, subject_en, chapter, topic, topic_en, checklist[], fact_title, facts[], footer[3]"""
    im=background(); d=ImageDraw.Draw(im)
    # right art
    if art: im.alpha_composite(soft_art(art,(930,70,1280,420)),(930,70))
    # logo
    if logo:
        lg=logo.convert("RGBA").resize((118,118)); m=Image.new("L",(118,118),0); ImageDraw.Draw(m).ellipse((0,0,117,117),fill=255)
        d.ellipse((16,10,140,134),fill="white"); im.paste(lg,(19,13),m)
    else:
        d.ellipse((16,10,140,134),fill="white")
        for i,t in enumerate(["Smart","Exam","Academy"]): ctext(im,78,32+i*26,t,F(HB,24),fill=(10,20,60),shadow=False)
    d=ImageDraw.Draw(im)
    # top banner
    top=info.get("top") or "सभी शैक्षिक एवं प्रतियोगी परीक्षाओं के लिए"
    tf=fit(d,top,HB,700,40); tw=d.textlength(top,font=tf); cx=640
    pill(im,(int(cx-tw/2-34),12,int(cx+tw/2+34),74),None,outline=(255,200,60),ow=4,grad=((200,20,30),(120,5,15)))
    ctext(im,cx,14,top,tf,fill="white")
    # subject headline
    subj=info.get("subject",""); se=info.get("subject_en","")
    hf=fit(d,subj,B,480 if se else 600,124,64)
    sw=d.textlength(subj,font=hf); sew=0
    if se:
        sef=fit(d,"("+se+")",HB,200,46); sew=d.textlength("("+se+")",font=sef)+30
    x_s=cx-(sw+sew)/2+sw/2
    ctext(im,x_s,62,subj,hf,stroke=7,sc=(110,20,10),grad=((255,236,90),(255,130,20)))
    if se:
        px=int(x_s+sw/2+12); pill(im,(px,128,int(px+sew),186),(255,255,255),outline=(220,38,38),ow=3)
        ctext(im,px+sew/2,130,"("+se+")",sef,fill=(200,20,30),shadow=False)
    # chapter pill
    ch=info.get("chapter","")
    if ch:
        cf=fit(d,ch,HB,300,50); cw=d.textlength(ch,font=cf)
        pill(im,(int(cx-cw/2-40),222,int(cx+cw/2+40),286),None,outline=(160,90,0),ow=3,grad=((255,236,120),(245,170,20)))
        ctext(im,cx,224,ch,cf,fill=(40,15,5),shadow=False)
    # topic pill
    tp=info.get("topic",""); tpf=fit(d,tp,B,540,110,48); tpw=d.textlength(tp,font=tpf)
    pill(im,(int(cx-tpw/2-46),300,int(cx+tpw/2+46),436),None,outline=(255,190,60),ow=5,r=40,grad=((120,10,20),(40,0,10)))
    ctext(im,cx,300+(136-tpf.size*1.35)/2,tp,tpf,fill="white",stroke=3,sc=(60,0,0))
    te=info.get("topic_en","")
    if te:
        tef=fit(d,"("+te+")",HB,420,46); tew=d.textlength("("+te+")",font=tef)
        pill(im,(int(cx-tew/2-30),448,int(cx+tew/2+30),506),(255,255,255),outline=(220,38,38),ow=3)
        ctext(im,cx,450,"("+te+")",tef,fill=(200,20,30),shadow=False)
    d=ImageDraw.Draw(im)
    # left checklist card
    items=[x for x in info.get("checklist",[]) if x][:8]
    if items:
        step=min(54,int(420/len(items))); bottom=min(592,166+step*len(items)+10)
        pill(im,(14,150,330,bottom),(250,250,255),outline=(255,200,60),ow=4,r=22)
        d=ImageDraw.Draw(im); y=166
        for it in items:
            f=fit(d,it,HS,250,32,18); check(d,30,y+8,26)
            d.text((66,y),it,font=f,fill=(15,25,70)); y+=step
            if it is not items[-1]: d.line([(30,y-6),(314,y-6)],fill=(200,205,230),width=1)
    # right fact card
    facts=[x for x in info.get("facts",[]) if x][:4]
    if facts:
        pill(im,(960,420,1266,592),(255,253,240),outline=(34,139,34),ow=4,r=22)
        d=ImageDraw.Draw(im); ft=info.get("fact_title","महत्वपूर्ण तथ्य")
        tf2=fit(d,ft,HB,260,30); ftw=d.textlength(ft,font=tf2)
        pill(im,(int(1113-ftw/2-18),404,int(1113+ftw/2+18),446),None,grad=((110,30,160),(70,10,110)))
        ctext(im,1113,404,ft,tf2,fill="white",shadow=False)
        d=ImageDraw.Draw(im); y=456; step=min(44,int(130/len(facts)))
        for i,fx in enumerate(facts):
            f=fit(d,fx,HB,280,32,18); ctext(im,1113,y,fx,f,fill=(15,25,90) if i%2==0 else (200,20,30),shadow=False); y+=step
    # bottom bar
    pill(im,(30,612,1250,700),None,outline=(255,200,60),ow=4,r=30,grad=((200,20,30),(110,5,15)))
    d=ImageDraw.Draw(im)
    foot=(info.get("footer") or ["संपूर्ण थ्योरी","महत्वपूर्ण सूत्र","MCQ + PYQ"])[:3]
    ff=F(HB,40); tot=sum(d.textlength(t,font=ff)+64 for t in foot)+70*(len(foot)-1); x=(W-tot)/2
    for i,t in enumerate(foot):
        gcheck(d,int(x),628,52); d.text((x+64,620),t,font=ff,fill="white"); x+=d.textlength(t,font=ff)+64
        if i<len(foot)-1: d.text((x+26,618),"|",font=ff,fill=(255,220,120)); x+=70
    out=io.BytesIO(); im.convert("RGB").save(out,"JPEG",quality=92); return out.getvalue()

def build(info,key=None,logo=None):
    im=gemini_full(key,info)
    if im:
        out=io.BytesIO(); im.convert("RGB").save(out,"JPEG",quality=92); return out.getvalue(),"gemini"
    art=ai_image(info.get("image_prompt") or info.get("topic_en") or info.get("topic",""),None)
    return make(info,art,logo),("template+art" if art else "template")

if __name__=="__main__":
    art=Image.open("/workspace/work/pol.jpg") if os.path.exists("/workspace/work/pol.jpg") else None
    open("/tmp/t.jpg","wb").write(make({"subject":"हिंदी","subject_en":"Hindi","chapter":"BA 1st Semester","topic":"भक्तिकाल PYQ","topic_en":"LNMU MCQ 2026",
      "checklist":["स्वामी रामानंद","कबीरदास","रैदास","पीपा","संत काव्य","राम-कृष्ण काव्य"],"fact_title":"याद रखें","facts":["रामानंद के 12 शिष्य","कबीर: निर्गुण भक्ति","सूरदास: कृष्ण भक्ति"],
      "footer":["महत्वपूर्ण MCQ","Previous Year","परीक्षा तैयारी"]},art))
