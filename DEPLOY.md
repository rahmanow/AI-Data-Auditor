# Data Quality Auditor - Vercel Deployment

## Quick Deploy to Vercel

### Option 1: One-Click Deploy
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/YOUR_REPO)

### Option 2: Manual Deploy

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Deploy on Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Configure environment variables:
     - `OPENAI_API_KEY` = your OpenAI API key

3. **Done!** Your app will be live at `https://your-project.vercel.app`

## Project Structure
```
├── api/
│   └── index.py          # FastAPI backend (Vercel serverless)
├── frontend/
│   ├── src/              # React frontend
│   ├── public/
│   └── package.json
├── requirements.txt      # Python dependencies
└── vercel.json          # Vercel configuration
```

## Environment Variables
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key for AI insights |

## Local Development
```bash
# Backend
cd api && pip install -r ../requirements.txt
uvicorn index:app --reload --port 8001

# Frontend
cd frontend && yarn install && yarn start
```

## Features
- Upload CSV/Excel files for analysis
- Automatic detection of data quality issues
- AI-powered insights using GPT-4
- Data cleaning with multiple strategies
- Download cleaned data and reports
