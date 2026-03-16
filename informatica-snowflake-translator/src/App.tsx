import { useState, useEffect } from 'react';
import { UploadZone } from './components/UploadZone';
import { ProgressDashboard } from './components/ProgressDashboard';
import { ResultsViewer } from './components/ResultsViewer';
import { sessionService } from './services/SessionService';
import { apiService } from './services/ApiService';
import type { UploadedFile, Session } from './types/TranslationTypes';
import { API_ENDPOINTS, SUCCESS_MESSAGES } from './config/constants';
import { Database, Zap, FileText, Shield, Github } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

function App() {
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [step, setStep] = useState<'upload' | 'processing' | 'completed'>('upload');

  // Load existing session on mount
  useEffect(() => {
    const session = sessionService.getCurrentSession();
    if (session && sessionService.isSessionValid()) {
      setCurrentSession(session);

      // Determine current step based on session status
      if (session.status === 'completed') {
        setStep('completed');
      } else if (session.status === 'processing') {
        setStep('processing');
        setIsProcessing(true);
      } else {
        setStep('upload');
      }
    }
  }, []);

  // Handle successful file upload
  const handleFilesUploaded = async (uploadedFiles: UploadedFile[]) => {
    try {
      // Create new session
      const session = sessionService.createSession(uploadedFiles);
      setCurrentSession(session);

      toast.success(SUCCESS_MESSAGES.UPLOAD_SUCCESS);

      // Start processing automatically
      await startProcessing(session.id);

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create session';
      toast.error(message);
    }
  };

  // Start processing pipeline
  const startProcessing = async (sessionId: string) => {
    try {
      setIsProcessing(true);
      setStep('processing');

      sessionService.updateSessionStatus('processing');

      // Call backend to start processing
      await apiService.post(`${API_ENDPOINTS.PROCESS}/${sessionId}`);

      toast.success(SUCCESS_MESSAGES.PROCESSING_STARTED);

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start processing';
      toast.error(message);
      setIsProcessing(false);
      sessionService.updateSessionStatus('error', message);
    }
  };

  // Handle processing completion
  const handleProcessingComplete = () => {
    setIsProcessing(false);
    setStep('completed');
    sessionService.updateSessionStatus('completed');
    toast.success('Translation completed successfully!');
  };

  // Handle processing error
  const handleProcessingError = (error: Error) => {
    setIsProcessing(false);
    sessionService.updateSessionStatus('error', error.message);
    toast.error(`Processing failed: ${error.message}`);
  };

  // Handle upload error
  const handleUploadError = (error: string) => {
    toast.error(error);
  };

  // Start new session
  const startNewSession = () => {
    sessionService.clearSession();
    setCurrentSession(null);
    setStep('upload');
    setIsProcessing(false);
  };

  return (
    <div className="min-h-screen bg-secondary-50">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          className: 'text-sm',
        }}
      />

      {/* Header */}
      <header className="bg-white shadow-sm border-b border-secondary-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary-600 text-white rounded-lg">
                  <Database size={24} />
                </div>
                <div>
                  <h1 className="text-2xl font-bold gradient-text">
                    Informatica → Snowflake
                  </h1>
                  <p className="text-sm text-secondary-600">
                    Automated Translation Platform
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {currentSession && (
                <div className="text-sm text-secondary-600">
                  <span className="font-medium">Session:</span>{' '}
                  <span className="font-mono">{currentSession.id.slice(-8)}</span>
                </div>
              )}
              <button
                onClick={startNewSession}
                className="btn btn-secondary text-sm"
                disabled={isProcessing}
              >
                New Translation
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {step === 'upload' && (
          <div className="space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-6">
              <div className="space-y-4">
                <h2 className="text-4xl font-bold text-secondary-900">
                  Transform Your ETL Workflows
                </h2>
                <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
                  Upload your Informatica XML files and automatically generate complete
                  Snowflake migration packages with SQL, tests, and documentation.
                </p>
              </div>

              {/* Features */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
                <div className="text-center space-y-3">
                  <div className="p-3 bg-primary-100 text-primary-600 rounded-lg w-fit mx-auto">
                    <Zap size={24} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary-900">6-Phase Pipeline</h3>
                    <p className="text-sm text-secondary-600">
                      Automated README, SQL, tests, and configuration generation
                    </p>
                  </div>
                </div>

                <div className="text-center space-y-3">
                  <div className="p-3 bg-success-100 text-success-600 rounded-lg w-fit mx-auto">
                    <FileText size={24} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary-900">Complete Migration</h3>
                    <p className="text-sm text-secondary-600">
                      Everything needed for production Snowflake deployment
                    </p>
                  </div>
                </div>

                <div className="text-center space-y-3">
                  <div className="p-3 bg-warning-100 text-warning-600 rounded-lg w-fit mx-auto">
                    <Shield size={24} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary-900">Validated Output</h3>
                    <p className="text-sm text-secondary-600">
                      Syntax-checked SQL with comprehensive test suites
                    </p>
                  </div>
                </div>

                <div className="text-center space-y-3">
                  <div className="p-3 bg-secondary-100 text-secondary-600 rounded-lg w-fit mx-auto">
                    <Github size={24} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary-900">Enterprise Ready</h3>
                    <p className="text-sm text-secondary-600">
                      Scales to handle complex enterprise workflows
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Upload Zone */}
            <div className="max-w-4xl mx-auto">
              <UploadZone
                onFilesUploaded={handleFilesUploaded}
                onError={handleUploadError}
                className="animate-fade-in"
              />
            </div>

            {/* Instructions */}
            <div className="max-w-4xl mx-auto">
              <div className="card">
                <h3 className="text-lg font-semibold text-secondary-900 mb-4">
                  Getting Started
                </h3>
                <div className="space-y-4 text-sm text-secondary-700">
                  <div className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs font-medium">
                      1
                    </span>
                    <div>
                      <strong>Upload XML Files:</strong> Select your Informatica workflow XML files
                      and any associated .param files from your local system.
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs font-medium">
                      2
                    </span>
                    <div>
                      <strong>Automatic Processing:</strong> Our 6-phase pipeline will analyze your workflows
                      and generate complete Snowflake migration packages.
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs font-medium">
                      3
                    </span>
                    <div>
                      <strong>Download Results:</strong> Get SQL files, test suites, documentation,
                      and configuration files ready for deployment.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'processing' && currentSession && (
          <div className="max-w-6xl mx-auto animate-fade-in">
            <ProgressDashboard
              sessionId={currentSession.id}
              onComplete={handleProcessingComplete}
              onError={handleProcessingError}
            />
          </div>
        )}

        {step === 'completed' && currentSession && (
          <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
            <ProgressDashboard
              sessionId={currentSession.id}
              onComplete={handleProcessingComplete}
              onError={handleProcessingError}
            />

            <ResultsViewer
              sessionId={currentSession.id}
            />

            <div className="card bg-primary-50 border-primary-200">
              <button
                onClick={startNewSession}
                className="btn btn-secondary"
              >
                Start New Translation
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-secondary-200 bg-white mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-secondary-600">
            <p>&copy; 2026 Informatica to Snowflake Translator. Built with modern web technologies.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
