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

def g(key,prompt):
    for m in ["gemini-3.5-flash","gemini-3.1-flash-lite","gemini-3.5-flash"]:
        time.sleep(4)
        try:
            j=http(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
              {"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json","temperature":0.3}})
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
काम: इसी वीडियो के विषय के अनुसार search में आने लायक SEO करो। title: 100 अक्षर से कम, मुख्य keyword शुरू में, विषय/अध्याय/परीक्षा का नाम, हिंदी+English keywords मिलाकर (जैसे अभी हैं), clickbait या झूठ नहीं। description: पहली 2 लाइनों में मुख्य keywords, फिर 3-6 लाइनों में वीडियो में क्या है, अंत में 3-5 hashtags; timestamps हों तो रखो; कोई लिंक/फ़ोन नंबर नहीं। tags: 10-20 relevant tags (हिंदी व English), कुल 450 अक्षर से कम।
सिर्फ़ JSON: {{"title":"...","description":"...","tags":["..."]}}"""
SPV="docs/seo_preview.json"; SDONE="docs/seo_done.json"
def seo_preview(H,key):
    vids=all_videos(H); out=[]
    full=[]
    for k in range(0,len(vids),50):
        full+=http(Y+"videos?part=snippet,status&id="+",".join(v["id"] for v in vids[k:k+50]),headers=H)["items"]
    un=[v for v in full if v["status"]["privacyStatus"]=="unlisted"]
    print("unlisted",len(un))
    pl=playlists(H); names=list(pl.keys()); inpl={x for p in pl.values() for x in p["videos"]}
    prev={i["id"]:i for i in json.load(open(PREV))["items"]} if os.path.exists(PREV) else {}
    for v in un:
        s=v["snippet"]; d=URL.sub("",s.get("description",""))
        o=g(key,SP.format(t=s["title"],d=d[:4000],g=json.dumps(s.get("tags",[]),ensure_ascii=False))) or {}
        th=s.get("thumbnails",{}); thumb=(th.get("maxres") or th.get("high") or th.get("medium") or {}).get("url","")
        p=prev.get(v["id"],{}).get("playlist","")
        if not p and v["id"] not in inpl:
            r=g(key,PP.format(pl=json.dumps(names,ensure_ascii=False),v=f'{v["id"]}: {s["title"]}')) or {}
            p=(r.get(v["id"]) or "").strip()[:140]
        out.append({"id":v["id"],"oldTitle":s["title"],"title":(o.get("title") or s["title"])[:100],"old":s.get("description",""),
            "new":o.get("description") or d,"tags":o.get("tags") or s.get("tags",[]),"thumb":thumb,"playlist":p,"newPlaylist":bool(p) and p not in pl})
        json.dump({"items":out,"updated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())},open(SPV,"w"),ensure_ascii=False,indent=0)
    json.dump({"items":out,"updated":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())},open(SPV,"w"),ensure_ascii=False,indent=0)
    print("seo preview",len(out))
def seo_apply(H):
    pv=json.load(open(SPV)); done=json.load(open(SDONE)) if os.path.exists(SDONE) else {}
    pl=playlists(H); n=0
    for it in pv["items"]:
        if it["id"] in done or n>=MAXAPPLY: continue
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
            http(Y+"videos?part=snippet,status",{"id":it["id"],"snippet":sn2,"status":st2},H,method="PUT")
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

if __name__=="__main__":
    H={"Authorization":"Bearer "+token()}
    {"preview":lambda:preview(H,gemini_key()),"apply":lambda:apply(H),"seo_preview":lambda:seo_preview(H,gemini_key()),"seo_apply":lambda:seo_apply(H)}[MODE]()
