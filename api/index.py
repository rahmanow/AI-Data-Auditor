from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import json
import os
from openai import AsyncOpenAI

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
    'font.sans-serif': ['DejaVu Sans', 'Arial'],
    'axes.edgecolor': '#e2e8f0',
    'axes.labelcolor': '#64748b',
    'xtick.color': '#64748b',
    'ytick.color': '#64748b',
    'text.color': '#0f172a',
    'figure.facecolor': '#ffffff',
    'axes.facecolor': '#ffffff',
    'grid.color': '#f1f5f9',
    'axes.grid': True,
    'grid.alpha': 0.5
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# Helper functions
def detect_missing_values(df: pd.DataFrame) -> List[IssueDetail]:
    missing = []
    for col in df.columns:
        count = df[col].isna().sum()
        if count > 0:
            percentage = (count / len(df)) * 100
            examples = df[df[col].isna()].index.tolist()[:5]
            missing.append(IssueDetail(
                column=col, count=int(count), percentage=round(percentage, 2),
                examples=[f"Row {i}" for i in examples]
            ))
    return missing

def detect_outliers(df: pd.DataFrame) -> List[IssueDetail]:
    outliers = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        data = df[col].dropna()
        if len(data) > 3:
            Q1, Q3 = data.quantile(0.25), data.quantile(0.75)
            IQR = Q3 - Q1
            lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
            outlier_mask = (data < lower) | (data > upper)
            count = outlier_mask.sum()
            if count > 0:
                outliers.append(IssueDetail(
                    column=col, count=int(count),
                    percentage=round((count / len(data)) * 100, 2),
                    examples=[round(v, 2) if isinstance(v, float) else v for v in data[outlier_mask].head(5).tolist()]
                ))
    return outliers

def detect_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    duplicate_rows = df.duplicated().sum()
    return {
        "total_duplicates": int(duplicate_rows),
        "percentage": round((duplicate_rows / len(df)) * 100, 2) if len(df) > 0 else 0,
        "duplicate_row_indices": df[df.duplicated()].index.tolist()[:10]
    }

def detect_inconsistencies(df: pd.DataFrame) -> List[IssueDetail]:
    inconsistencies = []
    for col in df.columns:
        data = df[col].dropna()
        if len(data) == 0:
            continue
        types = data.apply(lambda x: type(x).__name__).unique()
        if len(types) > 1:
            inconsistencies.append(IssueDetail(
                column=col, count=int(len(types)), percentage=0,
                examples=[f"Types found: {', '.join(types)}"]
            ))
        if data.dtype == 'object':
            try:
                whitespace_issues = data.str.strip() != data
                whitespace_count = whitespace_issues.sum() if hasattr(whitespace_issues, 'sum') else 0
                if whitespace_count > 0:
                    inconsistencies.append(IssueDetail(
                        column=col, count=int(whitespace_count),
                        percentage=round((whitespace_count / len(data)) * 100, 2),
                        examples=["Leading/trailing whitespace detected"]
                    ))
            except:
                pass
    return inconsistencies

def compute_column_stats(df: pd.DataFrame) -> Dict[str, Any]:
    stats_dict = {}
    for col in df.columns:
        col_stats = {
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].count()),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique())
        }
        if np.issubdtype(df[col].dtype, np.number):
            col_stats.update({
                "mean": round(float(df[col].mean()), 2) if not df[col].isna().all() else None,
                "std": round(float(df[col].std()), 2) if not df[col].isna().all() else None,
                "min": round(float(df[col].min()), 2) if not df[col].isna().all() else None,
                "max": round(float(df[col].max()), 2) if not df[col].isna().all() else None,
                "median": round(float(df[col].median()), 2) if not df[col].isna().all() else None
            })
        stats_dict[col] = col_stats
    return stats_dict

