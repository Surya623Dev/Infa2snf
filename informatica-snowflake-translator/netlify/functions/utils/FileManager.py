"""
File Management Utility for Informatica Translation Pipeline
Handles file operations including saving generated files, creating ZIP archives, and managing session data.
"""

import os
import json
import zipfile
import tempfile
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime
import logging
import shutil

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations for the translation pipeline.
    In production, this would integrate with Netlify Blob storage or similar.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_files: Dict[str, Dict[str, Any]] = {}

        # Create session directory for file storage
        self.session_dir = self._create_session_directory()

    def _create_session_directory(self) -> str:
        """Create a directory for session files."""
        try:
            # In production, this would be handled by blob storage
            # For development, create local session directory
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp", "sessions")
            session_dir = os.path.join(base_dir, self.session_id)

            os.makedirs(session_dir, exist_ok=True)
            os.makedirs(os.path.join(session_dir, "generated"), exist_ok=True)
            os.makedirs(os.path.join(session_dir, "test_data"), exist_ok=True)

            logger.info(f"Created session directory: {session_dir}")
            return session_dir

        except Exception as e:
            logger.error(f"Failed to create session directory: {e}")
            # Fallback to temp directory
            return tempfile.mkdtemp(prefix=f"session_{self.session_id}_")

    def save_file(self, filename: str, content: str, file_type: str = "text") -> str:
        """
        Save a file to the session storage.

        Args:
            filename: Name of the file (can include subdirectory like 'test_data/file.csv')
            content: File content as string
            file_type: Type of file (text, binary, etc.)

        Returns:
            Full path to the saved file
        """
        try:
            # Determine full file path
            if "/" in filename:
                # Handle subdirectories
                file_path = os.path.join(self.session_dir, filename)
                # Create subdirectories if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            else:
                file_path = os.path.join(self.session_dir, "generated", filename)

            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Track file metadata
            file_metadata = {
                "filename": filename,
                "path": file_path,
                "size": len(content.encode('utf-8')),
                "type": file_type,
                "created_at": datetime.now().isoformat(),
                "mime_type": self._get_mime_type(filename)
            }

            self.session_files[filename] = file_metadata

            logger.info(f"Saved file: {filename} ({file_metadata['size']} bytes)")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            raise

    def save_binary_file(self, filename: str, content: bytes) -> str:
        """
        Save binary content to a file.

        Args:
            filename: Name of the file
            content: Binary content

        Returns:
            Full path to the saved file
        """
        try:
            # Determine full file path
            if "/" in filename:
                file_path = os.path.join(self.session_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            else:
                file_path = os.path.join(self.session_dir, "generated", filename)

            # Write binary content
            with open(file_path, 'wb') as f:
                f.write(content)

            # Track file metadata
            file_metadata = {
                "filename": filename,
                "path": file_path,
                "size": len(content),
                "type": "binary",
                "created_at": datetime.now().isoformat(),
                "mime_type": self._get_mime_type(filename)
            }

            self.session_files[filename] = file_metadata

            logger.info(f"Saved binary file: {filename} ({file_metadata['size']} bytes)")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save binary file {filename}: {e}")
            raise

    def get_file_content(self, filename: str) -> Optional[str]:
        """
        Get the content of a saved file.

        Args:
            filename: Name of the file to read

        Returns:
            File content as string, or None if file not found
        """
        try:
            if filename not in self.session_files:
                logger.warning(f"File not found in session: {filename}")
                return None

            file_path = self.session_files[filename]["path"]
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to read file {filename}: {e}")
            return None

    def get_file_binary_content(self, filename: str) -> Optional[bytes]:
        """
        Get the binary content of a saved file.

        Args:
            filename: Name of the file to read

        Returns:
            File content as bytes, or None if file not found
        """
        try:
            if filename not in self.session_files:
                logger.warning(f"File not found in session: {filename}")
                return None

            file_path = self.session_files[filename]["path"]
            with open(file_path, 'rb') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to read binary file {filename}: {e}")
            return None

    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files in the session.

        Returns:
            List of file metadata dictionaries
        """
        return list(self.session_files.values())

    def get_file_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file.

        Args:
            filename: Name of the file

        Returns:
            File metadata dictionary, or None if file not found
        """
        return self.session_files.get(filename)

    def create_zip_archive(self, filename: str = None) -> str:
        """
        Create a ZIP archive containing all session files.

        Args:
            filename: Optional custom filename for the ZIP file

        Returns:
            Path to the created ZIP file
        """
        try:
            if not filename:
                filename = f"{self.session_id}_translation_package.zip"

            zip_path = os.path.join(self.session_dir, filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all session files to ZIP
                for file_metadata in self.session_files.values():
                    file_path = file_metadata["path"]
                    if os.path.exists(file_path):
                        # Use relative path in ZIP for clean structure
                        arcname = file_metadata["filename"]
                        zipf.write(file_path, arcname)

                # Add session metadata
                metadata = {
                    "session_id": self.session_id,
                    "created_at": datetime.now().isoformat(),
                    "files": list(self.session_files.keys()),
                    "total_files": len(self.session_files),
                    "total_size": sum(f["size"] for f in self.session_files.values())
                }

                zipf.writestr("session_metadata.json", json.dumps(metadata, indent=2))

            # Add ZIP to session files tracking
            zip_size = os.path.getsize(zip_path)
            self.session_files[filename] = {
                "filename": filename,
                "path": zip_path,
                "size": zip_size,
                "type": "archive",
                "created_at": datetime.now().isoformat(),
                "mime_type": "application/zip"
            }

            logger.info(f"Created ZIP archive: {filename} ({zip_size} bytes)")
            return zip_path

        except Exception as e:
            logger.error(f"Failed to create ZIP archive: {e}")
            raise

    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from the session.

        Args:
            filename: Name of the file to delete

        Returns:
            True if file was deleted, False otherwise
        """
        try:
            if filename not in self.session_files:
                logger.warning(f"File not found for deletion: {filename}")
                return False

            file_path = self.session_files[filename]["path"]
            if os.path.exists(file_path):
                os.remove(file_path)

            del self.session_files[filename]
            logger.info(f"Deleted file: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {filename}: {e}")
            return False

    def cleanup_session(self) -> bool:
        """
        Clean up all session files and directories.

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            if os.path.exists(self.session_dir):
                shutil.rmtree(self.session_dir)

            self.session_files.clear()
            logger.info(f"Cleaned up session directory: {self.session_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup session {self.session_id}: {e}")
            return False

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the session files.

        Returns:
            Dictionary with session statistics
        """
        total_size = sum(f["size"] for f in self.session_files.values())
        file_types = {}

        for file_metadata in self.session_files.values():
            file_type = file_metadata["type"]
            file_types[file_type] = file_types.get(file_type, 0) + 1

        return {
            "session_id": self.session_id,
            "total_files": len(self.session_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "session_directory": self.session_dir,
            "files": list(self.session_files.keys())
        }

    def _get_mime_type(self, filename: str) -> str:
        """
        Determine MIME type based on file extension.

        Args:
            filename: Name of the file

        Returns:
            MIME type string
        """
        extension = os.path.splitext(filename)[1].lower()

        mime_types = {
            '.sql': 'text/sql',
            '.snowsql': 'text/sql',
            '.md': 'text/markdown',
            '.yml': 'text/yaml',
            '.yaml': 'text/yaml',
            '.param': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.zip': 'application/zip',
            '.xml': 'text/xml',
        }

        return mime_types.get(extension, 'application/octet-stream')

    def generate_download_links(self) -> Dict[str, str]:
        """
        Generate download links for all files.
        In production, these would be signed URLs from blob storage.

        Returns:
            Dictionary mapping filenames to download URLs
        """
        # In production, this would generate signed URLs
        # For development, return file paths
        download_links = {}

        for filename, metadata in self.session_files.items():
            # In production: download_links[filename] = generate_signed_url(metadata["path"])
            download_links[filename] = f"/api/download/{self.session_id}/{filename}"

        return download_links

    def get_file_preview(self, filename: str, max_lines: int = 50) -> Optional[str]:
        """
        Get a preview of a text file (first N lines).

        Args:
            filename: Name of the file
            max_lines: Maximum number of lines to return

        Returns:
            Preview content as string, or None if file cannot be previewed
        """
        try:
            if filename not in self.session_files:
                return None

            metadata = self.session_files[filename]
            if metadata["type"] == "binary":
                return "Binary file - preview not available"

            content = self.get_file_content(filename)
            if not content:
                return None

            lines = content.split('\n')
            if len(lines) <= max_lines:
                return content

            # Return first max_lines with indication of truncation
            preview_lines = lines[:max_lines]
            preview_content = '\n'.join(preview_lines)
            preview_content += f"\n\n... (truncated - showing first {max_lines} of {len(lines)} lines)"

            return preview_content

        except Exception as e:
            logger.error(f"Failed to generate preview for {filename}: {e}")
            return None


# Utility functions for file operations
def get_session_file_manager(session_id: str) -> FileManager:
    """
    Get a FileManager instance for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        FileManager instance
    """
    return FileManager(session_id)


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """
    Clean up old session directories.

    Args:
        max_age_hours: Maximum age in hours before cleanup

    Returns:
        Number of sessions cleaned up
    """
    cleaned_count = 0
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp", "sessions")
        if not os.path.exists(sessions_dir):
            return 0

        current_time = datetime.now()
        max_age_seconds = max_age_hours * 3600

        for session_dir_name in os.listdir(sessions_dir):
            session_path = os.path.join(sessions_dir, session_dir_name)
            if os.path.isdir(session_path):
                # Check directory age
                dir_mtime = datetime.fromtimestamp(os.path.getmtime(session_path))
                age_seconds = (current_time - dir_mtime).total_seconds()

                if age_seconds > max_age_seconds:
                    shutil.rmtree(session_path)
                    cleaned_count += 1
                    logger.info(f"Cleaned up old session: {session_dir_name}")

    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")

    return cleaned_count


# Example usage and testing
if __name__ == "__main__":
    # Test the file manager
    fm = FileManager("test_session_456")

    # Save some test files
    fm.save_file("workflow_readme.md", "# Test Workflow\nThis is a test README.")
    fm.save_file("session1_generated.snowsql", "-- Generated SQL\nCREATE TABLE test_table (id INTEGER);")
    fm.save_file("test_data/sample.csv", "id,name\n1,test\n2,test2")

    print("Session stats:")
    print(json.dumps(fm.get_session_stats(), indent=2))

    print("\nFile list:")
    for file_info in fm.list_files():
        print(f"- {file_info['filename']} ({file_info['size']} bytes)")

    print("\nFile preview for workflow_readme.md:")
    print(fm.get_file_preview("workflow_readme.md"))

    # Create ZIP archive
    zip_path = fm.create_zip_archive()
    print(f"\nCreated ZIP archive: {zip_path}")

    # Cleanup
    # fm.cleanup_session()