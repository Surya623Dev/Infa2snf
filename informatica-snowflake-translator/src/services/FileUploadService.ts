import { apiService } from './ApiService';
import { sessionService } from './SessionService';
import { UploadedFile, ValidationResult } from '../types/TranslationTypes';
import { FileUploadOptions, XMLValidationResult } from '../types/ApiTypes';
import {
  API_ENDPOINTS,
  FILE_CONSTRAINTS,
  ERROR_MESSAGES,
  DEV_FLAGS
} from '../config/constants';

export interface FileUploadResult {
  success: boolean;
  sessionId?: string;
  uploadedFiles?: UploadedFile[];
  error?: string;
}

class FileUploadService {
  // Validate files before upload
  validateFiles(files: File[]): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check file count
    if (files.length === 0) {
      errors.push('No files selected');
      return { isValid: false, errors, warnings };
    }

    if (files.length > FILE_CONSTRAINTS.MAX_FILES_PER_SESSION) {
      errors.push(`Too many files. Maximum ${FILE_CONSTRAINTS.MAX_FILES_PER_SESSION} files allowed.`);
    }

    // Validate each file
    files.forEach((file, index) => {
      const fileErrors = this.validateSingleFile(file, index);
      errors.push(...fileErrors.errors);
      warnings.push(...fileErrors.warnings);
    });

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  // Validate a single file
  private validateSingleFile(file: File, index: number): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    const prefix = `File ${index + 1} (${file.name}):`;

    // Size validation
    if (file.size > FILE_CONSTRAINTS.MAX_FILE_SIZE) {
      errors.push(`${prefix} ${ERROR_MESSAGES.FILE_TOO_LARGE}`);
    }

    if (file.size === 0) {
      errors.push(`${prefix} File is empty`);
    }

    // Extension validation
    const extension = this.getFileExtension(file.name).toLowerCase();
    if (!FILE_CONSTRAINTS.SUPPORTED_EXTENSIONS.includes(extension)) {
      errors.push(`${prefix} ${ERROR_MESSAGES.INVALID_FILE_TYPE}`);
    }

    // MIME type validation
    if (file.type && !FILE_CONSTRAINTS.SUPPORTED_MIME_TYPES.includes(file.type)) {
      warnings.push(`${prefix} Unexpected MIME type: ${file.type}`);
    }

    // XML file specific validation
    if (extension === '.xml') {
      // We'll validate XML structure after reading the content
      if (file.size < 100) {
        warnings.push(`${prefix} XML file seems very small`);
      }
    }

