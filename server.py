"""NFL Deadline Command: lightweight live-check server. Run: python server.py"""
import copy
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).parent
app = Flask(__name__, static_folder=str(HERE))
SEED = json.loads((HERE / 'trades.json').read_text(encoding='utf-8'))
NFL = 'https://www.nfl.com/news/nfl-trade-deadline-track-every-move-since-start-of-2026-regular-season'
CBS = 'https://www.cbssports.com/nfl/news/2026-nfl-trade-deadline-tracker-latest-deals-grades/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DeadlineCommand/1.0; public-sports-monitor)'}
TEAM_NAME = {'CARDINALS':'ari','RAVENS':'bal','BEARS':'chi','TITANS':'ten','49ERS':'sf','COLTS':'ind','SEAHAWKS':'sea','TEXANS':'hou','EAGLES':'phi','COWBOYS':'dal','STEELERS':'pit','GIANTS':'nyg','VIKINGS':'min',
'BILLS':'buf','DOLPHINS':'mia','PATRIOTS':'ne','JETS':'nyj','BENGALS':'cin','BROWNS':'cle','JAGUARS':'jax','CHIEFS':'kc','RAIDERS':'lv','BRONCOS':'den','CHARGERS':'lac','LIONS':'det','PACKERS':'gb','FALCONS':'atl','PANTHERS':'car','SAINTS':'no','BUCCANEERS':'tb','RAMS':'lar','COMMANDERS':'wsh'}
# Two known currently inconsistent reports are deliberately not automatically overwritten.
state = {'trades': copy.deepcopy(SEED), 'profiles': {}, 'last_checked': None, 'source_ok': False, 'note': 'Verified seed trades loaded; initial verification pending.'}
_lock = threading.Lock()
_next_trade_check = 0
_next_profile_check = 0


def fetch_html(url):
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    if len(response.content) < 3500:
        raise ValueError('source response too short')
    return BeautifulSoup(response.text, 'html.parser')


