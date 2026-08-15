import React, { useState, useRef, useCallback } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Layers,
  ArrowRight,
  RefreshCw,
  Loader2,
  Database,
  Table,
  Check
} from 'lucide-react';
import { BrandLogo } from '../../components/icons/BrandLogo';
import {
  uploadFile,
  selectSheet,
  formatBytes,
  ApiError,
  type DatasetMetadataResponse
} from '../../lib/api';
import { useDataset } from '../../store/datasetStore';

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.json', '.parquet'];
const ACCEPT_STRING = ACCEPTED_EXTENSIONS.join(',');

const PROGRESS_STEPS = [
  'Reading dataset...',
  'Detecting columns...',
  'Calculating statistics...',
  'Preparing AI context...'
];

export interface UploadScreenProps {
  onDatasetLoaded?: (dataset: DatasetMetadataResponse) => void;
  onContinueToOverview?: (dataset: DatasetMetadataResponse) => void;
}

type UploadState = 'idle' | 'processing' | 'sheet_picker' | 'success' | 'error';

export const UploadScreen: React.FC<UploadScreenProps> = ({
  onDatasetLoaded,
  onContinueToOverview
}) => {
  const { setDataset, sessionError } = useDataset();
  const [state, setState] = useState<UploadState>('idle');
  const [isDragging, setIsDragging] = useState<boolean>(false);
  
  // File details & API responses
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<DatasetMetadataResponse | null>(null);
  const [selectedSheetName, setSelectedSheetName] = useState<string>('');
  
  // Progress states
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [progressPercent, setProgressPercent] = useState<number>(0);

  // Error handling
  const [errorDetails, setErrorDetails] = useState<{ message: string; code?: string; guidance?: string; hint?: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  // Run progress sequence with realistic delays
  const runProgressSteps = useCallback(async (startStep: number, endStep: number) => {
    for (let i = startStep; i <= endStep; i++) {
      setCurrentStepIndex(i);
      const percent = Math.round(((i + 1) / PROGRESS_STEPS.length) * 100);
      setProgressPercent(percent);
      await sleep(550); // Reasonable delay matching actual processing visual steps
    }
  }, []);

  const handleFileProcess = async (file: File) => {
    // Basic client validation
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(fileExt)) {
      setErrorDetails({
        message: `Unsupported file extension '${fileExt}'`,
        code: 'UNSUPPORTED_FILE_TYPE',
        guidance: 'This file format is not supported. Please upload a file in .csv, .xlsx, .xls, .json, or .parquet format.'
      });
      setState('error');
      return;
    }

    if (file.size === 0) {
      setErrorDetails({
        message: 'The selected file is empty (0 bytes)',
        code: 'EMPTY_FILE',
        guidance: 'The uploaded file contains no data. Please check your data export and select a valid non-empty file.'
      });
      setState('error');
      return;
    }

    setSelectedFile(file);
    setState('processing');
    setErrorDetails(null);
    setCurrentStepIndex(0);
    setProgressPercent(15);

    try {
      // Step 0: Reading dataset...
      const apiPromise = uploadFile(file);
      await runProgressSteps(0, 0);

      const res = await apiPromise;
      setMetadata(res);

      if (res.requires_sheet_selection && res.sheet_names && res.sheet_names.length > 0) {
        // Multi-sheet excel -> Prompt sheet picker
        setSelectedSheetName(res.sheet_names[0]);
        setState('sheet_picker');
        return;
      }

      // Single sheet / CSV / JSON -> run remaining steps
      await runProgressSteps(1, 3);
      setDataset(res);
      setState('success');
      if (onDatasetLoaded) {
        onDatasetLoaded(res);
      }
    } catch (err: any) {
      console.error('File upload error:', err);
      if (err instanceof ApiError) {
        setErrorDetails({
          message: err.message,
          code: err.errorCode,
          guidance: err.userGuidance
        });
      } else {
        setErrorDetails({
          message: err.message || 'An unexpected error occurred during dataset processing.',
          code: 'UPLOAD_FAILED',
          guidance: 'Please verify your file format and network connection, then try again.'
        });
      }
      setState('error');
    }
  };

  const handleSheetConfirm = async () => {
    if (!metadata || !selectedSheetName) return;

    setState('processing');
    setErrorDetails(null);

    try {
      // Run step 1..3 for sheet selection parsing
      const selectPromise = selectSheet(metadata.file_id, selectedSheetName);
      await runProgressSteps(1, 3);

      const finalRes = await selectPromise;
      setMetadata(finalRes);
      setDataset(finalRes);
      setState('success');
      if (onDatasetLoaded) {
        onDatasetLoaded(finalRes);
      }
    } catch (err: any) {
      console.error('Select sheet error:', err);
      if (err instanceof ApiError) {
        setErrorDetails({
          message: err.message,
          code: err.errorCode,
          guidance: err.userGuidance
        });
      } else {
        setErrorDetails({
          message: err.message || 'Failed to parse the selected Excel sheet.',
          code: 'SHEET_PARSE_FAILED',
          guidance: 'Try selecting a different sheet or re-exporting the workbook.'
        });
      }
      setState('error');
    }
  };

  // Drag & drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileProcess(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFileProcess(file);
    }
  };

  const resetUpload = () => {
    setState('idle');
    setSelectedFile(null);
    setMetadata(null);
    setErrorDetails(null);
    setCurrentStepIndex(0);
    setProgressPercent(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-4 px-2 md:px-6">
      {/* Session Expired Banner */}
      {sessionError && (
        <div className="mb-6 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300 text-sm font-medium flex items-center justify-center gap-2 max-w-2xl mx-auto shadow-xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />
          <span>{sessionError}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-light/60 border border-primary/20 text-primary text-xs font-semibold mb-3">
          <BrandLogo size={16} />
          <span>Data Ingestion Engine</span>
        </div>
        <h1 className="text-display-sm md:text-display-md text-ink tracking-tight font-bold mb-2">
          Upload your dataset
        </h1>
        <p className="text-body-md text-muted max-w-xl mx-auto">
          Import your data for automated schema detection, summary analytics, and instant AI insights.
        </p>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept={ACCEPT_STRING}
        className="hidden"
      />

      {/* STATE 1: IDLE / DROPZONE */}
      {state === 'idle' && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            relative group cursor-pointer rounded-2xl border-2 border-dashed p-8 md:p-12
            flex flex-col items-center justify-center text-center transition-all duration-200
            bg-surface-card shadow-xs hover:shadow-md
            ${isDragging
              ? 'border-primary bg-primary-light/30 scale-[1.01]'
              : 'border-border hover:border-primary/60 hover:bg-surface-soft/60'
            }
          `}
        >
          <div className="w-16 h-16 rounded-full bg-primary-light/70 border border-primary/20 flex items-center justify-center text-primary mb-4 group-hover:scale-110 transition-transform">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h3 className="text-title-md text-ink font-semibold mb-1">
            Drag and drop your file here
          </h3>
          <p className="text-body-sm text-muted mb-4">
            or <span className="text-primary font-semibold underline underline-offset-2">click to browse</span> from your device
          </p>

          {/* Format Tags */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-2">
            {ACCEPTED_EXTENSIONS.map((ext) => (
              <span
                key={ext}
                className="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-canvas text-muted border border-hairline"
              >
                {ext}
              </span>
            ))}
          </div>

          <p className="text-caption text-muted-soft mt-6">
            Supported formats: CSV, Excel (.xlsx, .xls), JSON, Parquet (Max size: 100MB)
          </p>
        </div>
      )}

      {/* STATE 2: PROCESSING & PROGRESS STEPS */}
      {state === 'processing' && (
        <div className="rounded-2xl border border-hairline bg-surface-card p-8 shadow-xs max-w-xl mx-auto">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-hairline">
            <div className="w-10 h-10 rounded-lg bg-primary-light/60 flex items-center justify-center text-primary">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="text-title-sm text-ink truncate font-semibold">
                {selectedFile?.name || 'Dataset'}
              </h4>
              <p className="text-caption text-muted">
                {selectedFile ? formatBytes(selectedFile.size) : 'Processing'}
              </p>
            </div>
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between items-center text-caption font-medium text-muted mb-2">
              <span>Analysis Progress</span>
              <span className="text-primary font-bold">{progressPercent}%</span>
            </div>
            <div className="w-full h-2.5 bg-canvas rounded-full overflow-hidden border border-hairline">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Step Sequence Checklist */}
          <div className="space-y-3.5">
            {PROGRESS_STEPS.map((stepText, idx) => {
              const isDone = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;

              return (
                <div
                  key={stepText}
                  className={`
                    flex items-center gap-3 text-sm transition-all duration-200
                    ${isDone
                      ? 'text-ink font-medium'
                      : isCurrent
                      ? 'text-primary font-semibold'
                      : 'text-muted-soft'
                    }
                  `}
                >
                  <div className="shrink-0">
                    {isDone ? (
                      <CheckCircle2 className="w-5 h-5 text-success fill-success-bg" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border border-border-strong flex items-center justify-center text-caption text-muted-soft">
                        {idx + 1}
                      </div>
                    )}
                  </div>
                  <span>{stepText}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* STATE 3: MULTI-SHEET EXCEL SELECTION */}
      {state === 'sheet_picker' && metadata && (
        <div className="rounded-2xl border border-hairline bg-surface-card p-6 md:p-8 shadow-xs max-w-xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-warning-bg text-warning flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-title-md text-ink font-bold">Select Excel Sheet</h3>
              <p className="text-body-sm text-muted">
                Multiple sheets detected in <span className="font-semibold text-ink">{metadata.filename}</span>.
              </p>
            </div>
          </div>

          <p className="text-body-sm text-ink mb-4">
            Choose which sheet you would like to analyze:
          </p>

          {/* Sheet options list */}
          <div className="space-y-2 mb-6 max-h-60 overflow-y-auto pr-1">
            {metadata.sheet_names?.map((sheet) => {
              const isSelected = selectedSheetName === sheet;
              return (
                <button
                  key={sheet}
                  onClick={() => setSelectedSheetName(sheet)}
                  className={`
                    w-full flex items-center justify-between p-3.5 rounded-xl border text-left text-sm font-medium transition-all
                    ${isSelected
                      ? 'border-primary bg-primary-light/40 text-primary font-semibold shadow-2xs'
                      : 'border-hairline bg-canvas text-ink hover:border-border-strong hover:bg-surface-soft'
                    }
                  `}
                >
                  <div className="flex items-center gap-2.5">
                    <Table className={`w-4 h-4 ${isSelected ? 'text-primary' : 'text-muted'}`} />
                    <span>{sheet}</span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSheetConfirm}
              className="btn-primary flex-1 gap-2"
            >
              <span>Confirm & Parse Sheet</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={resetUpload}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* STATE 4: SUCCESS SUMMARY */}
      {state === 'success' && metadata && (
        <div className="rounded-2xl border border-hairline bg-surface-card p-6 md:p-8 shadow-xs max-w-2xl mx-auto">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-hairline">
            <div className="w-12 h-12 rounded-xl bg-success-bg text-success flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-title-md text-ink font-bold">Dataset Ingested Successfully</h3>
              <p className="text-body-sm text-muted">
                {metadata.filename} {metadata.selected_sheet && `(Sheet: ${metadata.selected_sheet})`}
              </p>
            </div>
          </div>

          {/* Stats Summary Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-xl bg-canvas border border-hairline">
              <div className="text-caption text-muted mb-1 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-primary" />
                Total Rows
              </div>
              <div className="text-title-lg font-bold text-ink">
                {metadata.row_count?.toLocaleString() ?? 'N/A'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-canvas border border-hairline">
              <div className="text-caption text-muted mb-1 flex items-center gap-1.5">
                <Table className="w-3.5 h-3.5 text-primary" />
                Columns
              </div>
              <div className="text-title-lg font-bold text-ink">
                {metadata.column_count ?? metadata.columns?.length ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-canvas border border-hairline col-span-2 md:col-span-1">
              <div className="text-caption text-muted mb-1 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-primary" />
                File Size
              </div>
              <div className="text-title-lg font-bold text-ink">
                {formatBytes(metadata.file_size)}
              </div>
            </div>
          </div>

          {/* Column Inferred Dtypes Preview */}
          {metadata.columns && metadata.columns.length > 0 && (
            <div className="mb-6">
              <h4 className="text-caption-uppercase text-muted mb-3 font-semibold">
                Detected Columns & Data Types ({metadata.columns.length})
              </h4>
              <div className="max-h-48 overflow-y-auto border border-hairline rounded-xl divide-y divide-hairline bg-canvas">
                {metadata.columns.map((col) => (
                  <div
                    key={col.name}
                    className="flex items-center justify-between px-4 py-2.5 text-sm hover:bg-surface-soft transition-colors"
                  >
                    <span className="font-mono text-ink font-medium truncate max-w-[60%]">
                      {col.name}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-surface-card border border-hairline text-primary">
                      {col.dtype}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            <button
              onClick={() => {
                if (onContinueToOverview) {
                  onContinueToOverview(metadata);
                }
              }}
              className="btn-primary w-full sm:w-auto gap-2 text-center justify-center flex-1"
            >
              <span>Continue to Data Overview</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={resetUpload}
              className="btn-secondary w-full sm:w-auto gap-2 justify-center"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Upload Another Dataset</span>
            </button>
          </div>
        </div>
      )}

      {/* STATE 5: ERROR DISPLAY */}
      {state === 'error' && errorDetails && (
        <div className="rounded-2xl border border-error/30 bg-error-bg/30 p-6 md:p-8 shadow-xs max-w-xl mx-auto">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-10 h-10 rounded-xl bg-error/15 text-error flex items-center justify-center shrink-0 mt-0.5">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-title-md text-error font-bold">
                Upload Failed
              </h3>
              <p className="text-body-sm text-ink font-medium mt-1">
                {errorDetails.message}
              </p>
            </div>
          </div>

          {/* Clear why and how to fix guidance */}
          <div className="p-4 rounded-xl bg-surface-card border border-hairline mb-6">
            <div className="text-caption-uppercase text-muted font-bold mb-1">
              How to resolve
            </div>
            <p className="text-body-sm text-body leading-relaxed">
              {errorDetails.guidance}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={resetUpload}
              className="btn-primary gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Try Uploading Again</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