    return { isValid: errors.length === 0, errors, warnings };
  }

  // Validate XML content
  async validateXMLContent(file: File): Promise<XMLValidationResult> {
    return new Promise((resolve) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const result = this.parseAndValidateXML(content);
          resolve(result);
        } catch (error) {
          resolve({
            isValid: false,
            hasWorkflow: false,
            hasSessions: false,
            hasMapping: false,
            missingElements: [],
            errors: [`Failed to read file: ${error}`],
            warnings: [],
          });
        }
      };

      reader.onerror = () => {
        resolve({
          isValid: false,
          hasWorkflow: false,
          hasSessions: false,
          hasMapping: false,
          missingElements: [],
          errors: ['Failed to read file'],
          warnings: [],
        });
      };

      reader.readAsText(file);
    });
  }

  // Parse and validate XML content
  private parseAndValidateXML(content: string): XMLValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    const missingElements: string[] = [];

    try {
      // Basic XML parsing
      const parser = new DOMParser();
      const doc = parser.parseFromString(content, 'text/xml');

      // Check for parsing errors
      const parseError = doc.querySelector('parsererror');
      if (parseError) {
        errors.push('Invalid XML format: ' + parseError.textContent);
        return {
          isValid: false,
          hasWorkflow: false,
          hasSessions: false,
          hasMapping: false,
          missingElements: [],
          errors,
          warnings,
        };
      }

      // Check for required Informatica elements
      const hasWorkflow = doc.querySelector('WORKFLOW') !== null;
      const hasSessions = doc.querySelectorAll('SESSION').length > 0;
      const hasMapping = doc.querySelectorAll('MAPPING').length > 0;

      if (!hasWorkflow) {
        missingElements.push('WORKFLOW');
      }

      if (!hasSessions) {
        missingElements.push('SESSION');
      }

      if (!hasMapping) {
        missingElements.push('MAPPING');
      }

      // Additional validations
      if (hasWorkflow) {
        const workflow = doc.querySelector('WORKFLOW');
        if (!workflow?.getAttribute('NAME')) {
          warnings.push('WORKFLOW element missing NAME attribute');
        }
      }

      if (hasSessions) {
        const sessions = doc.querySelectorAll('SESSION');
        sessions.forEach((session, index) => {
          if (!session.getAttribute('NAME')) {
            warnings.push(`SESSION ${index + 1} missing NAME attribute`);
          }
          if (!session.getAttribute('MAPPINGNAME')) {
            warnings.push(`SESSION ${index + 1} missing MAPPINGNAME attribute`);
          }
        });
      }

      const isValid = errors.length === 0 && hasWorkflow && hasSessions && hasMapping;

      return {
        isValid,
        hasWorkflow,
        hasSessions,
        hasMapping,
        missingElements,
        errors,
        warnings,
      };

    } catch (error) {
      errors.push(`XML parsing error: ${error}`);
      return {
        isValid: false,
        hasWorkflow: false,
        hasSessions: false,
        hasMapping: false,
        missingElements: [],
        errors,
        warnings,
      };
    }
  }

  // Upload files
  async uploadFiles(
    files: File[],
    options?: FileUploadOptions
  ): Promise<FileUploadResult> {
    try {
      // Validate files first
      const validation = this.validateFiles(files);
      if (!validation.isValid) {
        return {
          success: false,
          error: validation.errors.join('; '),
        };
      }

      // For XML files, validate content
      for (const file of files) {
        const extension = this.getFileExtension(file.name).toLowerCase();
        if (extension === '.xml') {
          const xmlValidation = await this.validateXMLContent(file);
          if (!xmlValidation.isValid) {
            return {
              success: false,
              error: `XML validation failed: ${xmlValidation.errors.join('; ')}`,
            };
          }
        }
      }

      // Mock upload in development mode
      if (DEV_FLAGS.MOCK_API) {
        return this.mockUpload(files, options);
      }

      // Real upload
      return this.performUpload(files, options);

    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed',
      };
    }
  }

  // Mock upload for development
  private async mockUpload(
    files: File[],
    options?: FileUploadOptions
  ): Promise<FileUploadResult> {
    // Simulate upload progress
    if (options?.onProgress) {
      for (let i = 0; i <= 100; i += 20) {
        options.onProgress(i);
        await this.delay(100);
      }
    }

    const uploadedFiles: UploadedFile[] = files.map((file, index) => ({
      id: `file_${Date.now()}_${index}`,
      name: file.name,
      size: file.size,
      type: file.type,
      path: `/mock/path/${file.name}`,
      uploadedAt: new Date(),
    }));

    // Create session
    const session = sessionService.createSession(uploadedFiles);

    return {
      success: true,
      sessionId: session.id,
      uploadedFiles,
    };
  }

  // Perform actual upload
  private async performUpload(
    files: File[],
    options?: FileUploadOptions
  ): Promise<FileUploadResult> {
    const formData = new FormData();

    files.forEach((file, index) => {
      formData.append(`file_${index}`, file);
    });

    if (options?.sessionId) {
      formData.append('session_id', options.sessionId);
    }

    try {
      const response = await apiService.uploadFile(
        API_ENDPOINTS.UPLOAD,
        files[0], // API service expects single file, we'll need to modify for multiple
        {
          onProgress: options?.onProgress,
          additionalData: { files_count: files.length },
        }
      );

      // Create session with uploaded files
      const uploadedFiles: UploadedFile[] = files.map((file, index) => ({
        id: `${response.session_id}_file_${index}`,
        name: file.name,
        size: file.size,
        type: file.type,
        path: `/uploads/${response.session_id}/${file.name}`,
        uploadedAt: new Date(),
      }));

      const session = sessionService.createSession(uploadedFiles);

      return {
        success: true,
        sessionId: response.session_id,
        uploadedFiles,
      };

    } catch (error) {
      throw error;
    }
  }

  // Helper: Get file extension
  private getFileExtension(filename: string): string {
    const parts = filename.split('.');
    return parts.length > 1 ? `.${parts.pop()}` : '';
  }

  // Helper: Create delay
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Get upload progress for session
  getUploadProgress(sessionId: string): number {
    const session = sessionService.getSessionById(sessionId);
    if (!session || session.status !== 'uploading') {
      return 0;
    }
    // Return mock progress for now
    return 100;
  }

  // Cancel upload
  cancelUpload(sessionId: string): void {
    // In a real implementation, this would cancel the upload request
    console.log(`Cancelling upload for session: ${sessionId}`);
    sessionService.updateSessionStatus('error', 'Upload cancelled by user');
  }
}

// Export singleton instance
export const fileUploadService = new FileUploadService();
export default FileUploadService;