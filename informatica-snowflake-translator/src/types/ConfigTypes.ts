// Configuration types
export interface AppConfig {
  etlParamsRepoPath: string;
  maxFileSize: number;
  sessionTimeout: number;
  supportedFileTypes: string[];
  netlifyConfig: NetlifyConfig;
}

export interface NetlifyConfig {
  siteId: string;
  functionTimeout: number;
  blobStorageEnabled: boolean;
}