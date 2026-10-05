# AI Astrologer v1

A zero-cost prototype calculation backend for a reusable Vedic Astrology consultant inside ChatGPT.

## What this is
This is **not a website**. It is a small API that a ChatGPT Action calls invisibly. ChatGPT remains the user interface.

## Calculation standard
- Sidereal zodiac
- Lahiri / Chitrapaksha ayanamsha
- Whole-sign houses
- Mean Rahu by default (true node optional)
- D1, D9, D10
- Vimshottari Mahadasha and Antardasha
- Sidereal transit endpoint

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open `http://127.0.0.1:8000/docs`.

## Deploy free on Render
1. Put these files in a Git repository.
2. In Render choose **New > Web Service** and connect the repository.
3. Render can read `render.yaml`, or use:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Choose the Free plan.
5. Copy the resulting `https://...onrender.com` URL.
6. Replace `REPLACE-WITH-YOUR-RENDER-SERVICE` in `openapi.yaml` with the service hostname.

## Connect to ChatGPT
In the GPT/assistant editor's Actions area:
1. Create a new Action.
2. Authentication: None for private prototype use.
3. Paste `openapi.yaml`.
4. Test `calculateVedicChart`.
5. Test `calculateSiderealTransits`.

## Privacy note
Birth data is sensitive personal data. v1 deliberately stores **nothing** in a database. Requests are calculated and returned. Hosting providers can still retain ordinary service/request logs, so do not describe this prototype as zero-retention unless logging is explicitly configured accordingly.

## Important licensing note
Swiss Ephemeris / Python wrappers carry Swiss Ephemeris licensing obligations. This prototype is intended for private/testing use. Review the applicable AGPL/professional-license terms before public/commercial distribution.
