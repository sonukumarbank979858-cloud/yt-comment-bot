import os, json, time, urllib.request, urllib.parse
CH="UCIu3HhyaYVGtkuFo0wJCyow"
STATE="docs/comments.json"; MAXREPLY=int(os.environ.get("MAXREPLY","15"))
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
PROMPT="""तुम Smart Exam Academy (प्रतियोगी परीक्षा/पढ़ाई का YouTube चैनल) की ओर से कमेंट का जवाब देते हो।
कमेंट: «{c}»
वीडियो: «{v}»
1) sentiment तय करो: "good" (तारीफ़/धन्यवाद/खुशी), "negative" (शिकायत/गुस्सा/आलोचना/गाली), या "average" (सवाल/सामान्य/न्यूट्रल)।
2) उसी भाषा और लिपि में जवाब लिखो जिसमें कमेंट है (हिंदी, हिंग्लिश, भोजपुरी, अंग्रेज़ी आदि)। 1-2 छोटे वाक्य, विनम्र, गर्मजोशी भरा। नेगेटिव कमेंट पर भी शांत, सकारात्मक, धन्यवाद देकर सुधार का वादा; कोई बहस, ताना या गाली नहीं। सवाल हो तो छोटा सही जवाब या अगले वीडियो का भरोसा। कोई लिंक, फ़ोन नंबर या झूठा वादा नहीं। स्पैम/लिंक वाले कमेंट पर reply खाली "" रखो।
सिर्फ़ JSON: {{"sentiment":"good|negative|average","reply":"..."}}"""
def ask(key,c,v):
    for m in ["gemini-3.1-flash-lite","gemini-3.5-flash"]:
        try:
            j=http(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}",
              {"contents":[{"parts":[{"text":PROMPT.format(c=c,v=v)}]}],"generationConfig":{"responseMimeType":"application/json","temperature":0.6}})
            t=j["candidates"][0]["content"]["parts"][0]["text"]; o=json.loads(t)
            if o.get("sentiment") in("good","negative","average"): return o
        except Exception as e: print("gemini",m,e)
    return None
def main():
    st=json.load(open(STATE)) if os.path.exists(STATE) else {"items":[]}
    seen={i["id"] for i in st["items"]}
    at=token(); H={"Authorization":"Bearer "+at}; key=gemini_key()
    q=urllib.parse.urlencode({"part":"snippet,replies","allThreadsRelatedToChannelId":CH,"maxResults":50,"order":"time","textFormat":"plainText"})
    th=http("https://www.googleapis.com/youtube/v3/commentThreads?"+q,headers=H).get("items",[])
    vids={}; n=0
    for t in reversed(th):
        if t["id"] in seen: continue
        s=t["snippet"]["topLevelComment"]["snippet"]
        if s.get("authorChannelId",{}).get("value")==CH: continue
        replied=any(r["snippet"].get("authorChannelId",{}).get("value")==CH for r in t.get("replies",{}).get("comments",[]))
        vid=t["snippet"].get("videoId","")
        if vid and vid not in vids:
            try: vids[vid]=http("https://www.googleapis.com/youtube/v3/videos?part=snippet&id="+vid,headers=H)["items"][0]["snippet"]["title"]
            except Exception: vids[vid]=""
        o=ask(key,s["textDisplay"],vids.get(vid,""))
        if not o: continue
        item={"id":t["id"],"author":s.get("authorDisplayName",""),"text":s["textDisplay"],"video":vids.get(vid,""),"videoId":vid,
              "time":s.get("publishedAt",""),"sentiment":o["sentiment"],"reply":"","status":"skipped"}
        if replied: item["status"]="already-replied"
        elif o.get("reply") and n<MAXREPLY:
            try:
                http("https://www.googleapis.com/youtube/v3/comments?part=snippet",{"snippet":{"parentId":t["id"],"textOriginal":o["reply"]}},H)
                item["reply"]=o["reply"]; item["status"]="replied"; n+=1
            except Exception as e: print("reply fail",e); continue
        elif o.get("reply"): continue  # over limit, try next run
        st["items"].insert(0,item); seen.add(t["id"]); time.sleep(1)
    st["items"]=st["items"][:2000]; st["updated"]=time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())
    json.dump(st,open(STATE,"w"),ensure_ascii=False,indent=0)
    print("replied",n)
main()
