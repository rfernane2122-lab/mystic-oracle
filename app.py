import math
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='static')
CORS(app)

OPENCAGE_KEY = os.environ.get('OPENCAGE_KEY', '')
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_KEY', '')

def julian_day(year, month, day, hour=12.0):
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + hour/24.0 + B - 1524.5

def normalize(deg):
    return deg % 360

def T_from_jd(jd):
    return (jd - 2451545.0) / 36525.0

def sun_longitude(T):
    L0 = 280.46646 + 36000.76983*T + 0.0003032*T**2
    M = math.radians(normalize(357.52911 + 35999.05029*T - 0.0001537*T**2))
    C = (1.914602 - 0.004817*T - 0.000014*T**2)*math.sin(M)
    C += (0.019993 - 0.000101*T)*math.sin(2*M) + 0.000289*math.sin(3*M)
    return normalize(L0 + C)

def moon_longitude(T):
    L = normalize(218.3164477 + 481267.88123421*T - 0.0015786*T**2)
    M = math.radians(normalize(357.5291092 + 35999.0502909*T))
    Mp = math.radians(normalize(134.9634114 + 477198.8676313*T))
    D = math.radians(normalize(297.8502042 + 445267.1115168*T))
    F = math.radians(normalize(93.2720993 + 483202.0175273*T))
    lon = L + 6.288750*math.sin(Mp) + 1.274018*math.sin(2*D-Mp)
    lon += 0.658309*math.sin(2*D) + 0.213616*math.sin(2*Mp)
    lon -= 0.185596*math.sin(M) - 0.114336*math.sin(2*F)
    lon += 0.058793*math.sin(2*D-2*Mp) + 0.057212*math.sin(2*D-M-Mp)
    lon += 0.053320*math.sin(2*D+Mp) + 0.045874*math.sin(2*D-M)
    return normalize(lon)

def mercury_longitude(T):
    L = 252.250906 + 149472.6746358*T
    M = math.radians(normalize(174.7947870 + 149472.5153380*T))
    return normalize(L + 6.74*math.sin(M) + 0.45*math.sin(2*M))

def venus_longitude(T):
    L = 181.979801 + 58517.8156760*T
    M = math.radians(normalize(19.994980 + 58517.8156760*T))
    return normalize(L + 0.7758*math.sin(M) + 0.0033*math.sin(2*M))

def mars_longitude(T):
    L = 355.433 + 19140.2993313*T
    M = math.radians(normalize(19.3730 + 19140.2993313*T))
    return normalize(L + 10.691*math.sin(M) + 0.623*math.sin(2*M) + 0.050*math.sin(3*M))

def jupiter_longitude(T):
    L = 34.351519 + 3034.9056606*T
    M = math.radians(normalize(20.020200 + 3034.9056606*T))
    return normalize(L + 5.5549*math.sin(M) + 0.1683*math.sin(2*M))

def saturn_longitude(T):
    L = 50.077444 + 1222.1137943*T
    M = math.radians(normalize(317.020200 + 1222.1137943*T))
    return normalize(L + 6.3585*math.sin(M) + 0.2204*math.sin(2*M))

def uranus_longitude(T):
    L = 314.055005 + 428.4669983*T
    M = math.radians(normalize(142.5905 + 428.4669983*T))
    return normalize(L + 5.3042*math.sin(M) + 0.1534*math.sin(2*M))

def neptune_longitude(T):
    L = 304.348665 + 218.4862002*T
    M = math.radians(normalize(256.225 + 218.4862002*T))
    return normalize(L + 1.0302*math.sin(M))

def pluto_longitude(T):
    P = math.radians(normalize(238.96 + 144.9600*T))
    return normalize(238.9508 + 144.9600*T - 19.799*math.sin(P) + 19.848*math.cos(P))

def north_node(T):
    return normalize(125.044522 - 1934.136261*T + 0.0020708*T**2)

def obliquity(T):
    return 23.439291 - 0.013004*T

def sidereal_time(jd, longitude):
    T = T_from_jd(jd)
    GMST = 280.46061837 + 360.98564736629*(jd-2451545.0) + 0.000387933*T**2
    return normalize(GMST + longitude)

def calc_ascendant(jd, lat, lon_geo):
    T = T_from_jd(jd)
    LST = sidereal_time(jd, lon_geo)
    e = math.radians(obliquity(T))
    RAMC = math.radians(LST)
    lat_r = math.radians(lat)
    return normalize(math.degrees(math.atan2(math.cos(RAMC), -(math.sin(RAMC)*math.cos(e) + math.tan(lat_r)*math.sin(e)))))

def calc_mc(jd, lon_geo):
    T = T_from_jd(jd)
    LST = sidereal_time(jd, lon_geo)
    e = math.radians(obliquity(T))
    LST_r = math.radians(LST)
    return normalize(math.degrees(math.atan2(math.sin(LST_r), math.cos(LST_r)*math.cos(e))))

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
ELEMENTS = {"Aries":"Fire","Taurus":"Earth","Gemini":"Air","Cancer":"Water","Leo":"Fire","Virgo":"Earth","Libra":"Air","Scorpio":"Water","Sagittarius":"Fire","Capricorn":"Earth","Aquarius":"Air","Pisces":"Water"}
NAKSHATRA_NAMES = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
NAKSHATRA_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
HEAVENLY_STEMS = ["Yang Wood","Yin Wood","Yang Fire","Yin Fire","Yang Earth","Yin Earth","Yang Metal","Yin Metal","Yang Water","Yin Water"]
EARTHLY_BRANCHES = ["Rat","Ox","Tiger","Rabbit","Dragon","Snake","Horse","Goat","Monkey","Rooster","Dog","Pig"]

