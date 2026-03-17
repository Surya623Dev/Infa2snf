import React, { useEffect, useState } from 'react';
import { Check, Clock, CircleAlert as AlertCircle, Loader, FileText, Database, Code, TestTube, Settings, FolderOpen, Download } from 'lucide-react';
import type { ProcessingProgress, PhaseType, PhaseStatus } from '../types/TranslationTypes';
import { progressService } from '../services/ProgressService';
import { PROCESSING } from '../config/constants';

export interface ProgressDashboardProps {
  sessionId: string;
  onComplete?: (progress: ProcessingProgress) => void;
  onError?: (error: Error) => void;
  className?: string;
}

const PHASE_ICONS: Record<PhaseType, React.ElementType> = {
  'Phase A': FileText,
  'Phase B': Database,
  'Phase C': Code,
  'Phase D': TestTube,
  'Phase E': Settings,
  'Phase F': FolderOpen,
};

const PHASE_COLORS: Record<PhaseStatus, string> = {
  pending: 'text-secondary-500 bg-secondary-100',
  in_progress: 'text-primary-600 bg-primary-100',
  completed: 'text-success-600 bg-success-100',
  error: 'text-danger-600 bg-danger-100',
};

export const ProgressDashboard: React.FC<ProgressDashboardProps> = ({
  sessionId,
  onComplete,
  onError,
  className = '',
}) => {
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState(0);

  // Start progress polling
  useEffect(() => {
    if (!sessionId) return;

    const startTime = Date.now();

    progressService.startPolling(sessionId, {
      onUpdate: (progressData) => {
        setProgress(progressData);
        setIsLoading(false);
        setError(null);

        // Update time calculations
        const elapsed = Date.now() - startTime;
        setTimeElapsed(elapsed);

        // Simple estimation based on current progress
        if (progressData.overallProgress > 0 && progressData.overallProgress < 100) {
          const totalEstimated = (elapsed / progressData.overallProgress) * 100;
          setEstimatedTimeRemaining(Math.max(0, totalEstimated - elapsed));
        } else if (progressData.overallProgress >= 100) {
          setEstimatedTimeRemaining(0);
        }
      },
      onComplete: (finalProgress) => {
        setProgress(finalProgress);
        setIsLoading(false);
        setEstimatedTimeRemaining(0);
        onComplete?.(finalProgress);
      },
      onError: (err) => {
        setError(err.message);
        setIsLoading(false);
        onError?.(err);
      },
    });

    return () => {
      progressService.stopPolling(sessionId);
    };
  }, [sessionId, onComplete, onError]);

  // Format time duration
  const formatDuration = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  if (isLoading) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="text-center space-y-4">
            <Loader className="mx-auto animate-spin text-primary-600" size={48} />
            <p className="text-secondary-600">Initializing processing...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center space-x-3 text-danger-600">
          <AlertCircle size={24} />
          <div>
            <h3 className="font-semibold">Processing Error</h3>
            <p className="text-sm text-danger-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!progress) {
    return (
      <div className={`card ${className}`}>
        <div className="text-center py-8">
          <p className="text-secondary-600">No progress data available</p>
        </div>
      </div>
    );
  }

  const isComplete = progress.overallProgress >= 100;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overall Progress */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-secondary-900">
              Translation Progress
            </h2>
            <div className="flex items-center space-x-4 text-sm text-secondary-600">
              <div className="flex items-center space-x-1">
                <Clock size={16} />
                <span>Elapsed: {formatDuration(timeElapsed)}</span>
              </div>
              {!isComplete && estimatedTimeRemaining > 0 && (
                <div className="flex items-center space-x-1">
                  <Clock size={16} />
                  <span>Remaining: ~{formatDuration(estimatedTimeRemaining)}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-secondary-700">Overall Progress</span>
              <span className="text-secondary-600">{progress.overallProgress}%</span>
            </div>
            <div className="progress-bar h-3">
              <div
                className={`
                  progress-fill h-full transition-all duration-500 ease-out
                  ${isComplete ? 'progress-fill-success' : ''}
                `}
                style={{ width: `${progress.overallProgress}%` }}
              />
            </div>
          </div>

          {/* Current Phase */}
          <div className="flex items-center justify-between p-4 bg-primary-50 rounded-lg border border-primary-200">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-600 text-white rounded-lg">
                {React.createElement(PHASE_ICONS[progress.currentPhase], { size: 20 })}
              </div>
              <div>
                <h3 className="font-medium text-primary-900">
                  {isComplete ? 'Translation Complete' : `Current: ${progress.currentPhase}`}
                </h3>
                <p className="text-sm text-primary-700">
                  {isComplete
                    ? 'All phases completed successfully'
                    : progress.phases[progress.currentPhase]?.description
                  }
                </p>
              </div>
            </div>
            {isComplete && (
              <div className="p-2 bg-success-600 text-white rounded-full">
                <Check size={24} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Phase Details */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-secondary-900">Phase Details</h3>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {PROCESSING.PHASES.map((phaseConfig) => {
            const phaseKey = phaseConfig.key as PhaseType;
            const phaseData = progress.phases[phaseKey];
            const Icon = PHASE_ICONS[phaseKey];
            const statusColors = PHASE_COLORS[phaseData.status];

            return (
              <div
                key={phaseKey}
                className={`
                  phase-indicator
                  phase-indicator-${phaseData.status}
                  ${progress.currentPhase === phaseKey ? 'ring-2 ring-primary-300' : ''}
                `}
              >
                <div className={`p-2 rounded-lg ${statusColors}`}>
                  <Icon size={20} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">{phaseConfig.name}</h4>
                    <div className="flex items-center space-x-2">
                      {phaseData.status === 'in_progress' && (
                        <Loader size={16} className="animate-spin" />
                      )}
                      {phaseData.status === 'completed' && (
                        <Check size={16} className="text-success-600" />
                      )}
                      {phaseData.status === 'error' && (
                        <AlertCircle size={16} className="text-danger-600" />
                      )}
                      <span className="text-xs font-medium">
                        {phaseData.progress}%
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-secondary-600 mt-1">
                    {phaseConfig.description}
                  </p>

                  {phaseData.status === 'in_progress' && phaseData.progress > 0 && (
                    <div className="mt-2">
                      <div className="progress-bar h-1">
                        <div
                          className="progress-fill h-full"
                          style={{ width: `${phaseData.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {phaseData.currentStep && (
                    <p className="text-xs text-primary-700 mt-1 font-medium">
                      {phaseData.currentStep}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Errors and Warnings */}
      {(progress.errors.length > 0 || progress.warnings.length > 0) && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-secondary-900">
              Issues & Warnings
            </h3>
          </div>

          <div className="space-y-4">
            {progress.errors.length > 0 && (
              <div>
                <h4 className="font-medium text-danger-800 mb-3 flex items-center space-x-2">
                  <AlertCircle size={18} />
                  <span>Errors ({progress.errors.length})</span>
                </h4>
                <div className="space-y-2">
                  {progress.errors.map((error, index) => (
                    <div
                      key={index}
                      className="p-3 bg-danger-50 border border-danger-200 rounded-lg"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-danger-800 font-medium">{error.message}</p>
                          {error.details && (
                            <p className="text-danger-700 text-sm mt-1">{error.details}</p>
                          )}
                        </div>
                        <div className="text-xs text-danger-600 ml-4">
                          {error.phase}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {progress.warnings.length > 0 && (
              <div>
                <h4 className="font-medium text-warning-800 mb-3 flex items-center space-x-2">
                  <AlertCircle size={18} />
                  <span>Warnings ({progress.warnings.length})</span>
                </h4>
                <div className="space-y-2">
                  {progress.warnings.map((warning, index) => (
                    <div
                      key={index}
                      className="p-3 bg-warning-50 border border-warning-200 rounded-lg"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-warning-800 font-medium">{warning.message}</p>
                          {warning.details && (
                            <p className="text-warning-700 text-sm mt-1">{warning.details}</p>
                          )}
                        </div>
                        <div className="text-xs text-warning-600 ml-4">
                          {warning.phase}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Completion Actions */}
      {isComplete && (
        <div className="card bg-success-50 border-success-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-success-600 text-white rounded-full">
                <Check size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-success-900">
                  Translation Completed Successfully!
                </h3>
                <p className="text-success-700">
                  All phases completed in {formatDuration(timeElapsed)}. Your files are ready for download.
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                const link = document.createElement('a');
                link.href = '#results';
                link.click();
              }}
              className="btn btn-success flex items-center space-x-2"
            >
              <Download size={20} />
              <span>Download Results</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};