def generate_charts(df: pd.DataFrame, missing: List[IssueDetail], outliers: List[IssueDetail]) -> Dict[str, str]:
    charts = {}
    
    # Completeness pie chart
    fig, ax = plt.subplots(figsize=(6, 6))
    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    ax.pie([total_cells - missing_cells, missing_cells], labels=['Valid', 'Missing'], 
           colors=['#10b981', '#ef4444'], autopct='%1.1f%%', startangle=90)
    ax.set_title('Data Completeness Overview', fontsize=14, fontweight='bold', color='#0f172a')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    charts['completeness'] = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    
    # Missing values bar chart
    if missing:
        fig, ax = plt.subplots(figsize=(10, 5))
        cols = [m.column[:15] for m in missing[:10]]
        counts = [m.count for m in missing[:10]]
        ax.barh(cols, counts, color='#ef4444', edgecolor='#dc2626')
        ax.set_xlabel('Missing Count', fontsize=10, color='#64748b')
        ax.set_title('Missing Values by Column', fontsize=14, fontweight='bold', color='#0f172a')
        ax.invert_yaxis()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['missing'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    # Distributions
    numeric_cols = df.select_dtypes(include=[np.number]).columns[:4]
    if len(numeric_cols) > 0:
        fig, axes = plt.subplots(1, min(4, len(numeric_cols)), figsize=(12, 4))
        if len(numeric_cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, numeric_cols):
            ax.hist(df[col].dropna(), bins=20, color='#2563eb', edgecolor='#1d4ed8', alpha=0.8)
            ax.set_title(col[:20], fontsize=10, fontweight='bold', color='#0f172a')
        plt.suptitle('Numeric Column Distributions', fontsize=14, fontweight='bold', color='#0f172a')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['distributions'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    # Summary bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    issue_types = ['Missing', 'Outliers', 'Duplicates', 'Inconsistencies']
    issue_counts = [sum(m.count for m in missing), sum(o.count for o in outliers),
                   df.duplicated().sum(), len(detect_inconsistencies(df))]
    ax.bar(issue_types, issue_counts, color=['#ef4444', '#f59e0b', '#6366f1', '#8b5cf6'])
    ax.set_title('Data Quality Issues Summary', fontsize=14, fontweight='bold', color='#0f172a')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    charts['summary'] = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    
    return charts

def calculate_quality_score(df, missing, outliers, duplicates, inconsistencies) -> float:
    total_cells = df.size
    if total_cells == 0:
        return 0.0
    missing_ded = sum(m.count for m in missing) / total_cells * 30
    outlier_ded = sum(o.count for o in outliers) / total_cells * 20
    dup_ded = duplicates['total_duplicates'] / len(df) * 25 if len(df) > 0 else 0
    incon_ded = len(inconsistencies) * 5
    return max(0, min(100, round(100 - missing_ded - outlier_ded - dup_ded - incon_ded, 1)))

# Routes
@app.get("/api")
async def root():
    return {"message": "Data Quality Auditor API"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents)) if filename.endswith('.csv') else pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")
        
        missing = detect_missing_values(df)
        outliers = detect_outliers(df)
        duplicates = detect_duplicates(df)
        inconsistencies = detect_inconsistencies(df)
        
        result = DataQualityResult(
            filename=file.filename,
            total_rows=len(df),
            total_columns=len(df.columns),
            quality_score=calculate_quality_score(df, missing, outliers, duplicates, inconsistencies),
            missing_values=missing,
            outliers=outliers,
            duplicates=duplicates,
            inconsistencies=inconsistencies,
            column_stats=compute_column_stats(df),
            charts=generate_charts(df, missing, outliers)
        )
        
        analysis_store[result.id] = result.model_dump()
        df_store[result.id] = df
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/api/ai-insights")
async def get_ai_insights(request: AIInsightsRequest):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    analysis_data = request.analysis_data
    context = f"""Analyze this data quality report and provide JSON response:
- File: {analysis_data.get('filename')}, Rows: {analysis_data.get('total_rows')}, Columns: {analysis_data.get('total_columns')}
- Quality Score: {analysis_data.get('quality_score')}/100
- Missing Values: {json.dumps(analysis_data.get('missing_values', []))}
- Outliers: {json.dumps(analysis_data.get('outliers', []))}
- Duplicates: {json.dumps(analysis_data.get('duplicates', {}))}
- Inconsistencies: {json.dumps(analysis_data.get('inconsistencies', []))}

Respond with JSON: {{"explanation": "...", "recommendations": ["..."], "cleaning_suggestions": {{"column": "action"}}}}"""
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data quality expert. Respond with valid JSON only."},
                {"role": "user", "content": context}
            ],
            temperature=0.7, max_tokens=2000
        )
        
        text = response.choices[0].message.content.strip()
        if text.startswith('```'): text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        parsed = json.loads(text)
        return AIInsightsResponse(**parsed)
    except Exception as e:
        return AIInsightsResponse(
            explanation=f"Error generating insights: {str(e)}",
            recommendations=["Check your data manually"],
            cleaning_suggestions={}
        )

