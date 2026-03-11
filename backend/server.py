from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
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
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure matplotlib for consistent styling
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

# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class IssueDetail(BaseModel):
    column: str
    count: int
    percentage: float
    examples: List[Any] = []

class DataQualityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
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

# Helper functions for data analysis
def detect_missing_values(df: pd.DataFrame) -> List[IssueDetail]:
    missing = []
    for col in df.columns:
        count = df[col].isna().sum()
        if count > 0:
            percentage = (count / len(df)) * 100
            examples = df[df[col].isna()].index.tolist()[:5]
            missing.append(IssueDetail(
                column=col,
                count=int(count),
                percentage=round(percentage, 2),
                examples=[f"Row {i}" for i in examples]
            ))
    return missing

def detect_outliers(df: pd.DataFrame) -> List[IssueDetail]:
    outliers = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        data = df[col].dropna()
        if len(data) > 3:
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outlier_mask = (data < lower) | (data > upper)
            count = outlier_mask.sum()
            if count > 0:
                percentage = (count / len(data)) * 100
                outlier_values = data[outlier_mask].head(5).tolist()
                outliers.append(IssueDetail(
                    column=col,
                    count=int(count),
                    percentage=round(percentage, 2),
                    examples=[round(v, 2) if isinstance(v, float) else v for v in outlier_values]
                ))
    return outliers

def detect_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    duplicate_rows = df.duplicated().sum()
    duplicate_indices = df[df.duplicated()].index.tolist()[:10]
    return {
        "total_duplicates": int(duplicate_rows),
        "percentage": round((duplicate_rows / len(df)) * 100, 2) if len(df) > 0 else 0,
        "duplicate_row_indices": duplicate_indices
    }

def detect_inconsistencies(df: pd.DataFrame) -> List[IssueDetail]:
    inconsistencies = []
    for col in df.columns:
        data = df[col].dropna()
        if len(data) == 0:
            continue
        
        # Check for mixed types
        types = data.apply(lambda x: type(x).__name__).unique()
        if len(types) > 1:
            type_counts = data.apply(lambda x: type(x).__name__).value_counts()
            inconsistencies.append(IssueDetail(
                column=col,
                count=int(len(types)),
                percentage=round((type_counts.iloc[1:].sum() / len(data)) * 100, 2) if len(type_counts) > 1 else 0,
                examples=[f"Types found: {', '.join(types)}"]
            ))
        
        # Check for whitespace issues in strings
        if data.dtype == 'object':
            whitespace_issues = data.str.strip() != data
            whitespace_count = whitespace_issues.sum() if hasattr(whitespace_issues, 'sum') else 0
            if whitespace_count > 0:
                inconsistencies.append(IssueDetail(
                    column=col,
                    count=int(whitespace_count),
                    percentage=round((whitespace_count / len(data)) * 100, 2),
                    examples=["Leading/trailing whitespace detected"]
                ))
    return inconsistencies

