import { AppConfig } from '../types/ConfigTypes';

// API endpoints
export const API_ENDPOINTS = {
  UPLOAD: '/api/upload',
  PROCESS: '/api/process',
  PROGRESS: '/api/progress',
  DOWNLOAD: '/api/download',
  SESSION: '/api/session',
} as const;

// File constraints
export const FILE_CONSTRAINTS = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  MAX_FILES_PER_SESSION: 10,
  SUPPORTED_EXTENSIONS: ['.xml', '.param'],
  SUPPORTED_MIME_TYPES: [
    'text/xml',
    'application/xml',
    'text/plain',
  ],
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks for upload
} as const;

// Processing constants
export const PROCESSING = {
  PHASES: [
    { key: 'Phase A', name: 'README Generation', description: 'Generate detailed README from XML' },
    { key: 'Phase B', name: 'Parameter Discovery', description: 'Find and copy .param file' },
    { key: 'Phase C', name: 'SQL Generation', description: 'Generate Snowflake SQL files' },
    { key: 'Phase D', name: 'Test Creation', description: 'Generate test files' },
    { key: 'Phase E', name: 'YAML Configuration', description: 'Generate snowflake.yml' },
    { key: 'Phase F', name: 'Test Data', description: 'Generate test_data folder' },
  ],
  POLLING_INTERVAL: 2000, // 2 seconds
  MAX_POLLING_ATTEMPTS: 150, // 5 minutes max
  SESSION_TIMEOUT: 3600000, // 1 hour
} as const;

// UI constants
export const UI = {
  COLORS: {
    PRIMARY: {
      50: '#eff6ff',
      100: '#dbeafe',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      900: '#1e3a8a',
    },
    SUCCESS: '#22c55e',
    WARNING: '#f59e0b',
    ERROR: '#ef4444',
    INFO: '#3b82f6',
  },
  BREAKPOINTS: {
    SM: '640px',
    MD: '768px',
    LG: '1024px',
    XL: '1280px',
    '2XL': '1536px',
  },
  ANIMATIONS: {
    DURATION: {
      FAST: 150,
      NORMAL: 300,
      SLOW: 500,
    },
    EASING: {
      EASE_IN: 'cubic-bezier(0.4, 0, 1, 1)',
      EASE_OUT: 'cubic-bezier(0, 0, 0.2, 1)',
      EASE_IN_OUT: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
} as const;

// Default configuration
export const DEFAULT_CONFIG: AppConfig = {
  etlParamsRepoPath: 'G:\\Projects\\BA\\etl-server-params 1\\etl-server-params\\',
  maxFileSize: FILE_CONSTRAINTS.MAX_FILE_SIZE,
  sessionTimeout: PROCESSING.SESSION_TIMEOUT,
  supportedFileTypes: FILE_CONSTRAINTS.SUPPORTED_EXTENSIONS,
  netlifyConfig: {
    siteId: process.env.NETLIFY_SITE_ID || '',
    functionTimeout: 26000, // 26 seconds
    blobStorageEnabled: true,
  },
};

// Informatica to Snowflake transformation mappings
export const TRANSFORMATION_MAPPINGS = {
  EXPRESSIONS: {
    'TO_DATE(': 'TO_TIMESTAMP(',
    'TO_INTEGER(': 'CAST(',
    'TO_DECIMAL(': 'CAST(',
    'LTRIM(RTRIM(': 'LTRIM(RTRIM(',
    'SYSTIMESTAMP()': 'CURRENT_TIMESTAMP()',
    'SESSSTARTTIME': 'CURRENT_TIMESTAMP()',
    'SYSDATE': 'CURRENT_DATE()',
    'IIF(': 'IFF(',
    'ISNULL(': ' IS NULL',
    'NVL(': 'NVL(',
    'DECODE(': 'DECODE(',
    'SUBSTR(': 'SUBSTR(',
    'LPAD(': 'LPAD(',
    'RPAD(': 'RPAD(',
    'CONCAT(': 'CONCAT(',
    'ROUND(': 'ROUND(',
    'TRUNC(': 'TRUNC(',
    'ABS(': 'ABS(',
    'UPPER(': 'UPPER(',
    'LOWER(': 'LOWER(',
    'LENGTH(': 'LENGTH(',
    'REPLACECHR(': 'REPLACE(',
    'REPLACESTR(': 'REPLACE(',
    'REG_REPLACE(': 'REGEXP_REPLACE(',
    'INSTR(': 'POSITION(',
    'ADD_TO_DATE(': 'DATEADD(',
    'DATE_DIFF(': 'DATEDIFF(',
    'GET_DATE_PART(': 'DATE_PART(',
  },
  DATA_TYPES: {
    'String': 'VARCHAR',
    'Integer': 'INTEGER',
    'Decimal': 'NUMBER',
    'Date/Time': 'TIMESTAMP',
    'Date': 'DATE',
    'Double': 'FLOAT',
    'BigInt': 'BIGINT',
    'Real': 'REAL',
    'Small Integer': 'SMALLINT',
  },
} as const;

// Error messages
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: `File size exceeds maximum allowed size of ${FILE_CONSTRAINTS.MAX_FILE_SIZE / 1024 / 1024}MB`,
  INVALID_FILE_TYPE: 'Invalid file type. Only XML and PARAM files are supported.',
  UPLOAD_FAILED: 'Failed to upload files. Please try again.',
  PROCESSING_FAILED: 'Processing failed. Please check the logs for details.',
  SESSION_NOT_FOUND: 'Session not found or expired.',
  NETWORK_ERROR: 'Network error. Please check your connection.',
  VALIDATION_FAILED: 'File validation failed. Please check the file format.',
  XML_PARSE_ERROR: 'Failed to parse XML file. Please ensure it\'s a valid Informatica XML file.',
  PARAM_FILE_NOT_FOUND: 'Parameter file not found in the specified location.',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  UPLOAD_SUCCESS: 'Files uploaded successfully',
  PROCESSING_STARTED: 'Processing started successfully',
  PROCESSING_COMPLETE: 'Translation completed successfully',
  DOWNLOAD_READY: 'Files are ready for download',
  SESSION_CREATED: 'Session created successfully',
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  SESSION_ID: 'informatica_translator_session_id',
  CONFIG: 'informatica_translator_config',
  RECENT_SESSIONS: 'informatica_translator_recent_sessions',
  USER_PREFERENCES: 'informatica_translator_preferences',
} as const;

// Development flags
export const DEV_FLAGS = {
  MOCK_API: process.env.NODE_ENV === 'development',
  ENABLE_LOGGING: process.env.NODE_ENV === 'development',
  SKIP_VALIDATION: false,
  DEBUG_MODE: process.env.NODE_ENV === 'development',
} as const;