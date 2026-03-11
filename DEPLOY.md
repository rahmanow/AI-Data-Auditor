# Data Quality Auditor - Vercel Deployment

## Deploy to Vercel

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for Vercel"
git push origin main
```

### Step 2: Deploy on Vercel
1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **"Add New Project"**
3. Import your GitHub repository
4. **Important**: Add environment variable:
   - Name: `OPENAI_API_KEY`
   - Value: `your-openai-api-key`
5. Click **Deploy**

### Step 3: Done!
Your app will be live at `https://your-project.vercel.app`

## Project Structure
```
├── api/
│   └── index.py          # FastAPI backend (serverless)
├── frontend/
│   ├── src/              # React app
│   └── package.json
├── requirements.txt      # Python dependencies
└── vercel.json          # Vercel config
```

## Environment Variables Required
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for AI insights |

## Local Development
```bash
# Install Python deps
pip install -r requirements.txt

# Install frontend deps
cd frontend && yarn install

# Run frontend
yarn start

# Run backend (separate terminal)
cd api && uvicorn index:app --reload --port 8001
```
