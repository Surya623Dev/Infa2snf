import React, { useState, useEffect } from 'react';
import {
  Download,
  File,
  FileText,
  Database,
  Code,
  TestTube,
  Archive,
  Eye,
  Copy,
  X,
} from 'lucide-react';
import type { GeneratedFile, ProcessingResults } from '../types/TranslationTypes';
import { apiService } from '../services/ApiService';
import { API_ENDPOINTS } from '../config/constants';
import toast from 'react-hot-toast';

export interface ResultsViewerProps {
  sessionId: string;
  results?: ProcessingResults;
  onDownload?: (fileId: string) => void;
  onDownloadAll?: () => void;
  className?: string;
}

const FILE_TYPE_ICONS: Record<string, React.ElementType> = {
  readme: FileText,
  param: Database,
  snowsql: Code,
  test: TestTube,
  yaml: File,
  csv: Database,
  sql: Code,
};

const FILE_TYPE_COLORS: Record<string, string> = {
  readme: 'bg-blue-100 text-blue-600',
  param: 'bg-green-100 text-green-600',
  snowsql: 'bg-purple-100 text-purple-600',
  test: 'bg-yellow-100 text-yellow-600',
  yaml: 'bg-indigo-100 text-indigo-600',
  csv: 'bg-orange-100 text-orange-600',
  sql: 'bg-red-100 text-red-600',
};

