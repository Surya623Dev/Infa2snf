import { apiService } from './ApiService';
import { sessionService } from './SessionService';
import type { ProcessingProgress, PhaseType, PhaseStatus } from '../types/TranslationTypes';
import { API_ENDPOINTS, PROCESSING, DEV_FLAGS } from '../config/constants';

export interface ProgressUpdateCallback {
  (progress: ProcessingProgress): void;
}

export interface ProgressCompleteCallback {
  (finalProgress: ProcessingProgress): void;
}

export interface ProgressErrorCallback {
  (error: Error): void;
}

class ProgressService {
  private pollingIntervals: Map<string, number> = new Map();
  private callbacks: Map<string, {
    onUpdate?: ProgressUpdateCallback;
    onComplete?: ProgressCompleteCallback;
    onError?: ProgressErrorCallback;
  }> = new Map();

  // Start polling progress for a session
  startPolling(
    sessionId: string,
    callbacks?: {
      onUpdate?: ProgressUpdateCallback;
      onComplete?: ProgressCompleteCallback;
      onError?: ProgressErrorCallback;
    }
  ): void {
    // Stop existing polling for this session
    this.stopPolling(sessionId);

    if (callbacks) {
      this.callbacks.set(sessionId, callbacks);
    }

    // Start polling
    const poll = async () => {
      try {
        const progress = await this.getProgress(sessionId);

        // Update session service
        sessionService.updateSessionProgress(progress);

        // Call update callback
        const sessionCallbacks = this.callbacks.get(sessionId);
        if (sessionCallbacks?.onUpdate) {
          sessionCallbacks.onUpdate(progress);
        }

        // Check if completed
        if (this.isProgressComplete(progress)) {
          this.stopPolling(sessionId);
          if (sessionCallbacks?.onComplete) {
            sessionCallbacks.onComplete(progress);
          }
          return;
        }

        // Continue polling
        const timeout = setTimeout(poll, PROCESSING.POLLING_INTERVAL);
        this.pollingIntervals.set(sessionId, timeout);

      } catch (error) {
        console.error(`Progress polling error for session ${sessionId}:`, error);

        const sessionCallbacks = this.callbacks.get(sessionId);
        if (sessionCallbacks?.onError) {
          sessionCallbacks.onError(error as Error);
        }

        // Continue polling on error (might be temporary)
        const timeout = setTimeout(poll, PROCESSING.POLLING_INTERVAL * 2);
        this.pollingIntervals.set(sessionId, timeout);
      }
    };

    // Start immediate poll
    poll();
  }

  // Stop polling for a session
  stopPolling(sessionId: string): void {
    const interval = this.pollingIntervals.get(sessionId);
    if (interval) {
      clearTimeout(interval);
      this.pollingIntervals.delete(sessionId);
    }

    this.callbacks.delete(sessionId);
  }

  // Get current progress for a session
  async getProgress(sessionId: string): Promise<ProcessingProgress> {
    if (DEV_FLAGS.MOCK_API) {
      return this.getMockProgress(sessionId);
    }

    try {
      const progress = await apiService.get<ProcessingProgress>(
        `${API_ENDPOINTS.PROGRESS}/${sessionId}`
      );

      return progress;
    } catch (error) {
      throw new Error(`Failed to get progress for session ${sessionId}: ${error}`);
    }
  }

