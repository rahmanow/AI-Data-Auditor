from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import json
import os
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure matplotlib
plt.rcParams.update({
    'font.family': 'sans-serif',
    'axes.edgecolor': '#e2e8f0',
    'axes.labelcolor': '#64748b',
    'text.color': '#0f172a',
    'figure.facecolor': '#ffffff',
    'axes.facecolor': '#ffffff',
})

# Models
class IssueDetail(BaseModel):
    column: str
    count: int
    percentage: float
    examples: List[Any] = []

class DataQualityResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    total_rows: int
    total_columns: int
    quality_score: float
    missing_values: List[IssueDetail]
    outliers: List[IssueDetail]
    duplicates: Dict[str, Any]
    inconsistencies: List[IssueDetail]
    column_stats: Dict[str, Any]
    charts: Dict[str, str]

class AIInsightsRequest(BaseModel):
    analysis_id: str
    analysis_data: Dict[str, Any]

class AIInsightsResponse(BaseModel):
    explanation: str
    recommendations: List[str]
    cleaning_suggestions: Dict[str, str]

class CleanDataRequest(BaseModel):
    analysis_id: str
    cleaning_options: Dict[str, str]

# In-memory storage
analysis_store: Dict[str, Any] = {}
df_store: Dict[str, pd.DataFrame] = {}

def detect_missing_values(df: pd.DataFrame) -> List[IssueDetail]:
    missing = []
    for col in df.columns:
        count = df[col].isna().sum()
        if count > 0:
            percentage = (count / len(df)) * 100
            missing.append(IssueDetail(
                column=col, count=int(count), percentage=round(percentage, 2),
                examples=[f"Row {i}" for i in df[df[col].isna()].index.tolist()[:5]]
            ))
    return missing

def detect_outliers(df: pd.DataFrame) -> List[IssueDetail]:
    outliers = []
    for col in df.select_dtypes(include=[np.number]).columns:
        data = df[col].dropna()
        if len(data) > 3:
            Q1, Q3 = data.quantile(0.25), data.quantile(0.75)
            IQR = Q3 - Q1
            mask = (data < Q1 - 1.5 * IQR) | (data > Q3 + 1.5 * IQR)
            count = mask.sum()
            if count > 0:
                outliers.append(IssueDetail(
                    column=col, count=int(count),
                    percentage=round((count / len(data)) * 100, 2),
                    examples=[round(v, 2) for v in data[mask].head(5).tolist()]
                ))
    return outliers

def detect_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    dup = df.duplicated().sum()
    return {"total_duplicates": int(dup), "percentage": round((dup / len(df)) * 100, 2) if len(df) > 0 else 0,
            "duplicate_row_indices": df[df.duplicated()].index.tolist()[:10]}

def detect_inconsistencies(df: pd.DataFrame) -> List[IssueDetail]:
    inconsistencies = []
    for col in df.columns:
        data = df[col].dropna()
        if len(data) == 0:
            continue
        if data.dtype == 'object':
            try:
                ws = (data.str.strip() != data).sum()
                if ws > 0:
                    inconsistencies.append(IssueDetail(column=col, count=int(ws),
                        percentage=round((ws / len(data)) * 100, 2), examples=["Whitespace issues"]))
            except:
                pass
    return inconsistencies

def compute_column_stats(df: pd.DataFrame) -> Dict[str, Any]:
    stats = {}
    for col in df.columns:
        s = {"dtype": str(df[col].dtype), "non_null": int(df[col].count()),
             "null": int(df[col].isna().sum()), "unique": int(df[col].nunique())}
        if np.issubdtype(df[col].dtype, np.number) and not df[col].isna().all():
            s.update({"mean": round(float(df[col].mean()), 2), "min": round(float(df[col].min()), 2),
                     "max": round(float(df[col].max()), 2)})
        stats[col] = s
    return stats