export const ResultsViewer: React.FC<ResultsViewerProps> = ({
  sessionId,
  results,
  onDownload,
  onDownloadAll,
  className = '',
}) => {
  const [selectedFile, setSelectedFile] = useState<GeneratedFile | null>(null);
  const [previewContent, setPreviewContent] = useState<string>('');
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [downloadingFiles, setDownloadingFiles] = useState<Set<string>>(new Set());
  const [displayResults, setDisplayResults] = useState<ProcessingResults | null>(null);
  const [isLoadingResults, setIsLoadingResults] = useState(false);

  // Fetch results from API if not provided
  useEffect(() => {
    if (results) {
      setDisplayResults(results);
    } else {
      fetchResults();
    }
  }, [sessionId, results]);

  const fetchResults = async () => {
    setIsLoadingResults(true);
    try {
      const apiResults = await apiService.get<ProcessingResults>(`${API_ENDPOINTS.SESSION}/${sessionId}/results`);
      setDisplayResults(apiResults);
    } catch (error) {
      console.error('Failed to fetch results:', error);
      toast.error('Failed to load results. Please try refreshing.');
      // Use fallback mock results if API fails
      setDisplayResults({
        sessionId,
        status: 'success',
        phasesCompleted: ['Phase A', 'Phase B', 'Phase C', 'Phase D', 'Phase E', 'Phase F'],
        generatedFiles: [],
        summary: {
          workflowsProcessed: 0,
          sessionsProcessed: 0,
          sqlFilesGenerated: 0,
          testFilesGenerated: 0,
          errorsFound: 1,
          warningsFound: 0,
          processingTimeMs: 0,
        },
      });
    } finally {
      setIsLoadingResults(false);
    }
  };

  if (isLoadingResults || !displayResults) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="text-secondary-600 mt-4">Loading results...</p>
        </div>
      </div>
    );
  }

  // Handle file preview
  const handlePreview = async (file: GeneratedFile) => {
    setSelectedFile(file);

    if (file.preview) {
      setPreviewContent(file.preview);
      return;
    }

    if (!['readme', 'snowsql', 'yaml', 'sql', 'csv'].includes(file.type)) {
      setPreviewContent('Preview not available for this file type.');
      return;
    }

    setIsLoadingPreview(true);
    try {
      // Fetch file content from API for preview
      const content = await apiService.get<string>(`${API_ENDPOINTS.DOWNLOAD}/${sessionId}/files/${file.id}/preview`);
      setPreviewContent(content);
    } catch (error) {
      setPreviewContent('Error loading file preview.');
      console.error('Preview error:', error);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  // Handle single file download
  const handleFileDownload = async (file: GeneratedFile) => {
    if (downloadingFiles.has(file.id)) return;

    setDownloadingFiles(prev => new Set(prev).add(file.id));

    try {
      // Download file from API
      await apiService.downloadFile(`${API_ENDPOINTS.DOWNLOAD}/${sessionId}/files/${file.id}`, file.name);

      toast.success(`Downloaded ${file.name}`);
      onDownload?.(file.id);

    } catch (error) {
      toast.error(`Failed to download ${file.name}`);
      console.error('Download error:', error);
    } finally {
      setDownloadingFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(file.id);
        return newSet;
      });
    }
  };

  // Handle download all
  const handleDownloadAll = async () => {
    try {
      toast.success('Preparing download package...');

      // Download ZIP file containing all generated files
      await apiService.downloadFile(`${API_ENDPOINTS.DOWNLOAD}/${sessionId}/all`, `${sessionId}-files.zip`);

      toast.success('All files downloaded successfully!');
      onDownloadAll?.();
    } catch (error) {
      toast.error('Failed to create download package');
      console.error('Download all error:', error);
    }
  };

  // Copy preview content to clipboard
  const handleCopyContent = () => {
    if (previewContent) {
      navigator.clipboard.writeText(previewContent);
      toast.success('Content copied to clipboard');
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Group files by type
  const filesByType = displayResults.generatedFiles.reduce((acc, file) => {
    if (!acc[file.type]) {
      acc[file.type] = [];
    }
    acc[file.type].push(file);
    return acc;
  }, {} as Record<string, GeneratedFile[]>);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-secondary-900">
              Generated Files
            </h2>
            <button
              onClick={handleDownloadAll}
              className="btn btn-primary flex items-center space-x-2"
            >
              <Archive size={20} />
              <span>Download All</span>
            </button>
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center p-4 bg-primary-50 rounded-lg">
            <div className="text-2xl font-bold text-primary-600">
              {displayResults.summary.sqlFilesGenerated}
            </div>
            <div className="text-sm text-primary-700">SQL Files</div>
          </div>
          <div className="text-center p-4 bg-success-50 rounded-lg">
            <div className="text-2xl font-bold text-success-600">
              {displayResults.summary.testFilesGenerated}
            </div>
            <div className="text-sm text-success-700">Test Files</div>
          </div>
          <div className="text-center p-4 bg-secondary-50 rounded-lg">
            <div className="text-2xl font-bold text-secondary-600">
              {displayResults.generatedFiles.length}
            </div>
            <div className="text-sm text-secondary-700">Total Files</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">
              {Math.round(displayResults.summary.processingTimeMs / 1000)}s
            </div>
            <div className="text-sm text-orange-700">Processing Time</div>
          </div>
        </div>

        {/* Files by type */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(filesByType).map(([type, files]) => {
            const Icon = FILE_TYPE_ICONS[type] || File;
            const colorClass = FILE_TYPE_COLORS[type] || 'bg-secondary-100 text-secondary-600';

            return (
              <div key={type} className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded ${colorClass}`}>
                    <Icon size={16} />
                  </div>
                  <h3 className="font-medium text-secondary-900 capitalize">
                    {type} Files ({files.length})
                  </h3>
                </div>

                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between p-3 border border-secondary-200 rounded-lg hover:bg-secondary-50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-secondary-900 truncate">
                          {file.name}
                        </p>
                        <p className="text-xs text-secondary-500">
                          {formatFileSize(file.size)} • {file.phase}
                        </p>
                      </div>

                      <div className="flex items-center space-x-2 ml-3">
                        {(file.preview || ['readme', 'snowsql', 'yaml', 'sql'].includes(file.type)) && (
                          <button
                            onClick={() => handlePreview(file)}
                            className="p-1 text-secondary-400 hover:text-secondary-600 transition-colors"
                            title="Preview"
                          >
                            <Eye size={16} />
                          </button>
                        )}

                        <button
                          onClick={() => handleFileDownload(file)}
                          disabled={downloadingFiles.has(file.id)}
                          className="p-1 text-primary-400 hover:text-primary-600 transition-colors disabled:opacity-50"
                          title="Download"
                        >
                          <Download size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* File Preview Modal */}
      {selectedFile && (
        <div className="modal-overlay" onClick={() => setSelectedFile(null)}>
          <div
            className="modal-content max-w-4xl w-full max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded ${FILE_TYPE_COLORS[selectedFile.type] || 'bg-secondary-100 text-secondary-600'}`}>
                    {React.createElement(FILE_TYPE_ICONS[selectedFile.type] || File, { size: 20 })}
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary-900">{selectedFile.name}</h3>
                    <p className="text-sm text-secondary-600">
                      {formatFileSize(selectedFile.size)} • {selectedFile.phase}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleCopyContent}
                    className="btn btn-secondary btn-sm flex items-center space-x-1"
                    disabled={!previewContent}
                  >
                    <Copy size={16} />
                    <span>Copy</span>
                  </button>
                  <button
                    onClick={() => handleFileDownload(selectedFile)}
                    className="btn btn-primary btn-sm flex items-center space-x-1"
                  >
                    <Download size={16} />
                    <span>Download</span>
                  </button>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="p-1 text-secondary-400 hover:text-secondary-600"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-body">
              {isLoadingPreview ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="code-block max-h-96 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">
                      {previewContent || 'No preview available.'}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};