"""Conservative official-source collector. Runs without requiring an account or API key.
Only adds trades if both teams, trade date, player, and complete packages are parseable.
If the upstream article layout changes, exits without modifying trades.json.
"""
import json
import re
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = 'https://www.nfl.com/news/nfl-trade-deadline-track-every-move-since-start-of-2026-regular-season'
HERE = Path(__file__).resolve().parent
CITY = {
 'ARIZONA':'ari','BALTIMORE':'bal','CHICAGO':'chi','TENNESSEE':'ten','SAN FRANCISCO':'sf','INDIANAPOLIS':'ind','SEATTLE':'sea','HOUSTON':'hou','PHILADELPHIA':'phi','DALLAS':'dal','PITTSBURGH':'pit','NEW YORK':'nyg','MINNESOTA':'min',
 'BUFFALO':'buf','MIAMI':'mia','NEW ENGLAND':'ne','CINCINNATI':'cin','CLEVELAND':'cle','JACKSONVILLE':'jax','KANSAS CITY':'kc','LAS VEGAS':'lv','DENVER':'den','LOS ANGELES':'lar','DETROIT':'det','GREEN BAY':'gb','ATLANTA':'atl','CAROLINA':'car','NEW ORLEANS':'no','TAMPA BAY':'tb','WASHINGTON':'wsh'}