def sign_from_lon(lon):
    return SIGNS[int(lon/30)], round(lon % 30, 2)

def ayanamsha(T):
    return 23.85 + 0.013972*((T*36525 + 2451545 - 2396758) / 365.25)

def get_nakshatra(moon_sid):
    idx = int(moon_sid / (360/27))
    pada = int((moon_sid % (360/27)) / (360/108)) + 1
    return {"name": NAKSHATRA_NAMES[idx], "pada": pada, "lord": NAKSHATRA_LORDS[idx]}

def life_path(year, month, day):
    digits = [int(d) for d in f"{year}{month:02d}{day:02d}"]
    total = sum(digits)
    while total > 9 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    meanings = {1:"The Leader",2:"The Diplomat",3:"The Creator",4:"The Builder",5:"The Free Spirit",6:"The Nurturer",7:"The Seeker",8:"The Achiever",9:"The Humanitarian",11:"The Spiritual Messenger",22:"The Master Builder",33:"The Master Teacher"}
    return {"number": total, "label": meanings.get(total, "Mystical Path")}

def compute_chart(year, month, day, hour, lat, lon_geo):
    jd = julian_day(year, month, day, hour)
    T = T_from_jd(jd)
    planets_lon = {
        "Sun": sun_longitude(T), "Moon": moon_longitude(T),
        "Mercury": mercury_longitude(T), "Venus": venus_longitude(T),
        "Mars": mars_longitude(T), "Jupiter": jupiter_longitude(T),
        "Saturn": saturn_longitude(T), "Uranus": uranus_longitude(T),
        "Neptune": neptune_longitude(T), "Pluto": pluto_longitude(T),
        "North Node": north_node(T)
    }
    planets_lon["South Node"] = normalize(planets_lon["North Node"] + 180)
    asc = calc_ascendant(jd, lat, lon_geo)
    mc = calc_mc(jd, lon_geo)
    planets_lon["Ascendant"] = asc
    planets_lon["Midheaven"] = mc
    planets = {}
    for name, lon in planets_lon.items():
        sign, deg = sign_from_lon(lon)
        house = int(normalize(lon - asc) / 30) + 1
        planets[name] = {"longitude": round(lon, 4), "sign": sign, "degree": deg, "house": house, "element": ELEMENTS.get(sign, "")}
    ayan = ayanamsha(T)
    moon_sid = normalize(planets_lon["Moon"] - ayan)
    sun_sid_sign = SIGNS[int(normalize(planets_lon["Sun"] - ayan) / 30)]
    moon_sid_sign = SIGNS[int(moon_sid / 30)]
    nak = get_nakshatra(moon_sid)
    year_off = ((year - 1984) % 60 + 60) % 60
    chinese = {"stem": HEAVENLY_STEMS[year_off % 10], "branch": EARTHLY_BRANCHES[year_off % 12]}
    day_off = int(jd - 2451549.5) % 60
    day_pillar = {"stem": HEAVENLY_STEMS[day_off % 10], "branch": EARTHLY_BRANCHES[day_off % 12]}
    lp = life_path(year, month, day)
    el_count = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    for p in ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]:
        el = planets[p]["element"]
        if el:
            el_count[el] += 1
    return {
        "planets": planets, "elements": el_count,
        "sun_sign": planets["Sun"]["sign"], "moon_sign": planets["Moon"]["sign"],
        "rising_sign": planets["Ascendant"]["sign"], "mc_sign": planets["Midheaven"]["sign"],
        "vedic": {"nakshatra": nak, "sun_sign": sun_sid_sign, "moon_sign": moon_sid_sign, "ayanamsha": round(ayan, 2)},
        "chinese": {"year": chinese, "day": day_pillar},
        "saju": {"day_master": day_pillar["stem"]},
        "numerology": {"life_path": lp}
    }

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/geocode')
def geocode():
    city = request.args.get('city', '')
    if not city:
        return jsonify({"error": "No city provided"}), 400
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={requests.utils.quote(city)}&key={OPENCAGE_KEY}&limit=6&no_annotations=1&language=en"
        r = requests.get(url, timeout=5)
        data = r.json()
        results = []
        for item in data.get("results", []):
            geo = item.get("geometry", {})
            comp = item.get("components", {})
            label = item.get("formatted", city)
            results.append({"label": label, "lat": geo.get("lat"), "lon": geo.get("lng"), "country": comp.get("country", "")})
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chart', methods=['POST'])
def chart():
    data = request.json
    try:
        result = compute_chart(
            int(data['year']), int(data['month']), int(data['day']),
            float(data['hour']), float(data['lat']), float(data['lon'])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/oracle', methods=['POST'])
def oracle():
    data = request.json
    messages = data.get('messages', [])
    system = data.get('system', '')
    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_KEY,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1000,
                'system': system,
                'messages': messages
            },
            timeout=30
        )
        result = r.json()
        print("Anthropic status:", r.status_code)
        print("Anthropic response:", result)
        if 'error' in result:
            return jsonify({"text": f"API Error: {result['error']['message']}"})
        return jsonify({"text": result.get('content', [{}])[0].get('text', 'The oracle is silent.')})
    except Exception as e:
        print("Oracle error:", str(e))
        return jsonify({"text": f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
