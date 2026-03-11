import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import type { ApiResponse, ApiError, RequestConfig } from '../types/ApiTypes';
import { DEV_FLAGS } from '../config/constants';

class ApiService {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = DEV_FLAGS.MOCK_API
      ? 'http://localhost:5173'
      : window.location.origin;

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (DEV_FLAGS.ENABLE_LOGGING) {
          console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        }
        return config;
      },
      (error) => {
        if (DEV_FLAGS.ENABLE_LOGGING) {
          console.error('❌ Request Error:', error);
        }
        return Promise.reject(this.handleError(error));
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        if (DEV_FLAGS.ENABLE_LOGGING) {
          console.log(`✅ API Response: ${response.status} ${response.config.url}`);
        }
        return response;
      },
      (error) => {
        if (DEV_FLAGS.ENABLE_LOGGING) {
          console.error('❌ Response Error:', error);
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: any): ApiError {
    const apiError: ApiError = {
      message: 'An unexpected error occurred',
      status: 500,
    };

    if (error.response) {
      // Server responded with error status
      apiError.status = error.response.status;
      apiError.message = error.response.data?.error || error.response.data?.message || error.message;
      apiError.details = error.response.data;
    } else if (error.request) {
      // Request was made but no response received
      apiError.status = 0;
      apiError.message = 'Network error. Please check your connection.';
    } else {
      // Something else happened
      apiError.message = error.message;
    }

    return apiError;
  }

  async request<T = any>(config: RequestConfig): Promise<T> {
    try {
      const axiosConfig: AxiosRequestConfig = {
        method: config.method,
        url: config.url,
        data: config.data,
        params: config.params,
        headers: config.headers,
        timeout: config.timeout,
      };

      const response: AxiosResponse<ApiResponse<T>> = await this.client.request(axiosConfig);

      if (response.data.success === false) {
        throw new Error(response.data.error || 'API request failed');
      }

      return (response.data.data || response.data) as T;
    } catch (error) {
      throw error;
    }
  }

  async get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>({
      method: 'GET',
      url,
      params,
    });
  }

  async post<T = any>(url: string, data?: any, headers?: Record<string, string>): Promise<T> {
    return this.request<T>({
      method: 'POST',
      url,
      data,
      headers,
    });
  }

  async put<T = any>(url: string, data?: any): Promise<T> {
    return this.request<T>({
      method: 'PUT',
      url,
      data,
    });
  }

  async delete<T = any>(url: string): Promise<T> {
    return this.request<T>({
      method: 'DELETE',
      url,
    });
  }

  // File upload with progress support
  async uploadFile<T = any>(
    url: string,
    file: File,
    options?: {
      onProgress?: (progress: number) => void;
      additionalData?: Record<string, any>;
    }
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    // Append additional data if provided
    if (options?.additionalData) {
      Object.entries(options.additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    try {
      const response = await this.client.post<ApiResponse<T>>(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (options?.onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            options.onProgress(progress);
          }
        },
      });

      if (response.data.success === false) {
        throw new Error(response.data.error || 'File upload failed');
      }

      return (response.data.data || response.data) as T;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Download file
  async downloadFile(url: string, filename: string): Promise<void> {
    try {
      const response = await this.client.get(url, {
        responseType: 'blob',
      });

      // Create blob link to download
      const blob = new Blob([response.data]);
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      link.click();

      // Clean up
      window.URL.revokeObjectURL(link.href);
    } catch (error) {
      throw this.handleError(error);
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default ApiService;