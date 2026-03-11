import { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { 
  Upload, 
  FileSpreadsheet, 
  AlertCircle, 
  CheckCircle2, 
  Download, 
  Sparkles,
  BarChart3,
  AlertTriangle,
  Copy,
  Trash2,
  Shuffle,
  Loader2,
  ChevronRight,
  Info,
  X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Quality Score Badge Component
const QualityScoreBadge = ({ score }) => {
  let colorClass = "score-poor";
  let label = "Poor";
  
  if (score >= 90) {
    colorClass = "score-excellent";
    label = "Excellent";
  } else if (score >= 70) {
    colorClass = "score-good";
    label = "Good";
  } else if (score >= 50) {
    colorClass = "score-fair";
    label = "Fair";
  }
  
  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 border font-medium ${colorClass}`}>
      <span className="text-2xl font-bold font-mono">{score}</span>
      <span className="text-sm">/100 {label}</span>
    </div>
  );
};

// Stat Card Component
const StatCard = ({ label, value, icon: Icon, color = "text-slate-600" }) => (
  <div className="border border-slate-200 bg-white p-6" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">{label}</p>
        <p className={`text-3xl font-bold font-mono ${color}`}>{value}</p>
      </div>
      <Icon className={`w-5 h-5 ${color}`} />
    </div>
  </div>
);

// Issue Card Component
const IssueCard = ({ issue, type }) => {
  const colors = {
    missing: "border-l-red-500 bg-red-50/30",
    outlier: "border-l-amber-500 bg-amber-50/30",
    inconsistency: "border-l-purple-500 bg-purple-50/30"
  };
  
  return (
    <div className={`border border-slate-200 border-l-4 ${colors[type]} p-4`} data-testid={`issue-${type}-${issue.column}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-slate-800 font-mono">{issue.column}</p>
          <p className="text-sm text-slate-600 mt-1">
            {issue.count} issues ({issue.percentage}%)
          </p>
        </div>
      </div>
      {issue.examples && issue.examples.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-200">
          <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Examples</p>
          <div className="flex flex-wrap gap-1">
            {issue.examples.map((ex, i) => (
              <span key={i} className="text-xs font-mono bg-slate-100 px-2 py-1 text-slate-600">
                {String(ex)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Upload Section Component
const UploadSection = ({ onUpload, isLoading }) => {
  const [dragOver, setDragOver] = useState(false);
  
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }, [onUpload]);
  
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) onUpload(file);
  };
  
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-900 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">Data Quality Auditor</h1>
              <p className="text-xs text-slate-500">AI-Powered Analysis</p>
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="flex-1 grid-background">
        <div className="max-w-4xl mx-auto px-8 py-20">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-semibold text-slate-900 tracking-tight mb-4">
              Analyze Your Data Quality
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Upload your CSV or Excel file and get AI-powered insights on data quality issues,
              with actionable recommendations for improvement.
            </p>
          </div>
          
          {/* Upload Zone */}
          <div
            className={`upload-zone p-20 text-center ${dragOver ? 'dragover' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            data-testid="upload-zone"
          >
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
              disabled={isLoading}
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              {isLoading ? (
                <div className="flex flex-col items-center gap-4">
                  <Loader2 className="w-16 h-16 text-blue-500 animate-spin" />
                  <p className="text-lg font-medium text-slate-700">Analyzing your data...</p>
                  <p className="text-sm text-slate-500">This may take a moment</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="w-20 h-20 bg-slate-100 flex items-center justify-center">
                    <Upload className="w-10 h-10 text-slate-400" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-slate-700">
                      Drop your file here or <span className="text-blue-600">browse</span>
                    </p>
                    <p className="text-sm text-slate-500 mt-2">
                      Supports CSV, XLSX, and XLS files
                    </p>
                  </div>
                </div>
              )}
            </label>
          </div>
          
          {/* Features */}
          <div className="grid grid-cols-3 gap-0 mt-12 border border-slate-200">
            <div className="p-6 border-r border-slate-200">
              <AlertCircle className="w-6 h-6 text-red-500 mb-3" />
              <h3 className="font-medium text-slate-800 mb-1">Issue Detection</h3>
              <p className="text-sm text-slate-600">Missing values, outliers, duplicates, inconsistencies</p>
            </div>
            <div className="p-6 border-r border-slate-200">
              <Sparkles className="w-6 h-6 text-blue-500 mb-3" />
              <h3 className="font-medium text-slate-800 mb-1">AI Insights</h3>
              <p className="text-sm text-slate-600">Natural language explanations and recommendations</p>
            </div>
            <div className="p-6">
              <CheckCircle2 className="w-6 h-6 text-emerald-500 mb-3" />
              <h3 className="font-medium text-slate-800 mb-1">Auto Cleaning</h3>
              <p className="text-sm text-slate-600">Apply fixes and download cleaned data</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// Dashboard Component
const Dashboard = ({ analysis, onReset, onGetInsights, insights, isLoadingInsights, onCleanData, cleanResult, isCleaningData }) => {
  const [selectedTab, setSelectedTab] = useState("overview");
  const [cleaningOptions, setCleaningOptions] = useState({});
  
  const handleCleaningOptionChange = (column, action) => {
    setCleaningOptions(prev => ({
      ...prev,
      [column]: action
    }));
  };
  
  const handleApplyClean = () => {
    onCleanData(cleaningOptions);
  };
  
  const handleDownloadCleaned = async () => {
    try {
      const response = await axios.get(`${API}/download-cleaned/${analysis.id}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `cleaned_data_${analysis.id}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Cleaned data downloaded successfully");
    } catch (error) {
      toast.error("Failed to download cleaned data");
    }
  };
  
  const handleDownloadReport = async () => {
    try {
      const response = await axios.get(`${API}/download-report/${analysis.id}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `quality_report_${analysis.id}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Report downloaded successfully");
    } catch (error) {
      toast.error("Failed to download report");
    }
  };
  
  const totalIssues = 
    analysis.missing_values.reduce((sum, m) => sum + m.count, 0) +
    analysis.outliers.reduce((sum, o) => sum + o.count, 0) +
    analysis.duplicates.total_duplicates +
    analysis.inconsistencies.length;
  
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-900 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">Data Quality Auditor</h1>
              <p className="text-xs text-slate-500 font-mono">{analysis.filename}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDownloadReport}
              data-testid="download-report-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Report
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onReset}
              data-testid="new-analysis-btn"
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              New Analysis
            </Button>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-8 py-8">
        {/* Summary Stats */}
        <div className="grid grid-cols-5 gap-0 border border-slate-200 bg-white mb-8" data-testid="summary-stats">
          <div className="p-6 border-r border-slate-200">
            <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Quality Score</p>
            <QualityScoreBadge score={analysis.quality_score} />
          </div>
          <StatCard label="Total Rows" value={analysis.total_rows.toLocaleString()} icon={BarChart3} />
          <StatCard label="Total Columns" value={analysis.total_columns} icon={FileSpreadsheet} />
          <StatCard label="Issues Found" value={totalIssues.toLocaleString()} icon={AlertCircle} color="text-red-600" />
          <StatCard label="Columns Clean" value={analysis.total_columns - analysis.missing_values.length} icon={CheckCircle2} color="text-emerald-600" />
        </div>
        
        {/* Tabs */}
        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-6">
          <TabsList className="bg-white border border-slate-200 p-1 h-auto">
            <TabsTrigger value="overview" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-overview">
              Overview
            </TabsTrigger>
            <TabsTrigger value="missing" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-missing">
              Missing Values ({analysis.missing_values.length})
            </TabsTrigger>
            <TabsTrigger value="outliers" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-outliers">
              Outliers ({analysis.outliers.length})
            </TabsTrigger>
            <TabsTrigger value="duplicates" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-duplicates">
              Duplicates ({analysis.duplicates.total_duplicates})
            </TabsTrigger>
            <TabsTrigger value="inconsistencies" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-inconsistencies">
              Inconsistencies ({analysis.inconsistencies.length})
            </TabsTrigger>
            <TabsTrigger value="insights" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-insights">
              <Sparkles className="w-4 h-4 mr-1" />
              AI Insights
            </TabsTrigger>
            <TabsTrigger value="clean" className="data-[state=active]:bg-slate-900 data-[state=active]:text-white px-6 py-2" data-testid="tab-clean">
              Clean Data
            </TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-2 gap-6">
              {/* Charts */}
              {analysis.charts.completeness && (
                <div className="chart-container" data-testid="chart-completeness">
                  <img src={`data:image/png;base64,${analysis.charts.completeness}`} alt="Data Completeness" />
                </div>
              )}
              {analysis.charts.summary && (
                <div className="chart-container" data-testid="chart-summary">
                  <img src={`data:image/png;base64,${analysis.charts.summary}`} alt="Issues Summary" />
                </div>
              )}
            </div>
            {analysis.charts.distributions && (
              <div className="chart-container" data-testid="chart-distributions">
                <img src={`data:image/png;base64,${analysis.charts.distributions}`} alt="Column Distributions" />
              </div>
            )}
            
            {/* Column Statistics */}
            <div className="border border-slate-200 bg-white" data-testid="column-stats">
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="font-semibold text-slate-900">Column Statistics</h3>
              </div>
              <ScrollArea className="h-96">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Type</th>
                      <th>Non-Null</th>
                      <th>Unique</th>
                      <th>Mean</th>
                      <th>Min</th>
                      <th>Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(analysis.column_stats).map(([col, stats]) => (
                      <tr key={col}>
                        <td className="font-medium">{col}</td>
                        <td>{stats.dtype}</td>
                        <td>{stats.non_null_count}</td>
                        <td>{stats.unique_count}</td>
                        <td>{stats.mean ?? '-'}</td>
                        <td>{stats.min ?? '-'}</td>
                        <td>{stats.max ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollArea>
            </div>
          </TabsContent>
          
          {/* Missing Values Tab */}
          <TabsContent value="missing" className="animate-fade-in">
            {analysis.missing_values.length === 0 ? (
              <div className="border border-slate-200 bg-white p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-800">No Missing Values</p>
                <p className="text-slate-600">Your dataset is complete with no missing values.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {analysis.charts.missing && (
                  <div className="chart-container" data-testid="chart-missing">
                    <img src={`data:image/png;base64,${analysis.charts.missing}`} alt="Missing Values" />
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  {analysis.missing_values.map((issue, i) => (
                    <IssueCard key={i} issue={issue} type="missing" />
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
          
          {/* Outliers Tab */}
          <TabsContent value="outliers" className="animate-fade-in">
            {analysis.outliers.length === 0 ? (
              <div className="border border-slate-200 bg-white p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-800">No Outliers Detected</p>
                <p className="text-slate-600">All numeric values are within expected ranges.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {analysis.charts.outliers && (
                  <div className="chart-container" data-testid="chart-outliers">
                    <img src={`data:image/png;base64,${analysis.charts.outliers}`} alt="Outliers" />
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  {analysis.outliers.map((issue, i) => (
                    <IssueCard key={i} issue={issue} type="outlier" />
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
          
          {/* Duplicates Tab */}
          <TabsContent value="duplicates" className="animate-fade-in">
            {analysis.duplicates.total_duplicates === 0 ? (
              <div className="border border-slate-200 bg-white p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-800">No Duplicates Found</p>
                <p className="text-slate-600">All rows in your dataset are unique.</p>
              </div>
            ) : (
              <div className="border border-slate-200 bg-white p-6" data-testid="duplicates-info">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-indigo-100 flex items-center justify-center flex-shrink-0">
                    <Copy className="w-6 h-6 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">
                      {analysis.duplicates.total_duplicates} Duplicate Rows Found
                    </h3>
                    <p className="text-slate-600 mt-1">
                      {analysis.duplicates.percentage}% of your dataset contains duplicate rows.
                    </p>
                    {analysis.duplicates.duplicate_row_indices.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm text-slate-500 mb-2">Duplicate Row Indices (first 10):</p>
                        <div className="flex flex-wrap gap-2">
                          {analysis.duplicates.duplicate_row_indices.map((idx, i) => (
                            <span key={i} className="text-sm font-mono bg-slate-100 px-3 py-1">
                              Row {idx}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </TabsContent>
          
          {/* Inconsistencies Tab */}
          <TabsContent value="inconsistencies" className="animate-fade-in">
            {analysis.inconsistencies.length === 0 ? (
              <div className="border border-slate-200 bg-white p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-800">No Inconsistencies Found</p>
                <p className="text-slate-600">Your data types and formats are consistent.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {analysis.inconsistencies.map((issue, i) => (
                  <IssueCard key={i} issue={issue} type="inconsistency" />
                ))}
              </div>
            )}
          </TabsContent>
          
          {/* AI Insights Tab */}
          <TabsContent value="insights" className="animate-fade-in">
            {!insights ? (
              <div className="border border-slate-200 bg-white p-12 text-center">
                <Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 mb-2">Get AI-Powered Insights</h3>
                <p className="text-slate-600 mb-6 max-w-md mx-auto">
                  Let AI analyze your data quality issues and provide actionable recommendations for improvement.
                </p>
                <Button 
                  onClick={onGetInsights} 
                  disabled={isLoadingInsights}
                  className="bg-blue-600 hover:bg-blue-700"
                  data-testid="get-insights-btn"
                >
                  {isLoadingInsights ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Generate AI Insights
                    </>
                  )}
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Explanation */}
                <div className="border border-slate-200 bg-white p-6" data-testid="ai-explanation">
                  <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    <Info className="w-5 h-5 text-blue-500" />
                    Analysis Summary
                  </h3>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{insights.explanation}</p>
                </div>
                
                {/* Recommendations */}
                {insights.recommendations && insights.recommendations.length > 0 && (
                  <div className="border border-slate-200 bg-white p-6" data-testid="ai-recommendations">
                    <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                      Recommendations
                    </h3>
                    <ul className="space-y-3">
                      {insights.recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-3">
                          <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                          <span className="text-slate-700">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Cleaning Suggestions */}
                {insights.cleaning_suggestions && Object.keys(insights.cleaning_suggestions).length > 0 && (
                  <div className="border border-slate-200 bg-white p-6" data-testid="ai-cleaning-suggestions">
                    <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                      <Trash2 className="w-5 h-5 text-amber-500" />
                      Column-Specific Cleaning Suggestions
                    </h3>
                    <div className="space-y-3">
                      {Object.entries(insights.cleaning_suggestions).map(([col, suggestion], i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200">
                          <span className="font-mono text-sm font-medium text-slate-800">{col}</span>
                          <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0 mt-1" />
                          <span className="text-sm text-slate-600">{suggestion}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>
          
          {/* Clean Data Tab */}
          <TabsContent value="clean" className="animate-fade-in">
            <div className="grid grid-cols-2 gap-6">
              {/* Cleaning Options */}
              <div className="border border-slate-200 bg-white" data-testid="cleaning-options">
                <div className="px-6 py-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-900">Configure Cleaning Options</h3>
                  <p className="text-sm text-slate-500 mt-1">Select how to handle issues for each column</p>
                </div>
                <ScrollArea className="h-96">
                  <div className="p-6 space-y-4">
                    {/* Missing Values */}
                    {analysis.missing_values.length > 0 && (
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-red-500" />
                          Missing Values
                        </p>
                        {analysis.missing_values.map((issue, i) => (
                          <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100">
                            <span className="font-mono text-sm">{issue.column}</span>
                            <Select
                              value={cleaningOptions[issue.column] || ""}
                              onValueChange={(v) => handleCleaningOptionChange(issue.column, v)}
                            >
                              <SelectTrigger className="w-40 h-8 text-xs" data-testid={`clean-option-${issue.column}`}>
                                <SelectValue placeholder="Select action" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="drop_missing">Drop rows</SelectItem>
                                <SelectItem value="fill_mean">Fill with mean</SelectItem>
                                <SelectItem value="fill_median">Fill with median</SelectItem>
                                <SelectItem value="fill_mode">Fill with mode</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Outliers */}
                    {analysis.outliers.length > 0 && (
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                          Outliers
                        </p>
                        {analysis.outliers.map((issue, i) => (
                          <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100">
                            <span className="font-mono text-sm">{issue.column}</span>
                            <Select
                              value={cleaningOptions[issue.column] || ""}
                              onValueChange={(v) => handleCleaningOptionChange(issue.column, v)}
                            >
                              <SelectTrigger className="w-40 h-8 text-xs" data-testid={`clean-outlier-${issue.column}`}>
                                <SelectValue placeholder="Select action" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="cap_outliers">Cap outliers</SelectItem>
                                <SelectItem value="remove_outliers">Remove rows</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Duplicates */}
                    {analysis.duplicates.total_duplicates > 0 && (
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                          <Copy className="w-4 h-4 text-indigo-500" />
                          Duplicates
                        </p>
                        <div className="flex items-center justify-between py-2">
                          <span className="text-sm">{analysis.duplicates.total_duplicates} duplicate rows</span>
                          <Select
                            value={cleaningOptions["remove_duplicates"] || ""}
                            onValueChange={(v) => handleCleaningOptionChange("remove_duplicates", v)}
                          >
                            <SelectTrigger className="w-40 h-8 text-xs" data-testid="clean-duplicates">
                              <SelectValue placeholder="Select action" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="yes">Remove duplicates</SelectItem>
                              <SelectItem value="no">Keep all</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                    
                    {/* Inconsistencies */}
                    {analysis.inconsistencies.filter(i => i.examples[0]?.includes('whitespace')).length > 0 && (
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
                          <Shuffle className="w-4 h-4 text-purple-500" />
                          Whitespace Issues
                        </p>
                        {analysis.inconsistencies
                          .filter(i => i.examples[0]?.includes('whitespace'))
                          .map((issue, i) => (
                            <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100">
                              <span className="font-mono text-sm">{issue.column}</span>
                              <Select
                                value={cleaningOptions[issue.column] || ""}
                                onValueChange={(v) => handleCleaningOptionChange(issue.column, v)}
                              >
                                <SelectTrigger className="w-40 h-8 text-xs" data-testid={`clean-whitespace-${issue.column}`}>
                                  <SelectValue placeholder="Select action" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="strip_whitespace">Strip whitespace</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          ))}
                      </div>
                    )}
                    
                    <Button 
                      className="w-full mt-4"
                      onClick={handleApplyClean}
                      disabled={Object.keys(cleaningOptions).length === 0 || isCleaningData}
                      data-testid="apply-cleaning-btn"
                    >
                      {isCleaningData ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Cleaning...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4 mr-2" />
                          Apply Cleaning
                        </>
                      )}
                    </Button>
                  </div>
                </ScrollArea>
              </div>
              
              {/* Cleaning Result */}
              <div className="border border-slate-200 bg-white" data-testid="cleaning-result">
                <div className="px-6 py-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-900">Cleaning Result</h3>
                </div>
                {!cleanResult ? (
                  <div className="p-12 text-center">
                    <Trash2 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500">Select cleaning options and apply to see results</p>
                  </div>
                ) : (
                  <div className="p-6">
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="p-4 bg-slate-50 border border-slate-200">
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">Original Rows</p>
                        <p className="text-2xl font-bold font-mono text-slate-700">{cleanResult.original_rows}</p>
                      </div>
                      <div className="p-4 bg-emerald-50 border border-emerald-200">
                        <p className="text-xs uppercase tracking-wider text-emerald-600 mb-1">Cleaned Rows</p>
                        <p className="text-2xl font-bold font-mono text-emerald-700">{cleanResult.cleaned_rows}</p>
                      </div>
                    </div>
                    
                    <div className="mb-6">
                      <p className="text-xs uppercase tracking-wider text-slate-500 mb-3">Changes Applied</p>
                      <ul className="space-y-2">
                        {cleanResult.changes_made.map((change, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                            {change}
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <Button 
                      className="w-full bg-emerald-600 hover:bg-emerald-700"
                      onClick={handleDownloadCleaned}
                      data-testid="download-cleaned-btn"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download Cleaned Data
                    </Button>
                    
                    {/* Preview */}
                    {cleanResult.preview && cleanResult.preview.length > 0 && (
                      <div className="mt-6">
                        <p className="text-xs uppercase tracking-wider text-slate-500 mb-3">Preview (first 20 rows)</p>
                        <ScrollArea className="h-64 border border-slate-200">
                          <table className="data-table text-xs">
                            <thead>
                              <tr>
                                {Object.keys(cleanResult.preview[0]).map(col => (
                                  <th key={col}>{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {cleanResult.preview.map((row, i) => (
                                <tr key={i}>
                                  {Object.values(row).map((val, j) => (
                                    <td key={j}>{String(val ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </ScrollArea>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

function App() {
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [insights, setInsights] = useState(null);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [cleanResult, setCleanResult] = useState(null);
  const [isCleaningData, setIsCleaningData] = useState(false);
  
  const handleUpload = async (file) => {
    setIsLoading(true);
    setInsights(null);
    setCleanResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setAnalysis(response.data);
      toast.success(`Analysis complete! Quality score: ${response.data.quality_score}/100`);
    } catch (error) {
      const message = error.response?.data?.detail || "Failed to analyze file";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleGetInsights = async () => {
    if (!analysis) return;
    
    setIsLoadingInsights(true);
    try {
      const response = await axios.post(`${API}/ai-insights`, {
        analysis_id: analysis.id,
        analysis_data: analysis
      });
      
      setInsights(response.data);
      toast.success("AI insights generated successfully");
    } catch (error) {
      const message = error.response?.data?.detail || "Failed to get AI insights";
      toast.error(message);
    } finally {
      setIsLoadingInsights(false);
    }
  };
  
  const handleCleanData = async (cleaningOptions) => {
    if (!analysis) return;
    
    setIsCleaningData(true);
    try {
      const response = await axios.post(`${API}/clean-data`, {
        analysis_id: analysis.id,
        cleaning_options: cleaningOptions
      });
      
      setCleanResult(response.data);
      toast.success("Data cleaned successfully");
    } catch (error) {
      const message = error.response?.data?.detail || "Failed to clean data";
      toast.error(message);
    } finally {
      setIsCleaningData(false);
    }
  };
  
  const handleReset = () => {
    setAnalysis(null);
    setInsights(null);
    setCleanResult(null);
  };
  
  return (
    <>
      <Toaster position="top-right" richColors />
      {!analysis ? (
        <UploadSection onUpload={handleUpload} isLoading={isLoading} />
      ) : (
        <Dashboard 
          analysis={analysis}
          onReset={handleReset}
          onGetInsights={handleGetInsights}
          insights={insights}
          isLoadingInsights={isLoadingInsights}
          onCleanData={handleCleanData}
          cleanResult={cleanResult}
          isCleaningData={isCleaningData}
        />
      )}
    </>
  );
}

export default App;
