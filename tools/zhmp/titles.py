"""Titles of ZHMP resolutions, 2022-2026, from the city's resolution register (usneseni.praha.eu, ISM OBIS),
because the 2022-2026 roll-call file leaves `nazevtisku` empty. Pages through the adopted-resolution list (about
84 form posts, one per second) and writes tools/data/zhmp/usneseni_zhmp_2022_2026.csv and titles2022.csv, joined
to votes2022.csv on resolution number + meeting date. Retrieved 2026-09-28.
"""

import re, time, html, csv, sys, urllib.request, urllib.parse, http.cookiejar
BASE='https://usneseni.praha.eu/ina/'
cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders=[('User-Agent','bsandova.com research (sandova) - polite paging of ZHMP resolution list')]
def get(url,data=None):
    if data is not None: data=urllib.parse.urlencode(data,encoding='cp1250').encode()
    r=op.open(url,data,timeout=60); b=r.read(); return r.geturl(), b.decode('cp1250',errors='replace')
def form(t):
    act=html.unescape(re.search(r'<form[^>]*action="([^"]+)"',t).group(1))
    d={}
    for m in re.finditer(r'<input[^>]*>',t):
        s=m.group(0); n=re.search(r'name="([^"]+)"',s); v=re.search(r'value="([^"]*)"',s)
        ty=re.search(r'type="([^"]+)"',s)
        if n and (not ty or ty.group(1) not in ('button','submit')): d[n.group(1)]=html.unescape(v.group(1)) if v else ''
    for m in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>',t,re.S):
        o=re.search(r'<option selected="selected" value="([^"]*)"',m.group(2)); d[m.group(1)]=o.group(1) if o else ''
    return urllib.parse.urljoin(BASE,act.lstrip('./')), d
def rows(t):
    out=[]
    for m in re.finditer(r'<tr[^>]*>\s*<td><a href="(tedusndetail\.aspx\?par=\d+)">([^<]*)</a></td><td>([^<]*)</td><td>([^<]*)</td><td>(.*?)</td><td>([^<]*)</td><td>([^<]*)</td>',t,re.S):
        out.append(dict(detail=BASE+m.group(1),cislotisku=m.group(2).strip(),cislousneseni=m.group(3).strip(),rok=m.group(4).strip(),
            title=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',m.group(5)))).strip(),datum=m.group(6).strip(),stav=m.group(7).strip()))
    return out
def pager(t):
    m=re.search(r'<td colspan="7">(.*?)</td>',t,re.S); p=m.group(1)
    cur=int(re.search(r'<span>(\d+)</span>',p).group(1))
    links=re.findall(r"__doPostBack\(&#39;([^&]+)&#39;,&#39;&#39;\)\">([^<]+)</a>",p)
    return cur,links
url,t=get(BASE+'seznamlist.aspx?evidence=usneseni-ZHMP-1')
act,d=form(t)
d.update({'__EVENTTARGET':'BtnHledej','__EVENTARGUMENT':'','DDListDotazy':'51186','TxtBx1':'2022-10-01','TxtBx2':'2026-12-31'})
time.sleep(1); url,t=get(act,d)
allr=[]; seen=set()
while True:
    rs=rows(t); cur,links=pager(t)
    allr+=rs; print('page',cur,len(rs),rs[0]['cislousneseni'] if rs else None,file=sys.stderr)
    nxt=None; after=False
    # links after current span
    p=re.search(r'<td colspan="7">(.*?)</td>',t,re.S).group(1)
    tail=p[p.find('<span>%d</span>'%cur):]
    lk=re.findall(r"__doPostBack\(&#39;([^&]+)&#39;,&#39;&#39;\)\">([^<]+)</a>",tail)
    if not lk: break
    target=lk[0][0]
    act,d=form(t); d.update({'__EVENTTARGET':target,'__EVENTARGUMENT':''})
    time.sleep(1.0); url,t=get(act,d)
    if cur>400: break
with open(sys.argv[1],'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(allr[0])); w.writeheader(); w.writerows(allr)
print('total',len(allr),file=sys.stderr)
