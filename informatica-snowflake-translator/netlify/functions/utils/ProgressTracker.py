"""
Progress Tracking Utility for Informatica Translation Pipeline
Manages phase-by-phase progress updates for the 6-phase translation process.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks and persists progress for the 6-phase translation pipeline.
    In production, this would use Netlify Blob storage or similar.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.progress_data = self._initialize_progress()

    def _initialize_progress(self) -> Dict[str, Any]:
        """Initialize progress structure for all phases."""
        return {
            "session_id": self.session_id,
            "overall_progress": 0,
            "current_phase": "Phase A",
            "phases": {
                "Phase A": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Generate detailed README from XML",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                },
                "Phase B": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Find and copy .param file",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                },
                "Phase C": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Generate Snowflake SQL files",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                },
                "Phase D": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Generate test files",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                },
                "Phase E": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Generate snowflake.yml",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                },
                "Phase F": {
                    "status": "pending",
                    "progress": 0,
                    "description": "Generate test_data folder",
                    "started_at": None,
                    "completed_at": None,
                    "current_step": None
                }
            },
            "errors": [],
            "warnings": [],
            "started_at": datetime.now().isoformat(),
            "estimated_completion": None,
            "completed_at": None
        }

    def update_phase(self, phase_name: str, progress: int, current_step: str = None):
        """Update progress for a specific phase."""
        try:
            if phase_name not in self.progress_data["phases"]:
                logger.warning(f"Unknown phase: {phase_name}")
                return

            phase_data = self.progress_data["phases"][phase_name]

            # Update phase status based on progress
            if progress == 0 and phase_data["status"] == "pending":
                phase_data["status"] = "in_progress"
                phase_data["started_at"] = datetime.now().isoformat()
                self.progress_data["current_phase"] = phase_name
            elif progress == 100:
                phase_data["status"] = "completed"
                phase_data["completed_at"] = datetime.now().isoformat()

            phase_data["progress"] = min(100, max(0, progress))

            if current_step:
                phase_data["current_step"] = current_step

            # Update overall progress
            self._update_overall_progress()

            # Persist progress
            self._persist_progress()

            logger.info(f"Progress updated - {phase_name}: {progress}%")

        except Exception as e:
            logger.error(f"Failed to update progress for {phase_name}: {e}")

    def add_error(self, phase_name: str, message: str, details: str = None, severity: str = "high"):
        """Add an error to the progress tracking."""
        error = {
            "phase": phase_name,
            "message": message,
            "details": details,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }

        self.progress_data["errors"].append(error)

        # Mark phase as error if not already completed
        if phase_name in self.progress_data["phases"]:
            phase_data = self.progress_data["phases"][phase_name]
            if phase_data["status"] != "completed":
                phase_data["status"] = "error"

        self._persist_progress()
        logger.error(f"Error added to {phase_name}: {message}")

    def add_warning(self, phase_name: str, message: str, details: str = None):
        """Add a warning to the progress tracking."""
        warning = {
            "phase": phase_name,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        self.progress_data["warnings"].append(warning)
        self._persist_progress()
        logger.warning(f"Warning added to {phase_name}: {message}")

    def mark_completed(self):
        """Mark the entire pipeline as completed."""
        self.progress_data["overall_progress"] = 100
        self.progress_data["completed_at"] = datetime.now().isoformat()

        # Ensure all phases are marked as completed
        for phase_name, phase_data in self.progress_data["phases"].items():
            if phase_data["status"] not in ["completed", "error"]:
                phase_data["status"] = "completed"
                phase_data["progress"] = 100
                if not phase_data["completed_at"]:
                    phase_data["completed_at"] = datetime.now().isoformat()

        self._persist_progress()
        logger.info(f"Pipeline marked as completed for session {self.session_id}")

    def mark_failed(self, error_message: str):
        """Mark the entire pipeline as failed."""
        self.progress_data["status"] = "failed"
        self.progress_data["completed_at"] = datetime.now().isoformat()

        # Add general error
        self.add_error("Pipeline", error_message, severity="critical")

        self._persist_progress()
        logger.error(f"Pipeline marked as failed for session {self.session_id}: {error_message}")

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress data."""
        return self.progress_data.copy()

    def _update_overall_progress(self):
        """Calculate and update overall progress based on phase progress."""
        total_progress = 0
        completed_phases = 0

        for phase_data in self.progress_data["phases"].values():
            total_progress += phase_data["progress"]
            if phase_data["status"] == "completed":
                completed_phases += 1

        # Overall progress is average of all phase progress
        self.progress_data["overall_progress"] = int(total_progress / len(self.progress_data["phases"]))

        # Update estimated completion time
        if self.progress_data["overall_progress"] > 0:
            self._update_estimated_completion()

    def _update_estimated_completion(self):
        """Update estimated completion time based on current progress."""
        try:
            started_at = datetime.fromisoformat(self.progress_data["started_at"])
            current_time = datetime.now()
            elapsed_seconds = (current_time - started_at).total_seconds()

            if self.progress_data["overall_progress"] > 0:
                # Simple linear estimation
                total_estimated_seconds = (elapsed_seconds / self.progress_data["overall_progress"]) * 100
                remaining_seconds = total_estimated_seconds - elapsed_seconds

                if remaining_seconds > 0:
                    estimated_completion = current_time.timestamp() + remaining_seconds
                    self.progress_data["estimated_completion"] = datetime.fromtimestamp(estimated_completion).isoformat()

        except Exception as e:
            logger.warning(f"Failed to update estimated completion: {e}")

    def _persist_progress(self):
        """
        Persist progress data to storage.
        In production, this would use Netlify Blob storage or similar persistent storage.
        For development, we'll store in memory or local file system.
        """
        try:
            # In production, this would be:
            # await blob_store.set(f"progress/{self.session_id}", json.dumps(self.progress_data))

            # For development, we could store in a temporary location
            progress_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp", "progress")
            os.makedirs(progress_dir, exist_ok=True)

            progress_file = os.path.join(progress_dir, f"{self.session_id}.json")
            with open(progress_file, 'w') as f:
                json.dump(self.progress_data, f, indent=2)

            logger.debug(f"Progress persisted for session {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to persist progress for session {self.session_id}: {e}")

    @classmethod
    def load_progress(cls, session_id: str) -> Optional['ProgressTracker']:
        """
        Load existing progress data for a session.
        Returns None if no progress data exists.
        """
        try:
            progress_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp", "progress")
            progress_file = os.path.join(progress_dir, f"{session_id}.json")

            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)

                tracker = cls.__new__(cls)
                tracker.session_id = session_id
                tracker.progress_data = progress_data

                logger.info(f"Loaded existing progress for session {session_id}")
                return tracker

        except Exception as e:
            logger.error(f"Failed to load progress for session {session_id}: {e}")

        return None

    def get_phase_summary(self) -> Dict[str, Any]:
        """Get a summary of phase statuses."""
        summary = {
            "total_phases": len(self.progress_data["phases"]),
            "completed_phases": 0,
            "in_progress_phases": 0,
            "pending_phases": 0,
            "error_phases": 0,
            "current_phase": self.progress_data["current_phase"],
            "overall_progress": self.progress_data["overall_progress"]
        }

        for phase_data in self.progress_data["phases"].values():
            status = phase_data["status"]
            if status == "completed":
                summary["completed_phases"] += 1
            elif status == "in_progress":
                summary["in_progress_phases"] += 1
            elif status == "pending":
                summary["pending_phases"] += 1
            elif status == "error":
                summary["error_phases"] += 1

        return summary

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        try:
            started_at = datetime.fromisoformat(self.progress_data["started_at"])
            current_time = datetime.now()
            elapsed_ms = int((current_time - started_at).total_seconds() * 1000)

            completed_at = None
            if self.progress_data.get("completed_at"):
                completed_at = datetime.fromisoformat(self.progress_data["completed_at"])

            return {
                "session_id": self.session_id,
                "started_at": self.progress_data["started_at"],
                "completed_at": self.progress_data.get("completed_at"),
                "elapsed_time_ms": elapsed_ms,
                "estimated_completion": self.progress_data.get("estimated_completion"),
                "total_errors": len(self.progress_data["errors"]),
                "total_warnings": len(self.progress_data["warnings"]),
                "phase_summary": self.get_phase_summary()
            }

        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {"error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    # Test the progress tracker
    tracker = ProgressTracker("test_session_123")

    print("Initial progress:")
    print(json.dumps(tracker.get_progress(), indent=2))

    # Simulate phase updates
    tracker.update_phase("Phase A", 50, "Parsing XML structure")
    tracker.update_phase("Phase A", 100)

    tracker.update_phase("Phase B", 30, "Searching for parameter files")
    tracker.add_warning("Phase B", "Parameter file not found in expected location")
    tracker.update_phase("Phase B", 100)

    print("\nProgress after Phase A and B:")
    print(json.dumps(tracker.get_phase_summary(), indent=2))

    # Test error handling
    tracker.add_error("Phase C", "SQL generation failed", "Invalid transformation mapping")

    print("\nFinal stats:")
    print(json.dumps(tracker.get_processing_stats(), indent=2))