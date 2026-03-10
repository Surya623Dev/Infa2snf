import { Session, SessionStatus, UploadedFile, ProcessingProgress } from '../types/TranslationTypes';
import { STORAGE_KEYS, PROCESSING } from '../config/constants';

class SessionService {
  private currentSession: Session | null = null;

  constructor() {
    this.loadSessionFromStorage();
  }

  // Create a new session
  createSession(uploadedFiles: UploadedFile[]): Session {
    const session: Session = {
      id: this.generateSessionId(),
      createdAt: new Date(),
      status: 'initializing',
      uploadedFiles,
      progress: this.createInitialProgress(),
    };

    this.currentSession = session;
    this.saveSessionToStorage();
    return session;
  }

  // Get current session
  getCurrentSession(): Session | null {
    return this.currentSession;
  }

  // Update session status
  updateSessionStatus(status: SessionStatus, error?: string): void {
    if (!this.currentSession) return;

    this.currentSession.status = status;
    if (error) {
      this.currentSession.error = error;
    }

    this.saveSessionToStorage();
  }

  // Update session progress
  updateSessionProgress(progress: ProcessingProgress): void {
    if (!this.currentSession) return;

    this.currentSession.progress = progress;

    // Update status based on progress
    if (progress.overallProgress === 100) {
      this.currentSession.status = 'completed';
    } else if (progress.overallProgress > 0) {
      this.currentSession.status = 'processing';
    }

    this.saveSessionToStorage();
  }

  // Clear current session
  clearSession(): void {
    this.currentSession = null;
    this.removeSessionFromStorage();
  }

  // Check if session is valid (not expired)
  isSessionValid(): boolean {
    if (!this.currentSession) return false;

    const now = new Date().getTime();
    const sessionTime = this.currentSession.createdAt.getTime();
    const sessionTimeout = PROCESSING.SESSION_TIMEOUT;

    return (now - sessionTime) < sessionTimeout;
  }

  // Get session by ID
  getSessionById(sessionId: string): Session | null {
    if (this.currentSession?.id === sessionId) {
      return this.currentSession;
    }

    // Try to load from recent sessions
    const recentSessions = this.getRecentSessions();
    return recentSessions.find(session => session.id === sessionId) || null;
  }

  // Save session to recent sessions
  saveToRecentSessions(): void {
    if (!this.currentSession) return;

    const recentSessions = this.getRecentSessions();
    const existingIndex = recentSessions.findIndex(s => s.id === this.currentSession!.id);

    if (existingIndex >= 0) {
      recentSessions[existingIndex] = this.currentSession;
    } else {
      recentSessions.unshift(this.currentSession);
      // Keep only last 10 sessions
      if (recentSessions.length > 10) {
        recentSessions.splice(10);
      }
    }

    localStorage.setItem(STORAGE_KEYS.RECENT_SESSIONS, JSON.stringify(recentSessions));
  }

  // Get recent sessions
  getRecentSessions(): Session[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.RECENT_SESSIONS);
      if (!stored) return [];

      const sessions = JSON.parse(stored) as Session[];
      // Convert date strings back to Date objects
      return sessions.map(session => ({
        ...session,
        createdAt: new Date(session.createdAt),
        uploadedFiles: session.uploadedFiles.map(file => ({
          ...file,
          uploadedAt: new Date(file.uploadedAt),
        })),
      }));
    } catch (error) {
      console.error('Error loading recent sessions:', error);
      return [];
    }
  }

  // Generate unique session ID
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  // Create initial progress structure
  private createInitialProgress(): ProcessingProgress {
    const phases = PROCESSING.PHASES.reduce((acc, phase) => {
      acc[phase.key as keyof typeof acc] = {
        status: 'pending',
        progress: 0,
        description: phase.description,
      };
      return acc;
    }, {} as ProcessingProgress['phases']);

    return {
      sessionId: this.currentSession?.id || '',
      overallProgress: 0,
      currentPhase: 'Phase A',
      phases,
      errors: [],
      warnings: [],
    };
  }

  // Save session to localStorage
  private saveSessionToStorage(): void {
    if (!this.currentSession) return;

    try {
      localStorage.setItem(STORAGE_KEYS.SESSION_ID, this.currentSession.id);
      // Also save to recent sessions
      this.saveToRecentSessions();
    } catch (error) {
      console.error('Error saving session to storage:', error);
    }
  }

  // Load session from localStorage
  private loadSessionFromStorage(): void {
    try {
      const sessionId = localStorage.getItem(STORAGE_KEYS.SESSION_ID);
      if (!sessionId) return;

      const recentSessions = this.getRecentSessions();
      const session = recentSessions.find(s => s.id === sessionId);

      if (session && this.isSessionValidForSession(session)) {
        this.currentSession = session;
      } else {
        // Remove invalid session ID
        localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
      }
    } catch (error) {
      console.error('Error loading session from storage:', error);
    }
  }

  // Remove session from localStorage
  private removeSessionFromStorage(): void {
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
  }

  // Check if a specific session is valid
  private isSessionValidForSession(session: Session): boolean {
    const now = new Date().getTime();
    const sessionTime = session.createdAt.getTime();
    const sessionTimeout = PROCESSING.SESSION_TIMEOUT;

    return (now - sessionTime) < sessionTimeout;
  }

  // Get session statistics
  getSessionStats(): {
    totalSessions: number;
    completedSessions: number;
    failedSessions: number;
    averageProcessingTime: number;
  } {
    const recentSessions = this.getRecentSessions();

    const completed = recentSessions.filter(s => s.status === 'completed');
    const failed = recentSessions.filter(s => s.status === 'error');

    const averageTime = completed.reduce((acc, session) => {
      if (session.progress.startedAt && session.progress.completedAt) {
        return acc + (session.progress.completedAt.getTime() - session.progress.startedAt.getTime());
      }
      return acc;
    }, 0) / completed.length || 0;

    return {
      totalSessions: recentSessions.length,
      completedSessions: completed.length,
      failedSessions: failed.length,
      averageProcessingTime: averageTime,
    };
  }
}

// Export singleton instance
export const sessionService = new SessionService();
export default SessionService;