import React, { useCallback, useState, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import type { UploadedFile } from '../types/TranslationTypes';
import { fileUploadService } from '../services/FileUploadService';
import { FILE_CONSTRAINTS } from '../config/constants';

export interface UploadZoneProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  onError?: (error: string) => void;
  maxFiles?: number;
  maxFileSize?: number;
  acceptedFileTypes?: string[];
  disabled?: boolean;
  className?: string;
}

interface FileWithPreview extends File {
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesUploaded,
  onError,
  maxFiles = FILE_CONSTRAINTS.MAX_FILES_PER_SESSION,
  maxFileSize = FILE_CONSTRAINTS.MAX_FILE_SIZE,
  acceptedFileTypes = FILE_CONSTRAINTS.SUPPORTED_EXTENSIONS,
  disabled = false,
  className = '',
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle file drop or selection
  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setValidationErrors([]);

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const errors = rejectedFiles.map((file) => {
          if (file.errors) {
            return `${file.file.name}: ${file.errors[0]?.message || 'Invalid file'}`;
          }
          return `${file.file.name}: Invalid file`;
        });
        setValidationErrors(errors);
        onError?.(errors.join('; '));
        return;
      }

      // Debug log accepted files
      console.log('UploadZone - About to validate files:', acceptedFiles.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type,
        lastModified: f.lastModified,
        constructor: f.constructor.name
      })));

      // Validate files
      const validation = fileUploadService.validateFiles(acceptedFiles);
      console.log('UploadZone - Validation result:', validation);

      if (!validation.isValid) {
        setValidationErrors(validation.errors);
        onError?.(validation.errors.join('; '));
        return;
      }

      // Add validation warnings if any
      if (validation.warnings.length > 0) {
        console.warn('File upload warnings:', validation.warnings);
      }

      // Create FileWithPreview objects
      const newFiles: FileWithPreview[] = acceptedFiles.map((file) => ({
        ...file,
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        status: 'pending',
        progress: 0,
      }));

      setFiles(newFiles);
    },
    [onError, maxFiles, maxFileSize]
  );

  // Configure dropzone - disable built-in file type validation, rely on our custom validation
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    // Remove strict MIME type checking, accept all files and validate manually
    accept: undefined,
    maxFiles,
    maxSize: maxFileSize,
    disabled: disabled || isUploading,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    onDropAccepted: () => setDragActive(false),
    onDropRejected: () => setDragActive(false),
  });

  // Handle file upload
  const handleUpload = async () => {
    if (files.length === 0 || isUploading) return;

    setIsUploading(true);
    setValidationErrors([]);

    try {
      // Update files to uploading state
      setFiles((prevFiles) =>
        prevFiles.map((file) => ({ ...file, status: 'uploading' as const }))
      );

      // Convert FileWithPreview back to File for upload
      const filesToUpload = files.map((file) => {
        // Return the file as-is since it's already a File object with additional properties
        return file as File;
      });

      // Upload files with progress tracking
      const result = await fileUploadService.uploadFiles(filesToUpload, {
        onProgress: (progress) => {
          setFiles((prevFiles) =>
            prevFiles.map((file) => ({ ...file, progress }))
          );
        },
      });

      if (result.success && result.uploadedFiles) {
        // Update files to success state
        setFiles((prevFiles) =>
          prevFiles.map((file) => ({
            ...file,
            status: 'success' as const,
            progress: 100,
          }))
        );

        // Notify parent component
        onFilesUploaded(result.uploadedFiles);
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';

      // Update files to error state
      setFiles((prevFiles) =>
        prevFiles.map((file) => ({
          ...file,
          status: 'error' as const,
          error: errorMessage,
        }))
      );

      setValidationErrors([errorMessage]);
      onError?.(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  // Remove file from list
  const removeFile = (fileId: string) => {
    setFiles((prevFiles) => prevFiles.filter((file) => file.id !== fileId));
    setValidationErrors([]);
  };

  // Clear all files
  const clearFiles = () => {
    setFiles([]);
    setValidationErrors([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`
          upload-zone
          ${isDragActive || dragActive ? 'upload-zone-active' : ''}
          ${validationErrors.length > 0 ? 'upload-zone-error' : ''}
          ${disabled || isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <input {...getInputProps()} ref={fileInputRef} />

        <div className="flex flex-col items-center space-y-4">
          <div className={`
            p-4 rounded-full transition-colors duration-200
            ${isDragActive || dragActive ? 'bg-primary-100 text-primary-600' : 'bg-secondary-100 text-secondary-600'}
          `}>
            <Upload size={32} />
          </div>

          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold text-secondary-900">
              {isDragActive || dragActive
                ? 'Drop files here'
                : 'Upload Informatica Files'
              }
            </h3>
            <p className="text-secondary-600">
              Drag & drop XML and PARAM files, or{' '}
              <span className="text-primary-600 font-medium">browse</span> to select
            </p>
            <div className="text-sm text-secondary-500 space-y-1">
              <p>Supported: {acceptedFileTypes.join(', ')}</p>
              <p>Max file size: {formatFileSize(maxFileSize)}</p>
              <p>Max files: {maxFiles}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="text-danger-600 mt-0.5" size={20} />
            <div className="flex-1">
              <h4 className="text-danger-800 font-medium mb-2">Upload Errors</h4>
              <ul className="text-danger-700 text-sm space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-danger-500">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-secondary-900">
              Selected Files ({files.length})
            </h4>
            {!isUploading && (
              <button
                onClick={clearFiles}
                className="text-secondary-500 hover:text-secondary-700 text-sm font-medium"
              >
                Clear All
              </button>
            )}
          </div>

          <div className="space-y-3">
            {files.map((file) => (
              <div
                key={file.id}
                className={`
                  file-item
                  ${file.status === 'uploading' ? 'file-item-uploading' : ''}
                  ${file.status === 'success' ? 'file-item-success' : ''}
                  ${file.status === 'error' ? 'file-item-error' : ''}
                `}
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    {file.status === 'success' ? (
                      <CheckCircle className="text-success-600" size={20} />
                    ) : file.status === 'error' ? (
                      <AlertCircle className="text-danger-600" size={20} />
                    ) : file.status === 'uploading' ? (
                      <Loader2 className="text-primary-600 animate-spin" size={20} />
                    ) : (
                      <File className="text-secondary-600" size={20} />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-secondary-900 truncate">
                        {file.name}
                      </p>
                      <span className="text-xs text-secondary-500 ml-2">
                        {formatFileSize(file.size)}
                      </span>
                    </div>

                    {file.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-secondary-600 mb-1">
                          <span>Uploading...</span>
                          <span>{file.progress}%</span>
                        </div>
                        <div className="progress-bar h-1">
                          <div
                            className="progress-fill h-full"
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {file.status === 'error' && file.error && (
                      <p className="text-xs text-danger-600 mt-1">{file.error}</p>
                    )}

                    {file.status === 'success' && (
                      <p className="text-xs text-success-600 mt-1">Upload complete</p>
                    )}
                  </div>
                </div>

                {!isUploading && file.status !== 'success' && (
                  <button
                    onClick={() => removeFile(file.id)}
                    className="flex-shrink-0 text-secondary-400 hover:text-secondary-600 p-1"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Upload Button */}
          {files.some(file => file.status === 'pending' || file.status === 'error') && (
            <div className="flex justify-center pt-4">
              <button
                onClick={handleUpload}
                disabled={isUploading || disabled}
                className={`
                  btn
                  ${isUploading || disabled ? 'btn-disabled' : 'btn-primary'}
                  flex items-center space-x-2 px-6 py-3
                `}
              >
                {isUploading ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <Upload size={20} />
                    <span>Start Upload</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};