from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math
import swisseph as swe

app = FastAPI(title='AI Astrologer Calculation API', version='1.0.0')

SIGNS=['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
NAK=[('Ashwini','Ketu'),('Bharani','Venus'),('Krittika','Sun'),('Rohini','Moon'),('Mrigashira','Mars'),('Ardra','Rahu'),('Punarvasu','Jupiter'),('Pushya','Saturn'),('Ashlesha','Mercury'),('Magha','Ketu'),('Purva Phalguni','Venus'),('Uttara Phalguni','Sun'),('Hasta','Moon'),('Chitra','Mars'),('Swati','Rahu'),('Vishakha','Jupiter'),('Anuradha','Saturn'),('Jyeshtha','Mercury'),('Mula','Ketu'),('Purva Ashadha','Venus'),('Uttara Ashadha','Sun'),('Shravana','Moon'),('Dhanishtha','Mars'),('Shatabhisha','Rahu'),('Purva Bhadrapada','Jupiter'),('Uttara Bhadrapada','Saturn'),('Revati','Mercury')]
DASHA_ORDER=['Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury']
DASHA_YEARS={'Ketu':7,'Venus':20,'Sun':6,'Moon':10,'Mars':7,'Rahu':18,'Jupiter':16,'Saturn':19,'Mercury':17}
PLANETS={'Sun':swe.SUN,'Moon':swe.MOON,'Mercury':swe.MERCURY,'Venus':swe.VENUS,'Mars':swe.MARS,'Jupiter':swe.JUPITER,'Saturn':swe.SATURN,'Rahu':swe.MEAN_NODE}

class ChartRequest(BaseModel):
    date: str = Field(description='YYYY-MM-DD')
    time: str = Field(description='HH:MM or HH:MM:SS, local birth time')
    timezone: str = Field(description='IANA timezone, e.g. Asia/Kolkata')
    latitude: float
    longitude: float
    node_type: str = 'mean'

class TransitRequest(BaseModel):
    date: str
    time: str = '12:00'
    timezone: str = 'UTC'


def norm(x): return x % 360.0

def pos_info(lon, asc_sign=None):
    lon=norm(lon); si=int(lon//30); deg=lon%30
    nidx=min(26,int(lon/(40/3)))
    within=lon-nidx*(40/3)
    pada=min(4,int(within/(10/3))+1)
    out={'longitude':round(lon,6),'sign':SIGNS[si],'degree_in_sign':round(deg,6),'nakshatra':NAK[nidx][0],'nakshatra_lord':NAK[nidx][1],'pada':pada}
    if asc_sign is not None: out['house']=((si-asc_sign)%12)+1
    return out

def navamsa_sign(lon):
    si=int(norm(lon)//30); deg=norm(lon)%30; part=min(8,int(deg/(10/3)))
    if si in [0,3,6,9]: start=si
    elif si in [1,4,7,10]: start=(si+8)%12
    else: start=(si+4)%12
    return (start+part)%12

def dashamsa_sign(lon):
    si=int(norm(lon)//30); deg=norm(lon)%30; part=min(9,int(deg/3))
    start=si if si%2==0 else (si+8)%12
    return (start+part)%12

def jd_from_local(date_s,time_s,tz_s):
    try:
        d=datetime.fromisoformat(f'{date_s}T{time_s}')
        local=d.replace(tzinfo=ZoneInfo(tz_s)); utc=local.astimezone(timezone.utc)
    except Exception as e: raise HTTPException(400,f'Invalid date/time/timezone: {e}')
    hour=utc.hour+utc.minute/60+utc.second/3600+utc.microsecond/3.6e9
    return swe.julday(utc.year,utc.month,utc.day,hour,swe.GREG_CAL), utc

def add_years_fraction(dt, years):
    # Dasha convention approximation using tropical-year length; boundaries should be treated as computational, not civil-year anniversaries.
    from datetime import timedelta
    return dt + timedelta(days=years*365.2425)

def vimshottari(moon_lon,birth_utc):
    span=40/3; idx=min(26,int(norm(moon_lon)/span)); nak_lord=NAK[idx][1]
    within=norm(moon_lon)-idx*span; remaining=1-within/span
    first_years=DASHA_YEARS[nak_lord]*remaining
    seq_start=DASHA_ORDER.index(nak_lord)
    periods=[]; start=birth_utc; dur=first_years
    for k in range(12):
        lord=DASHA_ORDER[(seq_start+k)%9]
        if k>0: dur=DASHA_YEARS[lord]
        end=add_years_fraction(start,dur)
        periods.append({'lord':lord,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'years':round(dur,6)})
        start=end
    return {'birth_nakshatra':NAK[idx][0],'starting_lord':nak_lord,'balance_fraction':round(remaining,8),'mahadashas':periods}

def antardashas(md):
    lord=md['lord']; start=datetime.fromisoformat(md['start_utc']); md_years=md['years']; base=DASHA_ORDER.index(lord); arr=[]
    for k in range(9):
        ad=DASHA_ORDER[(base+k)%9]; years=md_years*DASHA_YEARS[ad]/120
        end=add_years_fraction(start,years); arr.append({'lord':ad,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'years':round(years,6)}); start=end
    return arr

def compute(req):
    jd,utc=jd_from_local(req.date,req.time,req.timezone)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags=swe.FLG_SWIEPH|swe.FLG_SIDEREAL|swe.FLG_SPEED
    planet_ids=dict(PLANETS); planet_ids['Rahu']=swe.TRUE_NODE if req.node_type.lower()=='true' else swe.MEAN_NODE
    raw={}
    for name,pid in planet_ids.items(): raw[name]=norm(swe.calc_ut(jd,pid,flags)[0][0])
    raw['Ketu']=norm(raw['Rahu']+180)
    # Swiss Ephemeris sidereal houses; 'W' = whole sign houses. ascmc[0] gives sidereal ascendant under sidereal mode.
    cusps,ascmc=swe.houses_ex(jd,req.latitude,req.longitude,b'W',swe.FLG_SIDEREAL)
    asc=norm(ascmc[0]); asc_sign=int(asc//30)
    planets={n:pos_info(l,asc_sign) for n,l in raw.items()}
    ascinfo=pos_info(asc); ascinfo['house']=1
    d1={'ascendant':ascinfo,'planets':planets}
    d9={'ascendant_sign':SIGNS[navamsa_sign(asc)],'planets':{n:SIGNS[navamsa_sign(l)] for n,l in raw.items()}}
    d10={'ascendant_sign':SIGNS[dashamsa_sign(asc)],'planets':{n:SIGNS[dashamsa_sign(l)] for n,l in raw.items()}}
    vd=vimshottari(raw['Moon'],utc)
    now=datetime.now(timezone.utc); current_md=None; current_ad=None
    for md in vd['mahadashas']:
        if datetime.fromisoformat(md['start_utc']) <= now < datetime.fromisoformat(md['end_utc']):
            current_md=md; ads=antardashas(md)
            for ad in ads:
                if datetime.fromisoformat(ad['start_utc']) <= now < datetime.fromisoformat(ad['end_utc']): current_ad=ad; break
            md['antardashas']=ads; break
    return {'calculation_metadata':{'zodiac':'sidereal','ayanamsha':'Lahiri/Chitrapaksha','houses':'whole sign','node_type':req.node_type,'birth_utc':utc.isoformat(),'julian_day_ut':jd,'engine':'Swiss Ephemeris'},'d1':d1,'d9':d9,'d10':d10,'vimshottari':{**vd,'current_mahadasha':current_md,'current_antardasha':current_ad}}

@app.get('/')
def health(): return {'status':'ok','service':'AI Astrologer Calculation API'}

@app.post('/vedic-chart')
def vedic_chart(req:ChartRequest): return compute(req)

@app.post('/transits')
def transits(req:TransitRequest):
    # Geocentric sidereal planetary positions; houses intentionally omitted because transit question may not have a geographic location.
    jd,utc=jd_from_local(req.date,req.time,req.timezone); swe.set_sid_mode(swe.SIDM_LAHIRI); flags=swe.FLG_SWIEPH|swe.FLG_SIDEREAL|swe.FLG_SPEED
    out={}
    for n,pid in PLANETS.items(): out[n]=pos_info(swe.calc_ut(jd,pid,flags)[0][0])
    out['Ketu']=pos_info(out['Rahu']['longitude']+180)
    return {'date_utc':utc.isoformat(),'ayanamsha':'Lahiri/Chitrapaksha','planets':out}