def parse_nfl_new(soup, existing):
    """Extract *new* confirmed trade entries from official NFL article; skip ambiguous deals.
    Only use exact 'X RECEIVES:' labels plus explicit player and pick line items.
    Articles change structure, so failure is nonfatal and never treated as proof of no trades.
    """
    new = []
    existing_player_names = {a['name'].lower() for t in existing for assets in t['receives'].values() for a in assets if a['type'] == 'player'}
    for h in soup.find_all(['h3']):
        title = h.get_text(' ', strip=True)
        if not any(x in title.lower() for x in ('trade', 'acquire', 'land', 'deal', 'ship', 'send', 'swap')):
            continue
        block = []
        for el in h.next_elements:
            if getattr(el, 'name', None) in ('h2','h3','h4'):
                break
            if getattr(el, 'name', None) in ('p','ul'):
                block.append(el)
            if len(block) > 40:
                break
        # The full text is used only to discover teams and assets; no guesses.
        lines = []
        for el in block:
            if getattr(el, 'name', None) == 'p':
                txt = el.get_text(' ', strip=True)
                if txt and len(txt) < 220: lines.append(txt)
            elif getattr(el, 'name', None) == 'ul':
                lines.extend(li.get_text(' ', strip=True) for li in el.find_all('li', recursive=False))
        sides = {}
        active = None
        for line in lines:
            upper = line.upper().strip()
            marker = re.match(r'^([A-Z .-]+?)\s+RECEIVES\s*:', upper)
            if marker:
                active = next((code for n,code in TEAM_NAME.items() if n in marker.group(1)), None)
                if active:
                    sides.setdefault(active, [])
                continue
            if not active or not line: continue
            pick = re.search(r'\b(202[6-9]|2030)\s+(first|second|third|fourth|fifth|sixth|seventh|1st|2nd|3rd|4th|5th|6th|7th)[- ]round\s+(?:draft\s+)?pick',line,re.I)
            if pick:
                rd = {'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7,'1st':1,'2nd':2,'3rd':3,'4th':4,'5th':5,'6th':6,'7th':7}[pick.group(2).lower()]
                sides[active].append({'type':'pick','year':int(pick.group(1)),'round':rd})
            else:
                match = re.match(r'^(QB|WR|RB|TE|DT|DL|DE|EDGE|CB|S|LB|OT|OL|C|G|K|P)\s+([A-Za-z.\-\' ]+(?:Jr\.|II|III)?)$', line.strip())
                if match:
                    sides[active].append({'type':'player','name':match.group(2).strip(),'position':match.group(1)})
        if len(sides) != 2 or not all(sides.values()):
            continue
        players = [a['name'].lower() for assets in sides.values() for a in assets if a['type']=='player']
        if not players or any(n in existing_player_names for n in players):
            continue
        # Date must be explicitly discoverable. If date cannot be parsed, do not publish a fake time.
        nearby = ' '.join(x.get_text(' ',strip=True) for x in block[:3])
        monthday = re.search(r'\b(?:Sep(?:t)?\.?|Oct\.?|Nov\.?)\s+(\d{1,2})\b', nearby, re.I)
        if not monthday: continue
        month = 9 if nearby[monthday.start():].lower().startswith('sep') else 10 if nearby[monthday.start():].lower().startswith('oct') else 11
        date = f'2026-{month:02d}-{int(monthday.group(1)):02d}'
        teams = list(sides)
        new.append({'id':'official-'+date+'-'+re.sub(r'[^a-z0-9]+','-',players[0]),'date':date,'time':None,'status':'completed','headline':title,'teams':teams,'receives':sides,'grade':{teams[0]:None,teams[1]:None},'analysis':'New entry identified on the NFL official trade tracker. Editorial grading not yet published. Review linked source for conditions and pick ownership.', 'sources':[NFL]})
    return new


def enrich_profiles(trades):
    """Use public ESPN roster data. Leave any unresolved field blank, not fabricated."""
    wanted = {a['name'] for t in trades for assets in t['receives'].values() for a in assets if a['type']=='player'}
    profiles = {}
    teams = sorted({code for t in trades for code in t['teams']})
    for code in teams:
        try:
            url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{code}/roster'
            data = requests.get(url,headers=HEADERS,timeout=7).json()
            for group in data.get('athletes',[]):
                for athlete in group.get('items',[]):
                    name = athlete.get('displayName')
                    if name not in wanted:
                        continue
                    profile = profiles.setdefault(name,{})
                    if athlete.get('id'):
                        profile['id'] = athlete['id']
                    if athlete.get('jersey'):
                        profile['number'] = athlete['jersey']
                    if athlete.get('height'):
                        profile['height'] = f"{int(athlete['height'])//12}′{int(athlete['height'])%12}″"  # ESPN returns inches
                    if athlete.get('weight'):
                        profile['weight'] = str(round(athlete['weight']))+' lb'
                    if athlete.get('dateOfBirth'):
                        profile['birth'] = athlete['dateOfBirth'][:10]
                    if athlete.get('debutYear'):
                        profile['debut'] = athlete['debutYear']
                    if isinstance(athlete.get('college'),dict):
                        profile['college'] = athlete['college'].get('name')
                    if isinstance(athlete.get('headshot'),dict):
                        profile['headshot'] = athlete['headshot'].get('href')
        except Exception:
            continue
    return profiles


def refresh_cache():
    global _next_trade_check, _next_profile_check
    now = time.time()
    with _lock:
        check_trades = now >= _next_trade_check
        check_profiles = now >= _next_profile_check
        if check_trades: _next_trade_check = now + 420
        if check_profiles: _next_profile_check = now + 43200
    if not check_trades and not check_profiles:
        return
    if check_trades:
        ok = False
        new_trades = []
        try:
            nfl_soup = fetch_html(NFL)
            new_trades = parse_nfl_new(nfl_soup, state['trades'])
            ok = 'RECEIVES' in nfl_soup.get_text(' ',strip=True).upper()
        except Exception:
            pass
        try:
            cbs_soup = fetch_html(CBS)
            ok = ok or ('Nov. 10' in cbs_soup.get_text(' ',strip=True))
        except Exception:
            pass
        with _lock:
            known_ids = {t['id'] for t in state['trades']}
            state['trades'].extend(t for t in new_trades if t['id'] not in known_ids)
            state['last_checked'] = datetime.now(timezone.utc).isoformat()
            state['source_ok'] = ok
            state['note'] = ('Sources reachable. NFL transaction check every 7 minutes; player profiles refresh twice daily. Newly formatted trades are added when their full package and date can be extracted.' if ok else 'News sites unavailable or blocked this check. Showing verified trades and profiles already cached; not claiming a successful live sync.')
    if check_profiles:
        profiles = enrich_profiles(state['trades'])
        with _lock:
            state['profiles'].update(profiles)


@app.route('/')
def home():
    return send_from_directory(HERE,'index.html')


@app.route('/api/trades')
def trades():
    # A single request checks stale data synchronously; no paid cron required.
    refresh_cache()
    with _lock:
        return jsonify(copy.deepcopy(state))


@app.route('/api/health')
def health():
    return jsonify({'ok':True,'source_ok':state['source_ok'],'last_checked':state['last_checked']})


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=False,threaded=True)