def compute_column_stats(df: pd.DataFrame) -> Dict[str, Any]:
    stats_dict = {}
    for col in df.columns:
        # Handle pandas 3.0+ StringDtype compatibility
        dtype_str = str(df[col].dtype)
        if 'StringDtype' in dtype_str or 'string' in dtype_str:
            dtype_str = 'object'
        
        col_stats = {
            "dtype": dtype_str,
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
    
    # Quality overview pie chart
    fig, ax = plt.subplots(figsize=(6, 6))
    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    valid_cells = total_cells - missing_cells
    ax.pie([valid_cells, missing_cells], 
           labels=['Valid', 'Missing'], 
           colors=['#10b981', '#ef4444'],
           autopct='%1.1f%%',
           startangle=90)
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
        bars = ax.barh(cols, counts, color='#ef4444', edgecolor='#dc2626')
        ax.set_xlabel('Missing Count', fontsize=10, color='#64748b')
        ax.set_title('Missing Values by Column', fontsize=14, fontweight='bold', color='#0f172a')
        ax.invert_yaxis()
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                   str(count), va='center', fontsize=9, color='#64748b')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['missing'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    # Numeric distribution histogram
    numeric_cols = df.select_dtypes(include=[np.number]).columns[:4]
    if len(numeric_cols) > 0:
        fig, axes = plt.subplots(1, min(4, len(numeric_cols)), figsize=(12, 4))
        if len(numeric_cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, numeric_cols):
            data = df[col].dropna()
            ax.hist(data, bins=20, color='#2563eb', edgecolor='#1d4ed8', alpha=0.8)
            ax.set_title(col[:20], fontsize=10, fontweight='bold', color='#0f172a')
            ax.tick_params(labelsize=8)
        plt.suptitle('Numeric Column Distributions', fontsize=14, fontweight='bold', color='#0f172a')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['distributions'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    # Outliers visualization
    if outliers:
        fig, ax = plt.subplots(figsize=(10, 5))
        cols = [o.column[:15] for o in outliers[:10]]
        percentages = [o.percentage for o in outliers[:10]]
        bars = ax.barh(cols, percentages, color='#f59e0b', edgecolor='#d97706')
        ax.set_xlabel('Outlier Percentage (%)', fontsize=10, color='#64748b')
        ax.set_title('Outlier Distribution by Column', fontsize=14, fontweight='bold', color='#0f172a')
        ax.invert_yaxis()
        for bar, pct in zip(bars, percentages):
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
                   f'{pct:.1f}%', va='center', fontsize=9, color='#64748b')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        charts['outliers'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
    
    # Issue summary bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    issue_types = ['Missing Values', 'Outliers', 'Duplicates', 'Inconsistencies']
    issue_counts = [
        sum(m.count for m in missing),
        sum(o.count for o in outliers),
        df.duplicated().sum(),
        len([i for i in detect_inconsistencies(df)])
    ]
    colors = ['#ef4444', '#f59e0b', '#6366f1', '#8b5cf6']
    bars = ax.bar(issue_types, issue_counts, color=colors, edgecolor=['#dc2626', '#d97706', '#4f46e5', '#7c3aed'])
    ax.set_ylabel('Count', fontsize=10, color='#64748b')
    ax.set_title('Data Quality Issues Summary', fontsize=14, fontweight='bold', color='#0f172a')
    for bar, count in zip(bars, issue_counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
               str(count), ha='center', fontsize=10, color='#64748b')
    plt.xticks(rotation=15)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    charts['summary'] = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    
    return charts

def calculate_quality_score(df: pd.DataFrame, missing: List[IssueDetail], outliers: List[IssueDetail], duplicates: Dict, inconsistencies: List[IssueDetail]) -> float:
    total_cells = df.size
    if total_cells == 0:
        return 0.0
    
    # Deductions
    missing_deduction = sum(m.count for m in missing) / total_cells * 30
    outlier_deduction = sum(o.count for o in outliers) / total_cells * 20
    duplicate_deduction = duplicates['total_duplicates'] / len(df) * 25 if len(df) > 0 else 0
    inconsistency_deduction = len(inconsistencies) * 5
    
    score = 100 - missing_deduction - outlier_deduction - duplicate_deduction - inconsistency_deduction
    return max(0, min(100, round(score, 1)))

# Store analysis results in memory for simplicity
analysis_store: Dict[str, Any] = {}
df_store: Dict[str, pd.DataFrame] = {}

@api_router.get("/")
async def root():
    return {"message": "Data Quality Auditor API"}

@api_router.post("/upload", response_model=DataQualityResult)
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV or Excel file for analysis"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        contents = await file.read()
        
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")
        
        # Force convert all string/StringDtype columns to object dtype for pandas 3.0+ compatibility
        for col in df.columns:
            if df[col].dtype.name == 'string' or 'StringDtype' in str(type(df[col].dtype)):
                df[col] = df[col].astype('object')
        
        # Perform analysis
        missing = detect_missing_values(df)
        outliers = detect_outliers(df)
        duplicates = detect_duplicates(df)
        inconsistencies = detect_inconsistencies(df)
        column_stats = compute_column_stats(df)
        charts = generate_charts(df, missing, outliers)
        quality_score = calculate_quality_score(df, missing, outliers, duplicates, inconsistencies)
        
        result = DataQualityResult(
            filename=file.filename,
            total_rows=len(df),
            total_columns=len(df.columns),
            quality_score=quality_score,
            missing_values=missing,
            outliers=outliers,
            duplicates=duplicates,
            inconsistencies=inconsistencies,
            column_stats=column_stats,
            charts=charts
        )
        
        # Store for later use
        analysis_store[result.id] = result.model_dump()
        df_store[result.id] = df
        
        return result
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="The file appears to be empty or corrupted")
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.post("/ai-insights", response_model=AIInsightsResponse)
async def get_ai_insights(request: AIInsightsRequest):
    """Get AI-powered explanations and recommendations"""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        analysis_data = request.analysis_data
        
        # Prepare context for AI
        context = f"""
You are a data quality expert. Analyze the following data quality report and provide:
1. A clear explanation of the main issues found
2. Specific recommendations for fixing each issue
3. Suggestions for cleaning the data

Data Quality Report:
- File: {analysis_data.get('filename', 'Unknown')}
- Total Rows: {analysis_data.get('total_rows', 0)}
- Total Columns: {analysis_data.get('total_columns', 0)}
- Quality Score: {analysis_data.get('quality_score', 0)}/100

Missing Values Issues:
{json.dumps(analysis_data.get('missing_values', []), indent=2)}

Outliers Detected:
{json.dumps(analysis_data.get('outliers', []), indent=2)}

Duplicates:
{json.dumps(analysis_data.get('duplicates', {}), indent=2)}

Inconsistencies:
{json.dumps(analysis_data.get('inconsistencies', []), indent=2)}

Please provide your analysis in the following JSON format:
{{
    "explanation": "A 2-3 paragraph explanation of the data quality issues",
    "recommendations": ["recommendation 1", "recommendation 2", ...],
    "cleaning_suggestions": {{"column_name": "suggested action", ...}}
}}
"""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"dqa-{request.analysis_id}",
            system_message="You are a data quality expert. Provide clear, actionable insights for improving data quality. Always respond with valid JSON."
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=context)
        response = await chat.send_message(user_message)
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed = json.loads(response_text.strip())
            return AIInsightsResponse(
                explanation=parsed.get('explanation', 'Unable to generate explanation'),
                recommendations=parsed.get('recommendations', []),
                cleaning_suggestions=parsed.get('cleaning_suggestions', {})
            )
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw response
            return AIInsightsResponse(
                explanation=response,
                recommendations=["Review the data quality issues identified above", "Address missing values first", "Remove or cap outliers based on business context"],
                cleaning_suggestions={}
            )
            
    except Exception as e:
        logging.error(f"Error getting AI insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting AI insights: {str(e)}")

