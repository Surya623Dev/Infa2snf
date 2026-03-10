// Core session and workflow types
export interface Session {
  id: string;
  createdAt: Date;
  status: SessionStatus;
  uploadedFiles: UploadedFile[];
  progress: ProcessingProgress;
  results?: ProcessingResults;
  error?: string;
}

export type SessionStatus =
  | 'initializing'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  path: string;
  uploadedAt: Date;
}

// Progress tracking types
export interface ProcessingProgress {
  sessionId: string;
  overallProgress: number;
  currentPhase: PhaseType;
  phases: Record<PhaseType, PhaseProgress>;
  errors: ProcessingError[];
  warnings: ProcessingWarning[];
  estimatedCompletion?: string;
  startedAt?: Date;
  completedAt?: Date;
}

export type PhaseType =
  | 'Phase A'
  | 'Phase B'
  | 'Phase C'
  | 'Phase D'
  | 'Phase E'
  | 'Phase F';

export interface PhaseProgress {
  status: PhaseStatus;
  progress: number;
  startedAt?: Date;
  completedAt?: Date;
  description?: string;
  currentStep?: string;
}

export type PhaseStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface ProcessingError {
  phase: PhaseType;
  message: string;
  details?: string;
  timestamp: Date;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface ProcessingWarning {
  phase: PhaseType;
  message: string;
  details?: string;
  timestamp: Date;
}

// Processing results types
export interface ProcessingResults {
  sessionId: string;
  status: 'success' | 'partial' | 'failed';
  phasesCompleted: PhaseType[];
  generatedFiles: GeneratedFile[];
  summary: ProcessingSummary;
}

export interface GeneratedFile {
  id: string;
  name: string;
  type: GeneratedFileType;
  phase: PhaseType;
  size: number;
  path: string;
  downloadUrl?: string;
  preview?: string;
  createdAt: Date;
}

export type GeneratedFileType =
  | 'readme'
  | 'param'
  | 'snowsql'
  | 'test'
  | 'yaml'
  | 'csv'
  | 'sql';

export interface ProcessingSummary {
  workflowsProcessed: number;
  sessionsProcessed: number;
  sqlFilesGenerated: number;
  testFilesGenerated: number;
  errorsFound: number;
  warningsFound: number;
  processingTimeMs: number;
}

// Informatica XML structure types
export interface InformaticaWorkflow {
  name: string;
  folder: string;
  schedulerType: string;
  parameterFilename?: string;
  sessions: InformaticaSession[];
  linkConditions: LinkCondition[];
}

export interface InformaticaSession {
  name: string;
  mappingName: string;
  treatSourceRowsAs: 'Insert' | 'Update' | 'Delete' | 'Data driven';
  sources: InformaticaSource[];
  targets: InformaticaTarget[];
  mapping: InformaticaMapping;
  extensions: SessionExtensions;
}

export interface InformaticaSource {
  name: string;
  type: 'Flat File' | 'Relational';
  fields: SourceField[];
  filename?: string;
  connection?: string;
}

export interface SourceField {
  name: string;
  datatype: string;
  precision?: number;
  scale?: number;
  length?: number;
  nullable: boolean;
}

export interface InformaticaTarget {
  name: string;
  type: 'Flat File' | 'Relational';
  fields: TargetField[];
  connection?: string;
  loadType?: 'Bulk' | 'Normal';
}

export interface TargetField {
  name: string;
  datatype: string;
  precision?: number;
  scale?: number;
  length?: number;
  nullable: boolean;
  keyType?: 'PRIMARY KEY' | 'FOREIGN KEY';
}

export interface InformaticaMapping {
  name: string;
  transformations: Transformation[];
  connectors: Connector[];
}

export interface Transformation {
  name: string;
  type: TransformationType;
  ports: TransformationPort[];
  attributes: Record<string, any>;
  expressions?: Expression[];
}

export type TransformationType =
  | 'Source Qualifier'
  | 'Expression'
  | 'Lookup Procedure'
  | 'Filter'
  | 'Update Strategy'
  | 'Aggregator'
  | 'Joiner'
  | 'Sorter'
  | 'Sequence Generator'
  | 'Router';

export interface TransformationPort {
  name: string;
  type: 'INPUT' | 'OUTPUT' | 'INPUT/OUTPUT' | 'LOOKUP/OUTPUT';
  datatype: string;
  precision?: number;
  scale?: number;
}

export interface Expression {
  portName: string;
  expression: string;
  description?: string;
}

export interface Connector {
  fromInstance: string;
  fromField: string;
  toInstance: string;
  toField: string;
}

export interface LinkCondition {
  fromTask: string;
  toTask: string;
  condition: 'SUCCESS' | 'FAILURE' | 'UNCONDITIONAL';
}

export interface SessionExtensions {
  fileReader?: FileReaderExtension;
  relationalWriter?: RelationalWriterExtension;
  relationalLookup?: RelationalLookupExtension;
  postSessionCommand?: string;
}

export interface FileReaderExtension {
  inputType: string;
  sourceFilename: string;
}

export interface RelationalWriterExtension {
  targetLoadType: 'Bulk' | 'Normal';
  insertFlag: boolean;
  updateFlag: boolean;
  deleteFlag: boolean;
}

export interface RelationalLookupExtension {
  connectionVariable: string;
}

// Snowflake generation types
export interface SnowflakeSQL {
  sessionName: string;
  sourceTable: string;
  targetTable: string;
  stagingStatements: string[];
  cteStatements: string[];
  finalStatement: string;
  fileOperations: FileOperation[];
}

export interface FileOperation {
  type: 'PUT' | 'COPY_INTO' | 'REMOVE' | 'GET';
  statement: string;
  description: string;
}


// API types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface UploadResponse extends ApiResponse {
  data: {
    sessionId: string;
    uploadedFiles: UploadedFile[];
  };
}

export interface ProcessResponse extends ApiResponse {
  data: {
    sessionId: string;
    status: string;
    estimatedCompletionTime: string;
  };
}

export interface ProgressResponse extends ApiResponse {
  data: ProcessingProgress;
}

export interface DownloadResponse extends ApiResponse {
  data: {
    downloadUrl: string;
    filename: string;
    fileType: string;
  };
}

// UI component types
export interface UploadZoneProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxFileSize?: number;
  acceptedFileTypes?: string[];
  disabled?: boolean;
}

export interface ProgressDashboardProps {
  sessionId: string;
  progress: ProcessingProgress;
  onComplete?: () => void;
}

export interface ResultsViewerProps {
  sessionId: string;
  results: ProcessingResults;
  onDownload: (fileId: string) => void;
  onDownloadAll: () => void;
}

// Form types
export interface ConfigurationForm {
  etlParamsRepoPath: string;
  outputFormat: 'individual' | 'zip';
  includeTests: boolean;
  includeDocumentation: boolean;
  customTemplates: boolean;
}

// Utility types
export type Without<T, U> = { [P in Exclude<keyof T, keyof U>]?: never };
export type XOR<T, U> = T | U extends object ? (Without<T, U> & U) | (Without<U, T> & T) : T | U;

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}