# PainSignal

AI-powered pain point intelligence for founders. Scrapes Reddit, analyzes with Groq, surfaces business opportunities.

## Run locally

```bash
pip install -r requirements.txt
# Fill .env with GROQ_API_KEY
python run_pipeline.py                 # Generate fresh data
uvicorn backend.main:app --reload      # Start API server
```

Then open `index.html` in your browser.

## Deploy (free)

- **Backend**: Render (free tier, sleeps after 15min idle)
- **Frontend**: Vercel (free, always-on)

See deploy instructions in the deployment guide.