NAMES = {'CARDINALS':'ari','RAVENS':'bal','BEARS':'chi','TITANS':'ten','49ERS':'sf','COLTS':'ind','SEAHAWKS':'sea','TEXANS':'hou','EAGLES':'phi','COWBOYS':'dal','STEELERS':'pit','GIANTS':'nyg','VIKINGS':'min','BILLS':'buf','DOLPHINS':'mia','PATRIOTS':'ne','JETS':'nyj','BENGALS':'cin','BROWNS':'cle','JAGUARS':'jax','CHIEFS':'kc','RAIDERS':'lv','BRONCOS':'den','CHARGERS':'lac','LIONS':'det','PACKERS':'gb','FALCONS':'atl','PANTHERS':'car','SAINTS':'no','BUCCANEERS':'tb','RAMS':'lar','COMMANDERS':'wsh'}
ROUND = {'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7, **{str(n)+s:n for n,s in [(1,'st'),(2,'nd'),(3,'rd'),(4,'th'),(5,'th'),(6,'th'),(7,'th')]}}
POS = r'(QB|RB|FB|WR|TE|OT|OL|OG|G|C|LT|RT|LG|RG|DT|DL|DE|EDGE|LB|ILB|OLB|MLB|CB|DB|S|FS|SS|K|P|LS)'
PICK = re.compile(r'\b(202[6-9]|2030)\s+(first|second|third|fourth|fifth|sixth|seventh|[1-7](?:st|nd|rd|th))[- ]round\s+(?:draft\s+)?pick',re.I)
PLAYER = re.compile(r'^'+POS+r'\s+([\w.\'’\- ]{3,65})$',re.I)
DATE = re.compile(r'\b(?:Date of trade\s*:\s*)?(Sep(?:t(?:ember)?)?\.?|Oct(?:ober)?\.?|Nov(?:ember)?\.?)\s+(\d{1,2})\b', re.I)

def team_code(raw):
    label = re.sub(r'[^A-Z0-9 ]','',raw.upper()).strip()
    # The site uses city names (CHICAGO RECEIVES), not mascot names.
    for name,code in sorted(CITY.items(),key=lambda x:-len(x[0])):
        if label == name or label.startswith(name+' '):
            return code
    for name,code in NAMES.items():
        if re.search(r'\b'+re.escape(name)+r'\b',label):return code
    return None

def parse_article(html):
    soup = BeautifulSoup(html,'html.parser')
    found=[]
    for heading in soup.find_all(['h2','h3','h4']):
        title=heading.get_text(' ',strip=True)
        if not title or len(title)>160:continue
        if not re.search(r'trad|acquir|land|deal|ship|send|swap|add|bolster|reunit|sell',title,re.I):continue
        lines=[]
        # Walk *siblings* under the heading: avoids traversing nested unrelated portions.
        for el in heading.next_elements:
            if el is heading:continue
            if getattr(el,'name',None) in ('h2','h3','h4'):break
            if getattr(el,'name',None)=='p':
                s=el.get_text(' ',strip=True)
                if s and len(s)<250:lines.append(s)
            elif getattr(el,'name',None)=='li' and getattr(getattr(el,'parent',None),'name',None) in ('ul','ol'):
                s=el.get_text(' ',strip=True)
                if s:lines.append(s)
            if len(lines)>80:break
        date=None
        for s in lines:
            m=DATE.search(s)
            if m:
                month=9 if m.group(1).lower().startswith('sep') else 10 if m.group(1).lower().startswith('oct') else 11
                date=f'2026-{month:02d}-{int(m.group(2)):02d}'
                break
        if not date:continue
        sides={};active=None
        for line in lines:
            marker=re.match(r'^(.{2,45}?)\s+RECEIVES\s*:\s*(.*)$',line,re.I)
            if marker:
                active=team_code(marker.group(1));
                if active:sides.setdefault(active,[])
                if not marker.group(2):continue
                line=marker.group(2)
            if not active:continue
            m=PICK.search(line)
            if m:
                sides[active].append({'type':'pick','year':int(m.group(1)),'round':ROUND[m.group(2).lower()]})
                continue
            m=PLAYER.fullmatch(line.strip())
            if m:
                sides[active].append({'type':'player','name':m.group(2).strip(),'position':m.group(1).upper()})
        if len(sides)!=2 or not all(sides.values()):continue
        players=[a['name'] for assets in sides.values() for a in assets if a['type']=='player']
        if not players:continue
        codes=list(sides)
        found.append({'id':'nfl-'+date+'-'+re.sub(r'[^a-z0-9]+','-',players[0].lower()).strip('-'), 'date':date,'time':None,'status':'completed','headline':title,'teams':codes,'receives':sides,'grade':{c:None for c in codes},'analysis':'Trade compensation reported by NFL.com. Independent grades and detailed evaluation not yet available for this newly detected deal.', 'sources':[URL]})
    return found

def merge(existing, discovered):
    new=[]; updated=[]
    for candidate in discovered:
        players={a['name'].lower() for assets in candidate['receives'].values() for a in assets if a['type']=='player'}
        matches=[t for t in existing if players.intersection(a['name'].lower() for assets in t['receives'].values() for a in assets if a['type']=='player')]
        if matches:
            # If NFL has confirmed a previously reported agreement, promote it to completed
            # and fill official compensation. Don't discard existing published editorial grades.
            previous=next((t for t in matches if t['status']=='agreement'),None)
            if previous is not None:
                old_grade=previous.get('grade',{})
                previous.update(candidate)
                previous['grade']={c:old_grade.get(c) for c in candidate['teams']}
                updated.append(candidate['headline'])
            continue
        existing.append(candidate);new.append(candidate['headline'])
    existing.sort(key=lambda t:(t['date'],t.get('time') or ''),reverse=True)
    return new,updated

def main():
    response=requests.get(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; NFLDeadlineTracker/2.0)'},timeout=22)
    response.raise_for_status()
    if len(response.content)<3500:raise ValueError('Article response too short')
    discovered=parse_article(response.text)
    if len(discovered)<4:raise ValueError(f'Only {len(discovered)} entries parsed. Article may have changed or blocked access; refusing unsafe update')
    filename=HERE/'trades.json'
    existing=json.loads(filename.read_text('utf-8'))
    new,updated=merge(existing,discovered)
    if new or updated:
        filename.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Official page: {len(discovered)} trades parsed. Added: {len(new)}, updated: {len(updated)}')
    for item in new:print('NEW:',item)
    for item in updated:print('CONFIRMED:',item)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Collector did not change records:',exc,file=sys.stderr)
        sys.exit(1)