  // Mock progress for development
  private getMockProgress(sessionId: string): ProcessingProgress {
    const session = sessionService.getCurrentSession();
    if (!session || session.id !== sessionId) {
      throw new Error(`Session ${sessionId} not found`);
    }

    // Simulate progress based on time elapsed
    const elapsed = Date.now() - session.createdAt.getTime();
    const totalTime = 5 * 60 * 1000; // 5 minutes total
    const overallProgress = Math.min(100, (elapsed / totalTime) * 100);

    // Determine current phase
    let currentPhase: PhaseType = 'Phase A';
    const phases = PROCESSING.PHASES;

    const phaseStatuses: Record<PhaseType, PhaseStatus> = {
      'Phase A': 'pending',
      'Phase B': 'pending',
      'Phase C': 'pending',
      'Phase D': 'pending',
      'Phase E': 'pending',
      'Phase F': 'pending',
    };

    const phaseProgressValues: Record<PhaseType, number> = {
      'Phase A': 0,
      'Phase B': 0,
      'Phase C': 0,
      'Phase D': 0,
      'Phase E': 0,
      'Phase F': 0,
    };

    // Update phases based on overall progress
    phases.forEach((phase, index) => {
      const phaseStart = index * (100 / phases.length);
      const phaseEnd = (index + 1) * (100 / phases.length);

      if (overallProgress > phaseEnd) {
        phaseStatuses[phase.key as PhaseType] = 'completed';
        phaseProgressValues[phase.key as PhaseType] = 100;
      } else if (overallProgress > phaseStart) {
        phaseStatuses[phase.key as PhaseType] = 'in_progress';
        phaseProgressValues[phase.key as PhaseType] = ((overallProgress - phaseStart) / (phaseEnd - phaseStart)) * 100;
        currentPhase = phase.key as PhaseType;
      }
    });

    return {
      sessionId,
      overallProgress: Math.round(overallProgress),
      currentPhase,
      phases: {
        'Phase A': {
          status: phaseStatuses['Phase A'],
          progress: Math.round(phaseProgressValues['Phase A']),
          description: 'Generate detailed README from XML',
        },
        'Phase B': {
          status: phaseStatuses['Phase B'],
          progress: Math.round(phaseProgressValues['Phase B']),
          description: 'Find and copy .param file',
        },
        'Phase C': {
          status: phaseStatuses['Phase C'],
          progress: Math.round(phaseProgressValues['Phase C']),
          description: 'Generate Snowflake SQL files',
        },
        'Phase D': {
          status: phaseStatuses['Phase D'],
          progress: Math.round(phaseProgressValues['Phase D']),
          description: 'Generate test files',
        },
        'Phase E': {
          status: phaseStatuses['Phase E'],
          progress: Math.round(phaseProgressValues['Phase E']),
          description: 'Generate snowflake.yml',
        },
        'Phase F': {
          status: phaseStatuses['Phase F'],
          progress: Math.round(phaseProgressValues['Phase F']),
          description: 'Generate test_data folder',
        },
      },
      errors: [],
      warnings: [],
      estimatedCompletion: new Date(session.createdAt.getTime() + totalTime).toISOString(),
      startedAt: session.createdAt,
      completedAt: overallProgress === 100 ? new Date() : undefined,
    };
  }

  // Check if progress is complete
  private isProgressComplete(progress: ProcessingProgress): boolean {
    return progress.overallProgress >= 100 ||
           Object.values(progress.phases).every(phase => phase.status === 'completed');
  }

  // Get estimated completion time
  getEstimatedCompletion(sessionId: string): Date | null {
    const session = sessionService.getSessionById(sessionId);
    if (!session) return null;

    // Simple estimation based on average processing time
    const averageTime = 5 * 60 * 1000; // 5 minutes average
    return new Date(session.createdAt.getTime() + averageTime);
  }

  // Get processing statistics
  getProcessingStats(sessionId: string): {
    totalPhases: number;
    completedPhases: number;
    currentPhase: string;
    timeElapsed: number;
    estimatedTimeRemaining: number;
  } | null {
    const session = sessionService.getSessionById(sessionId);
    if (!session) return null;

    const progress = session.progress;
    const completedPhases = Object.values(progress.phases).filter(
      phase => phase.status === 'completed'
    ).length;

    const timeElapsed = Date.now() - session.createdAt.getTime();
    const estimatedTotal = timeElapsed * (PROCESSING.PHASES.length / Math.max(completedPhases, 1));
    const estimatedTimeRemaining = Math.max(0, estimatedTotal - timeElapsed);

    return {
      totalPhases: PROCESSING.PHASES.length,
      completedPhases,
      currentPhase: progress.currentPhase,
      timeElapsed,
      estimatedTimeRemaining,
    };
  }

  // Format time duration
  formatDuration(milliseconds: number): string {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }

  // Clean up all polling
  cleanup(): void {
    this.pollingIntervals.forEach((_, sessionId) => {
      this.stopPolling(sessionId);
    });
  }
}

// Export singleton instance
export const progressService = new ProgressService();

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    progressService.cleanup();
  });
}

export default ProgressService;