def generate_charts(df: pd.DataFrame, missing: List[IssueDetail], outliers: List[IssueDetail]) -> Dict[str, str]:
    charts = {}
    
    # Completeness
    fig, ax = plt.subplots(figsize=(5, 5))
    total, miss = df.size, df.isna().sum().sum()
    ax.pie([total - miss, miss], labels=['Valid', 'Missing'], colors=['#10b981', '#ef4444'], autopct='%1.1f%%')
    ax.set_title('Data Completeness')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    charts['completeness'] = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    
    # Summary
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['Missing', 'Outliers', 'Duplicates']
    values = [sum(m.count for m in missing), sum(o.count for o in outliers), df.duplicated().sum()]
    ax.bar(labels, values, color=['#ef4444', '#f59e0b', '#6366f1'])
    ax.set_title('Issues Summary')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    charts['summary'] = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    
    # Distributions
    num_cols = df.select_dtypes(include=[np.number]).columns[:3]
    if len(num_cols) > 0:
        fig, axes = plt.subplots(1, len(num_cols), figsize=(4 * len(num_cols), 3))
        if len(num_cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, num_cols):
            ax.hist(df[col].dropna(), bins=15, color='#2563eb', alpha=0.8)
            ax.set_title(col[:15])
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=80, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['distributions'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    return charts

def calc_score(df, missing, outliers, dups, incons):
    if df.size == 0:
        return 0
    d1 = sum(m.count for m in missing) / df.size * 30
    d2 = sum(o.count for o in outliers) / df.size * 20
    d3 = dups['total_duplicates'] / len(df) * 25 if len(df) > 0 else 0
    d4 = len(incons) * 5
    return max(0, min(100, round(100 - d1 - d2 - d3 - d4, 1)))

@app.get("/api")
@app.get("/api/")
def root():
    return {"message": "Data Quality Auditor API"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file")
    fn = file.filename.lower()
    if not any(fn.endswith(e) for e in ['.csv', '.xlsx', '.xls']):
        raise HTTPException(400, "Only CSV/Excel supported")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents)) if fn.endswith('.csv') else pd.read_excel(io.BytesIO(contents))
        if df.empty:
            raise HTTPException(400, "Empty file")
        
        missing = detect_missing_values(df)
        outliers = detect_outliers(df)
        dups = detect_duplicates(df)
        incons = detect_inconsistencies(df)
        
        result = DataQualityResult(
            filename=file.filename, total_rows=len(df), total_columns=len(df.columns),
            quality_score=calc_score(df, missing, outliers, dups, incons),
            missing_values=missing, outliers=outliers, duplicates=dups,
            inconsistencies=incons, column_stats=compute_column_stats(df),
            charts=generate_charts(df, missing, outliers)
        )
        analysis_store[result.id] = result.model_dump()
        df_store[result.id] = df
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@app.post("/api/ai-insights")
def get_ai_insights(request: AIInsightsRequest):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(500, "OPENAI_API_KEY not set")
    
    data = request.analysis_data
    prompt = f"""Analyze this data quality report:
- File: {data.get('filename')}, Rows: {data.get('total_rows')}, Score: {data.get('quality_score')}/100
- Missing: {json.dumps(data.get('missing_values', []))}
- Outliers: {json.dumps(data.get('outliers', []))}
- Duplicates: {data.get('duplicates', {})}
- Inconsistencies: {data.get('inconsistencies', [])}

Return JSON: {{"explanation": "2-3 sentences", "recommendations": ["..."], "cleaning_suggestions": {{"col": "action"}}}}"""
    
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[
                {"role": "system", "content": "Data quality expert. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=1500
        )
        text = resp.choices[0].message.content.strip()
        if '```' in text:
            text = text.split('```')[1].replace('json', '').strip()
        return AIInsightsResponse(**json.loads(text))
    except Exception as e:
        return AIInsightsResponse(explanation=f"Error: {str(e)}", recommendations=[], cleaning_suggestions={})

@app.post("/api/clean-data")
def clean_data(request: CleanDataRequest):
    if request.analysis_id not in df_store:
        raise HTTPException(404, "Analysis not found")
    
    df = df_store[request.analysis_id].copy()
    changes = []
    
    for col, action in request.cleaning_options.items():
        if col == "remove_duplicates":
            if action == "yes":
                before = len(df)
                df = df.drop_duplicates()
                changes.append(f"Removed {before - len(df)} duplicates")
            continue
        if col not in df.columns:
            continue
        if action == "drop_missing":
            before = len(df)
            df = df.dropna(subset=[col])
            changes.append(f"Dropped {before - len(df)} rows")
        elif action == "fill_mean" and np.issubdtype(df[col].dtype, np.number):
            df[col] = df[col].fillna(df[col].mean())
            changes.append(f"Filled {col} with mean")
        elif action == "fill_median" and np.issubdtype(df[col].dtype, np.number):
            df[col] = df[col].fillna(df[col].median())
            changes.append(f"Filled {col} with median")
        elif action == "cap_outliers" and np.issubdtype(df[col].dtype, np.number):
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            df[col] = df[col].clip(Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)
            changes.append(f"Capped {col} outliers")
        elif action == "strip_whitespace" and df[col].dtype == 'object':
            df[col] = df[col].str.strip()
            changes.append(f"Stripped {col}")
    
    df_store[f"{request.analysis_id}_cleaned"] = df
    return {"success": True, "changes_made": changes, "original_rows": len(df_store[request.analysis_id]),
            "cleaned_rows": len(df), "preview": df.head(20).to_dict(orient='records')}

@app.get("/api/download-cleaned/{analysis_id}")
def download_cleaned(analysis_id: str):
    key = f"{analysis_id}_cleaned"
    if key not in df_store:
        raise HTTPException(404, "Not found")
    buf = io.StringIO()
    df_store[key].to_csv(buf, index=False)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                           headers={"Content-Disposition": f"attachment; filename=cleaned.csv"})

@app.get("/api/download-report/{analysis_id}")
def download_report(analysis_id: str):
    if analysis_id not in analysis_store:
        raise HTTPException(404, "Not found")
    report = {k: v for k, v in analysis_store[analysis_id].items() if k != 'charts'}
    return StreamingResponse(iter([json.dumps(report, indent=2, default=str)]), media_type="application/json",
                           headers={"Content-Disposition": "attachment; filename=report.json"})

# Vercel serverless handler
handler = Mangum(app, lifespan="off")
