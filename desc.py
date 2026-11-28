import os, json, re, time, urllib.request, urllib.parse, sys
CH="UCIu3HhyaYVGtkuFo0wJCyow"
def http(url, data=None, headers={}, method=None):
    if isinstance(data,dict): data=json.dumps(data).encode(); headers={**headers,"Content-Type":"application/json"}
    elif isinstance(data,str): data=data.encode(); headers={**headers,"Content-Type":"application/x-www-form-urlencoded"}
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as f: return json.loads(f.read() or b"{}")
def token():
    d=urllib.parse.urlencode({"client_id":os.environ["YT_CLIENT_ID"],"client_secret":os.environ["YT_CLIENT_SECRET"],
        "refresh_token":os.environ["YT_REFRESH_TOKEN"],"grant_type":"refresh_token"})
    return http("https://oauth2.googleapis.com/token",d)["access_token"]
def gemini_key():
    k=os.environ.get("GEMINI_KEY")
    if k: return k
    j=http("https://firestore.googleapis.com/v1/projects/saathi-ai-68bbf/databases/(default)/documents/config/app")
    return j["fields"]["geminiKey"]["stringValue"]
MODE=os.environ.get("MODE","preview")      # preview | apply
LINK=os.environ.get("LINK","").strip()     # link to add at end
LINE=os.environ.get("LINE","").strip()     # optional line before link
MAXAPPLY=int(os.environ.get("MAXAPPLY","90"))
PREV="docs/desc_preview.json"; DONE="docs/desc_done.json"
Y="https://www.googleapis.com/youtube/v3/"
URL=re.compile(r'(https?://\S+|www\.\S+|\b\S+\.(com|in|me|ly|be|org|net|app|io)/\S*)',re.I)

