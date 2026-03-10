// HTTP client types
export interface RequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  data?: any;
  params?: Record<string, string>;
  timeout?: number;
}

export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: any;
}

// File upload types
export interface FileUploadOptions {
  sessionId?: string;
  chunkSize?: number;
  maxRetries?: number;
  onProgress?: (progress: number) => void;
  onError?: (error: ApiError) => void;
}

export interface UploadChunk {
  data: Blob;
  index: number;
  total: number;
  sessionId: string;
}

// Progress polling types
export interface PollingConfig {
  interval: number;
  maxAttempts?: number;
  backoffMultiplier?: number;
  onUpdate?: (progress: any) => void;
  onComplete?: (result: any) => void;
  onError?: (error: ApiError) => void;
}

// Validation types
export interface FileValidationRule {
  type: 'size' | 'extension' | 'mime-type' | 'structure';
  value: any;
  message: string;
}

export interface XMLValidationResult {
  isValid: boolean;
  hasWorkflow: boolean;
  hasSessions: boolean;
  hasMapping: boolean;
  missingElements: string[];
  errors: string[];
  warnings: string[];
}