@app.post("/api/clean-data")
async def clean_data(request: CleanDataRequest):
    if request.analysis_id not in df_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    df = df_store[request.analysis_id].copy()
    changes = []
    
    for col, action in request.cleaning_options.items():
        if col not in df.columns and col != "remove_duplicates":
            continue
        if action == "drop_missing":
            before = len(df)
            df = df.dropna(subset=[col])
            changes.append(f"Dropped {before - len(df)} rows with missing {col}")
        elif action == "fill_mean" and np.issubdtype(df[col].dtype, np.number):
            df[col] = df[col].fillna(df[col].mean())
            changes.append(f"Filled missing {col} with mean")
        elif action == "fill_median" and np.issubdtype(df[col].dtype, np.number):
            df[col] = df[col].fillna(df[col].median())
            changes.append(f"Filled missing {col} with median")
        elif action == "fill_mode":
            mode = df[col].mode()
            if len(mode) > 0:
                df[col] = df[col].fillna(mode.iloc[0])
                changes.append(f"Filled missing {col} with mode")
        elif action == "cap_outliers" and np.issubdtype(df[col].dtype, np.number):
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            df[col] = df[col].clip(lower=Q1-1.5*IQR, upper=Q3+1.5*IQR)
            changes.append(f"Capped outliers in {col}")
        elif action == "strip_whitespace" and df[col].dtype == 'object':
            df[col] = df[col].str.strip()
            changes.append(f"Stripped whitespace from {col}")
    
    if request.cleaning_options.get("remove_duplicates") == "yes":
        before = len(df)
        df = df.drop_duplicates()
        changes.append(f"Removed {before - len(df)} duplicates")
    
    df_store[f"{request.analysis_id}_cleaned"] = df
    return {
        "success": True, "changes_made": changes,
        "original_rows": len(df_store[request.analysis_id]),
        "cleaned_rows": len(df),
        "preview": df.head(20).to_dict(orient='records')
    }

@app.get("/api/download-cleaned/{analysis_id}")
async def download_cleaned(analysis_id: str):
    if f"{analysis_id}_cleaned" not in df_store:
        raise HTTPException(status_code=404, detail="Cleaned data not found")
    stream = io.StringIO()
    df_store[f"{analysis_id}_cleaned"].to_csv(stream, index=False)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                           headers={"Content-Disposition": f"attachment; filename=cleaned_{analysis_id}.csv"})

@app.get("/api/download-report/{analysis_id}")
async def download_report(analysis_id: str):
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    report = {k: v for k, v in analysis_store[analysis_id].items() if k != 'charts'}
    return StreamingResponse(iter([json.dumps(report, indent=2, default=str)]),
                           media_type="application/json",
                           headers={"Content-Disposition": f"attachment; filename=report_{analysis_id}.json"})

# Vercel handler
handler = app