@api_router.post("/clean-data")
async def clean_data(request: CleanDataRequest):
    """Apply cleaning operations and return cleaned data"""
    analysis_id = request.analysis_id
    cleaning_options = request.cleaning_options
    
    if analysis_id not in df_store:
        raise HTTPException(status_code=404, detail="Analysis not found. Please upload the file again.")
    
    df = df_store[analysis_id].copy()
    changes_made = []
    
    # Apply cleaning based on options
    for column, action in cleaning_options.items():
        if column not in df.columns:
            continue
            
        if action == "drop_missing":
            before_count = len(df)
            df = df.dropna(subset=[column])
            changes_made.append(f"Dropped {before_count - len(df)} rows with missing values in {column}")
            
        elif action == "fill_mean":
            if np.issubdtype(df[column].dtype, np.number):
                mean_val = df[column].mean()
                count = df[column].isna().sum()
                df[column] = df[column].fillna(mean_val)
                changes_made.append(f"Filled {count} missing values in {column} with mean ({mean_val:.2f})")
                
        elif action == "fill_median":
            if np.issubdtype(df[column].dtype, np.number):
                median_val = df[column].median()
                count = df[column].isna().sum()
                df[column] = df[column].fillna(median_val)
                changes_made.append(f"Filled {count} missing values in {column} with median ({median_val:.2f})")
                
        elif action == "fill_mode":
            mode_val = df[column].mode()
            if len(mode_val) > 0:
                count = df[column].isna().sum()
                df[column] = df[column].fillna(mode_val.iloc[0])
                changes_made.append(f"Filled {count} missing values in {column} with mode ({mode_val.iloc[0]})")
                
        elif action == "cap_outliers":
            if np.issubdtype(df[column].dtype, np.number):
                Q1 = df[column].quantile(0.25)
                Q3 = df[column].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                count = ((df[column] < lower) | (df[column] > upper)).sum()
                df[column] = df[column].clip(lower=lower, upper=upper)
                changes_made.append(f"Capped {count} outliers in {column} to range [{lower:.2f}, {upper:.2f}]")
                
        elif action == "remove_outliers":
            if np.issubdtype(df[column].dtype, np.number):
                Q1 = df[column].quantile(0.25)
                Q3 = df[column].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                before_count = len(df)
                df = df[(df[column] >= lower) & (df[column] <= upper)]
                changes_made.append(f"Removed {before_count - len(df)} rows with outliers in {column}")
                
        elif action == "strip_whitespace":
            if df[column].dtype == 'object':
                df[column] = df[column].str.strip()
                changes_made.append(f"Stripped whitespace from {column}")
    
    # Remove duplicates if requested
    if cleaning_options.get("remove_duplicates") == "yes":
        before_count = len(df)
        df = df.drop_duplicates()
        changes_made.append(f"Removed {before_count - len(df)} duplicate rows")
    
    # Store cleaned DataFrame
    df_store[f"{analysis_id}_cleaned"] = df
    
    return {
        "success": True,
        "changes_made": changes_made,
        "original_rows": len(df_store[analysis_id]),
        "cleaned_rows": len(df),
        "preview": df.head(20).to_dict(orient='records')
    }

@api_router.get("/download-cleaned/{analysis_id}")
async def download_cleaned(analysis_id: str):
    """Download the cleaned dataset as CSV"""
    cleaned_id = f"{analysis_id}_cleaned"
    
    if cleaned_id not in df_store:
        raise HTTPException(status_code=404, detail="Cleaned data not found. Please run cleaning first.")
    
    df = df_store[cleaned_id]
    
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=cleaned_data_{analysis_id}.csv"
    return response

@api_router.get("/download-report/{analysis_id}")
async def download_report(analysis_id: str):
    """Download the analysis report as JSON"""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    report = analysis_store[analysis_id].copy()
    # Remove chart data from report (too large)
    report['charts'] = {k: "base64_encoded_image" for k in report.get('charts', {}).keys()}
    
    return StreamingResponse(
        iter([json.dumps(report, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=quality_report_{analysis_id}.json"}
    )

@api_router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get a stored analysis result"""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_store[analysis_id]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