def g(key,prompt,img=None):
    parts=[{"text":prompt}]
    if img: parts=[{"inline_data":{"mime_type":"image/jpeg","data":img}}]+parts
    for m in ["gemini-3.1-flash-lite","gemini-3.5-flash","gemini-3.1-flash-lite","gemini-3.5-flash"]:
        time.sleep(4)
        try:
            j=http(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
              {"contents":[{"parts":parts}],"generationConfig":{"responseMimeType":"application/json","temperature":0.3}})
            return json.loads(j["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e: print("gemini",m,e)
    return None

def all_videos(H):
    up=http(Y+"channels?part=contentDetails&id="+CH,headers=H)["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids=[];p=""
    while True:
        j=http(Y+"playlistItems?"+urllib.parse.urlencode({"part":"contentDetails","playlistId":up,"maxResults":50,"pageToken":p}),headers=H)
        ids+=[i["contentDetails"]["videoId"] for i in j["items"]]; p=j.get("nextPageToken")
        if not p: break
    vids=[]
    for k in range(0,len(ids),50):
        vids+=http(Y+"videos?part=snippet&id="+",".join(ids[k:k+50]),headers=H)["items"]
    return vids

def playlists(H):
    pl={};p=""
    while True:
        j=http(Y+"playlists?"+urllib.parse.urlencode({"part":"snippet","mine":"true","maxResults":50,"pageToken":p}),headers=H)
        for i in j["items"]: pl[i["snippet"]["title"]]={"id":i["id"],"videos":set()}
        p=j.get("nextPageToken")
        if not p: break
    for t,v in pl.items():
        p=""
        while True:
            j=http(Y+"playlistItems?"+urllib.parse.urlencode({"part":"contentDetails","playlistId":v["id"],"maxResults":50,"pageToken":p}),headers=H)
            v["videos"]|={i["contentDetails"]["videoId"] for i in j["items"]}; p=j.get("nextPageToken")
            if not p: break
    return pl

DP="""तुम Smart Exam Academy (प्रतियोगी परीक्षा/पढ़ाई का YouTube चैनल) की वीडियो description सुधारते हो।
वीडियो title: «{t}»
अभी की description (लिंक हटा दिए गए हैं): «{d}»
काम: description को इसी वीडियो के विषय के अनुसार साफ़, सही और पढ़ने लायक बनाओ। जो सही जानकारी है वह रखो, गलत या दूसरे वीडियो की बात हटाओ, वर्तनी सुधारो। उसी भाषा/लिपि में जिसमें title है। 2-5 छोटी लाइनें + अगर पहले hashtags/timestamps थे तो वे रखो (timestamps बदलना नहीं)। कोई लिंक, फ़ोन नंबर, झूठा दावा या नई जानकारी मत गढ़ो।
सिर्फ़ JSON: {{"description":"..."}}"""
PP="""Smart Exam Academy चैनल की वीडियो को playlist में डालना है।
पहले से मौजूद playlists: {pl}
वीडियो (id: title): 
{v}
हर वीडियो के लिए सबसे सही playlist चुनो। मौजूदा playlist सही बैठे तो वही नाम बिल्कुल वैसा ही लिखो; कोई सही न हो तो नया छोटा, साफ़ playlist नाम दो (विषय/परीक्षा के अनुसार, जैसे "GK Questions", "Science MCQ"), और मिलती-जुलती वीडियो को एक ही नए नाम में रखो।
सिर्फ़ JSON: {{"<id>":"<playlist नाम>", ...}}"""

def preview(H,key):
    vids=all_videos(H); pl=playlists(H)
    inpl={vid for v in pl.values() for vid in v["videos"]}
    names=list(pl.keys()); assign={}
    todo=[v for v in vids if v["id"] not in inpl]
    for k in range(0,len(todo),40):
        part=todo[k:k+40]
        o=g(key,PP.format(pl=json.dumps(names,ensure_ascii=False),v="\n".join(f'{v["id"]}: {v["snippet"]["title"]}' for v in part))) or {}
        for v in part:
            n=(o.get(v["id"]) or "").strip()[:140]
            if n: assign[v["id"]]=n; names.append(n) if n not in names else None
    old=json.load(open(PREV)) if os.path.exists(PREV) else {"items":[]}
    oldd={i["id"]:i for i in old["items"]}
    items=[]
    for v in vids:
        s=v["snippet"]; d=s.get("description","")
        if v["id"] in oldd and oldd[v["id"]].get("old")==d: it=oldd[v["id"]]
        else:
            clean=URL.sub("",d); clean=re.sub(r"\n{3,}","\n\n",clean).strip()
            o=g(key,DP.format(t=s["title"],d=clean[:4000]))
            it={"id":v["id"],"title":s["title"],"old":d,"new":(o or {}).get("description",clean)}
        it["playlist"]=assign.get(v["id"],"") ; it["newPlaylist"]=bool(it["playlist"]) and it["playlist"] not in pl
        items.append(it)
        json.dump({"items":items,"updated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime()),"total":len(vids)},open(PREV,"w"),ensure_ascii=False,indent=0)
    print("preview",len(items))

def apply(H):
    if not LINK: sys.exit("LINK missing")
    pv=json.load(open(PREV)); done=json.load(open(DONE)) if os.path.exists(DONE) else {}
    pl=playlists(H); n=0
    for it in pv["items"]:
        if it["id"] in done or n>=MAXAPPLY: continue
        v=http(Y+"videos?part=snippet&id="+it["id"],headers=H)["items"]
        if not v: continue
        sn=v[0]["snippet"]
        tail=(LINE+"\n" if LINE else "")+LINK
        desc=(it["new"].strip()+"\n\n"+tail)[:4900]
        body={"id":it["id"],"snippet":{"title":sn["title"],"categoryId":sn["categoryId"],"description":desc,
              "tags":sn.get("tags",[]),"defaultLanguage":sn.get("defaultLanguage"),"defaultAudioLanguage":sn.get("defaultAudioLanguage")}}
        body["snippet"]={k:x for k,x in body["snippet"].items() if x is not None}
        try:
            http(Y+"videos?part=snippet",body,H,method="PUT")
            p=it.get("playlist")
            if p:
                if p not in pl:
                    r=http(Y+"playlists?part=snippet,status",{"snippet":{"title":p},"status":{"privacyStatus":"public"}},H)
                    pl[p]={"id":r["id"],"videos":set()}
                if it["id"] not in pl[p]["videos"]:
                    http(Y+"playlistItems?part=snippet",{"snippet":{"playlistId":pl[p]["id"],"resourceId":{"kind":"youtube#video","videoId":it["id"]}}},H)
                    pl[p]["videos"].add(it["id"])
            done[it["id"]]=time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime()); n+=1
        except Exception as e:
            body_=getattr(e,"read",lambda:b"")()[:400].decode("utf8","ignore"); print("fail",it["id"],e,body_)
            if "quota" in body_.lower(): break
        json.dump(done,open(DONE,"w"),indent=0)
    print("applied",n,"total done",len(done))

SP="""तुम Smart Exam Academy (प्रतियोगी/बोर्ड/यूनिवर्सिटी परीक्षा की पढ़ाई का YouTube चैनल) के लिए YouTube SEO करते हो।
वीडियो title: «{t}»
description: «{d}»
tags: {g}
साथ में वीडियो का thumbnail है: असली विषय (कक्षा/सेमेस्टर, विषय, इकाई/अध्याय, यूनिवर्सिटी जैसे LNMU) thumbnail पर लिखे टेक्स्ट से पढ़ो। अगर title में सिर्फ़ तारीख़ है तो तारीख़ को विषय मत मानो और "Current Affairs" मत लिखो जब तक thumbnail पर वह न हो।
काम: इसी वीडियो के विषय के अनुसार search में आने लायक SEO करो। title: 100 अक्षर से कम, मुख्य keyword शुरू में, विषय/अध्याय/परीक्षा का नाम, हिंदी+English keywords मिलाकर (जैसे अभी हैं), clickbait या झूठ नहीं। description: पहली 2 लाइनों में मुख्य keywords, फिर 3-6 लाइनों में वीडियो में क्या है, अंत में 3-5 hashtags; timestamps हों तो रखो; कोई लिंक/फ़ोन नंबर नहीं। tags: 10-20 relevant tags (हिंदी व English), कुल 450 अक्षर से कम।
सिर्फ़ JSON: {{"title":"...","description":"...","tags":["..."]}}"""
SPV="docs/seo_preview.json"; SDONE="docs/seo_done.json"
def seo_preview(H,key):
    vids=all_videos(H); out=[]
    full=[]
    for k in range(0,len(vids),50):
        full+=http(Y+"videos?part=snippet,status&id="+",".join(v["id"] for v in vids[k:k+50]),headers=H)["items"]
    print("uploads",len(vids),"fetched",len(full))
    un=[v for v in full if v["status"]["privacyStatus"]!="public"]
    for v in un: print("NONPUBLIC",v["id"],v["status"]["privacyStatus"],v["status"].get("uploadStatus"),v["snippet"]["title"][:60])
    un=[v for v in un if v["status"]["privacyStatus"]=="unlisted"]
    print("unlisted",len(un))
    pl=playlists(H); names=list(pl.keys()); inpl={x for p in pl.values() for x in p["videos"]}
    prev={i["id"]:i for i in json.load(open(PREV))["items"]} if os.path.exists(PREV) else {}
    for v in un:
        s=v["snippet"]; d=URL.sub("",s.get("description",""))
        th=s.get("thumbnails",{}); thumb=(th.get("maxres") or th.get("standard") or th.get("high") or th.get("medium") or {}).get("url","")
        img=None
        try:
            import base64; img=base64.b64encode(urllib.request.urlopen(thumb,timeout=30).read()).decode()
        except Exception as e: print("thumb",e)
        o=g(key,SP.format(t=s["title"],d=d[:4000],g=json.dumps(s.get("tags",[]),ensure_ascii=False)),img) or {}
        p=prev.get(v["id"],{}).get("playlist","")
        if not p and v["id"] not in inpl:
            r=g(key,PP.format(pl=json.dumps(names,ensure_ascii=False),v=f'{v["id"]}: {(o.get("title") or s["title"])}')) or {}
            p=(r.get(v["id"]) or "").strip()[:140]
        out.append({"id":v["id"],"oldTitle":s["title"],"title":(o.get("title") or s["title"])[:100],"old":s.get("description",""),
            "new":o.get("description") or d,"tags":o.get("tags") or s.get("tags",[]),"thumb":thumb,"ok":bool(o.get("title")),"playlist":p,"newPlaylist":bool(p) and p not in pl})
        json.dump({"items":out,"updated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())},open(SPV,"w"),ensure_ascii=False,indent=0)
    json.dump({"items":out,"updated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())},open(SPV,"w"),ensure_ascii=False,indent=0)
    print("seo preview",len(out))
def seo_apply(H):
    pv=json.load(open(SPV)); done=json.load(open(SDONE)) if os.path.exists(SDONE) else {}
    pl=playlists(H); n=0
    for it in pv["items"]:
        if it["id"] in done or n>=MAXAPPLY or not it.get("ok",True): continue
        v=http(Y+"videos?part=snippet,status&id="+it["id"],headers=H)["items"]
        if not v: continue
        sn=v[0]["snippet"]; st=v[0]["status"]
        tail=("\n\n"+(LINE+"\n" if LINE else "")+LINK) if LINK else ""
        tags=[]; tot=0
        for t in it["tags"]:
            if tot+len(t)+2>480: break
            tags.append(t); tot+=len(t)+2
        sn2={"title":it["title"],"categoryId":sn["categoryId"],"description":(it["new"].strip()+tail)[:4900],"tags":tags}
        for k in("defaultLanguage","defaultAudioLanguage"):
            if sn.get(k): sn2[k]=sn[k]
        st2={"privacyStatus":"public","embeddable":st.get("embeddable",True),"publicStatsViewable":st.get("publicStatsViewable",True)}
        if "selfDeclaredMadeForKids" in st: st2["selfDeclaredMadeForKids"]=st["selfDeclaredMadeForKids"]
        try:
            http(Y+"videos?part=snippet,status",{"id":it["id"],"snippet":sn2,"status":st2},H,method="PUT"); print("updated",it["id"])
            p=it.get("playlist")
            if p:
                if p not in pl:
                    r=http(Y+"playlists?part=snippet,status",{"snippet":{"title":p},"status":{"privacyStatus":"public"}},H); pl[p]={"id":r["id"],"videos":set()}
                if it["id"] not in pl[p]["videos"]:
                    http(Y+"playlistItems?part=snippet",{"snippet":{"playlistId":pl[p]["id"],"resourceId":{"kind":"youtube#video","videoId":it["id"]}}},H); pl[p]["videos"].add(it["id"])
            done[it["id"]]=time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime()); n+=1
        except Exception as e:
            b_=getattr(e,"read",lambda:b"")()[:400].decode("utf8","ignore"); print("fail",it["id"],e,b_)
            if "quota" in b_.lower(): break
        json.dump(done,open(SDONE,"w"),indent=0)
    print("published",n)

def seo_verify(H):
    pv=json.load(open(SPV)); done=json.load(open(SDONE)) if os.path.exists(SDONE) else {}
    ids=[i["id"] for i in pv["items"]]; got={}
    for k in range(0,len(ids),50):
        for v in http(Y+"videos?part=snippet,status&id="+",".join(ids[k:k+50]),headers=H)["items"]: got[v["id"]]=v
    for i in pv["items"]:
        v=got.get(i["id"]); st=v["status"]["privacyStatus"] if v else "missing"
        print("STATE",i["id"],st,"|",v["snippet"]["title"][:70] if v else "")
        if st!="public": done.pop(i["id"],None)
    json.dump(done,open(SDONE,"w"),indent=0)
    seo_apply(H)
    for k in range(0,len(ids),50):
        for v in http(Y+"videos?part=status&id="+",".join(ids[k:k+50]),headers=H)["items"]: print("AFTER",v["id"],v["status"]["privacyStatus"])

AP="""तुम Smart Exam Academy (प्रतियोगी/बोर्ड/यूनिवर्सिटी परीक्षा की पढ़ाई का YouTube चैनल) के YouTube SEO और thumbnail designer हो।
वीडियो title: «{t}»
description: «{d}»
tags: {g}
साथ में वीडियो का अभी का thumbnail है। असली विषय (कक्षा/सेमेस्टर, विषय, इकाई/अध्याय, यूनिवर्सिटी) title, description और thumbnail पर लिखे टेक्स्ट से पहचानो। title में सिर्फ़ तारीख़ हो तो उसे विषय मत मानो; अंदाज़े से "Current Affairs" मत लिखो।
1) designed: thumbnail पहले से डिज़ाइन किया हुआ है (बड़ा शीर्षक/चैनल नाम/टेक्स्ट वाला) तो true, अगर वीडियो का साधारण frame/धुंधला/खाली है तो false।
2) SEO: title (100 अक्षर से कम, मुख्य keyword शुरू में, हिंदी+English), description (पहली 2 लाइनों में keywords, 3-6 लाइनें सामग्री, अंत में 3-5 hashtags, कोई लिंक/फ़ोन नहीं), tags (10-20, कुल 450 अक्षर से कम)।
3) thumbnail (चैनल की शैली) के लिए: top (ऊपर का banner, आम तौर पर "सभी शैक्षिक एवं प्रतियोगी परीक्षाओं के लिए" या "BA 1st Semester • LNMU 2026" जैसा), subject (विषय हिंदी में 1-2 शब्द, जैसे "गणित", "भौतिक विज्ञान", "हिंदी"), subject_en (जैसे "Math"), chapter (जैसे "अध्याय - 3" या "BA 1st Semester" या "MCQ 2026"), topic (मुख्य विषय हिंदी में 1-4 शब्द, सबसे बड़ा), topic_en (English नाम या "LNMU MCQ 2026"), checklist (6-8 छोटे बिंदु, हर एक 4 शब्द तक, वीडियो में क्या-क्या है), fact_title (जैसे "महत्वपूर्ण सूत्र" या "याद रखें"), facts (2-4 छोटी लाइनें: सूत्र/उदाहरण/तथ्य, बिल्कुल सही), footer (3 छोटे शब्द-समूह, जैसे ["संपूर्ण थ्योरी","महत्वपूर्ण सूत्र","MCQ + PYQ"]), image_prompt (English में विषय से जुड़ा चित्र: व्यक्ति/वस्तु, बिना text)।
सिर्फ़ JSON: {{"designed":true,"title":"...","description":"...","tags":["..."],"top":"...","subject":"...","subject_en":"...","chapter":"...","topic":"...","topic_en":"...","checklist":["..."],"fact_title":"...","facts":["..."],"footer":["..."],"image_prompt":"..."}}"""
ALOG="docs/auto_log.json"
def set_thumb(H,vid,jpg):
    r=urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId="+vid,data=jpg,method="POST",
        headers={**H,"Content-Type":"image/jpeg"})
    with urllib.request.urlopen(r,timeout=120) as f: return json.loads(f.read() or b"{}")
def auto(H,key):
    import base64, thumb
    FORCE=os.environ.get("FORCE_THUMB","")=="1"
    vids=all_videos(H); full=[]
    for k in range(0,len(vids),50):
        full+=http(Y+"videos?part=snippet,status&id="+",".join(v["id"] for v in vids[k:k+50]),headers=H)["items"]
    un=[v for v in full if v["status"]["privacyStatus"]=="unlisted" and v["status"].get("uploadStatus") in ("processed","uploaded",None)]
    print("uploads",len(vids),"unlisted",len(un))
    if not un: return
    log=json.load(open(ALOG)) if os.path.exists(ALOG) else {"items":[]}
    pl=playlists(H); names=list(pl.keys())
    global LOGO; LOGO=None
    try:
        from PIL import Image as _I; import io as _io
        cu=http(Y+"channels?part=snippet&id="+CH,headers=H)["items"][0]["snippet"]["thumbnails"]["high"]["url"]
        LOGO=_I.open(_io.BytesIO(urllib.request.urlopen(cu,timeout=30).read()))
    except Exception as e: print("logo",e)
    for v in un[:MAXAPPLY]:
        s=v["snippet"]; d=URL.sub("",s.get("description",""))
        th=s.get("thumbnails",{}); turl=(th.get("maxres") or th.get("standard") or th.get("high") or th.get("medium") or {}).get("url","")
        img=None
        try: img=base64.b64encode(urllib.request.urlopen(turl,timeout=30).read()).decode()
        except Exception as e: print("thumb get",e)
        o=g(key,AP.format(t=s["title"],d=d[:4000],g=json.dumps(s.get("tags",[]),ensure_ascii=False)),img) or {}
        if not o.get("title"): print("seo failed, skip",v["id"]); continue
        entry={"id":v["id"],"oldTitle":s["title"],"title":o["title"][:100],"time":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime()),"thumb":"kept"}
        try:
            if FORCE or not o.get("designed",True):
                jpg,how=thumb.build(o,key,LOGO)
                os.makedirs("docs/thumbs",exist_ok=True); open(f"docs/thumbs/{v['id']}.jpg","wb").write(jpg)
                set_thumb(H,v["id"],jpg); entry["thumb"]="new: "+how
        except Exception as e:
            b_=getattr(e,"read",lambda:b"")()[:300].decode("utf8","ignore"); print("thumb set fail",e,b_); entry["thumb"]="fail: "+b_[:120]
        r=g(key,PP.format(pl=json.dumps(names,ensure_ascii=False),v=f'{v["id"]}: {o["title"]}')) or {}
        p=(r.get(v["id"]) or "").strip()[:140]
        if p and p not in names: names.append(p)
        tags=[]; tot=0
        for t in o.get("tags") or []:
            if tot+len(t)+2>480: break
            tags.append(t); tot+=len(t)+2
        tail=("\n\n"+(LINE+"\n" if LINE else "")+LINK) if LINK else ""
        sn2={"title":entry["title"],"categoryId":s["categoryId"],"description":((o.get("description") or d).strip()+tail)[:4900],"tags":tags}
        for k in("defaultLanguage","defaultAudioLanguage"):
            if s.get(k): sn2[k]=s[k]
        st=v["status"]; st2={"privacyStatus":"public","embeddable":st.get("embeddable",True),"publicStatsViewable":st.get("publicStatsViewable",True)}
        if "selfDeclaredMadeForKids" in st: st2["selfDeclaredMadeForKids"]=st["selfDeclaredMadeForKids"]
        try:
            http(Y+"videos?part=snippet,status",{"id":v["id"],"snippet":sn2,"status":st2},H,method="PUT"); entry["status"]="public"
            if p:
                if p not in pl:
                    rr_=http(Y+"playlists?part=snippet,status",{"snippet":{"title":p},"status":{"privacyStatus":"public"}},H); pl[p]={"id":rr_["id"],"videos":set()}
                if v["id"] not in pl[p]["videos"]:
                    http(Y+"playlistItems?part=snippet",{"snippet":{"playlistId":pl[p]["id"],"resourceId":{"kind":"youtube#video","videoId":v["id"]}}},H); pl[p]["videos"].add(v["id"])
                entry["playlist"]=p
        except Exception as e:
            b_=getattr(e,"read",lambda:b"")()[:300].decode("utf8","ignore"); print("publish fail",v["id"],e,b_); entry["status"]="fail"
        print("AUTO",json.dumps(entry,ensure_ascii=False))
        log["items"].insert(0,entry); log["items"]=log["items"][:500]; log["updated"]=entry["time"]
        json.dump(log,open(ALOG,"w"),ensure_ascii=False,indent=0)

if __name__=="__main__":
    H={"Authorization":"Bearer "+token()}
    {"preview":lambda:preview(H,gemini_key()),"apply":lambda:apply(H),"seo_preview":lambda:seo_preview(H,gemini_key()),"seo_apply":lambda:seo_apply(H),"seo_verify":lambda:seo_verify(H),"auto":lambda:auto(H,gemini_key()),"seo_all":lambda:(seo_preview(H,gemini_key()),seo_apply(H))}[MODE]()
