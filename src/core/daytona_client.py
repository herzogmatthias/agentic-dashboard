from pathlib import Path
from threading import Lock
from typing import Any, List, Optional, Union

from daytona import Daytona, DaytonaConfig, CreateSandboxFromSnapshotParams, Sandbox

from .config import ARTIFACTS_DIR, DAYTONA_SNAPSHOT_NAME, DAYTONA_TARGET, LOCAL_CSV_PATH, SANDBOX_CSV_PATH


class DaytonaSandboxSingleton:
    """
    Thread-safe singleton for managing a single persistent Daytona sandbox instance.
    
    This ensures that only one sandbox is created and reused across all tool calls,
    preventing resource leaks and duplicate sandbox creation.
    """
    
    _instance: Optional["DaytonaSandboxSingleton"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "DaytonaSandboxSingleton":
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        # Only initialize once
        if self._initialized:
            return
            
        self._daytona: Optional[Daytona] = None
        self._sandbox: Optional[Sandbox] = None
        self._is_stopped = False
        self._initialized = True
    
    def _get_daytona_client(self) -> Daytona:
        """Get or create the Daytona client."""
        if self._daytona is None:
            cfg = DaytonaConfig(target=DAYTONA_TARGET)
            self._daytona = Daytona(cfg)
        return self._daytona
    
    def get_sandbox(self) -> Sandbox:
        """
        Get the singleton sandbox instance, creating it if necessary.
        
        Returns:
            The active Daytona sandbox instance.
            
        Raises:
            RuntimeError: If sandbox was previously stopped and cannot be reused.
        """
        if self._sandbox is not None:
            return self._sandbox
        
        with self._lock:
            # Double-check after acquiring lock
            if self._sandbox is not None:
                return self._sandbox
            # We might be starting a new lifecycle after a previous stop.
            self._is_stopped = False
            daytona = self._get_daytona_client()
            params = CreateSandboxFromSnapshotParams(
                snapshot=DAYTONA_SNAPSHOT_NAME,
                auto_stop_interval=60,
                auto_archive_interval=0,
                auto_delete_interval=0,
                language="python",
            )
            self._sandbox = daytona.create(params)
            
            # Optional: upload local CSV into the sandbox once for quick testing
            self._sandbox.fs.create_folder("workspace/artifacts/data_analysis", "755")
            self._sandbox.fs.create_folder("workspace/original", "755")
            self._sandbox.fs.create_folder("workspace/cleaned", "755")
            if LOCAL_CSV_PATH.exists():
                csv_bytes = LOCAL_CSV_PATH.read_bytes()
                self._sandbox.fs.upload_file(csv_bytes, SANDBOX_CSV_PATH)
            

            return self._sandbox
    
    def stop_and_archive(self, copy_artifacts: bool = True) -> None:
        if self._sandbox is None or self._is_stopped:
            return

        with self._lock:
            if self._sandbox is None or self._is_stopped:
                return

            try:
                if copy_artifacts:
                    self.copy_workspace_to_artifacts()
            except Exception as e:
                print(f"Warning: Failed to copy artifacts: {e}")

            try:
                self._sandbox.stop(timeout=30)
            except Exception as e:
                print(f"Warning: Failed to stop sandbox: {e}")

            try:
                self._sandbox.archive()
            except Exception as e:
                print(f"Warning: Failed to archive sandbox: {e}")

            self._is_stopped = True
            self._sandbox = None
    
    def copy_workspace_to_artifacts(
        self,
        local_artifacts_dir: Path = ARTIFACTS_DIR,
        remote_root: str = "workspace",
    ) -> List[str]:
        """
        Recursively copy all files from a Daytona sandbox directory (default: workspace)
        into a local artifacts directory, preserving the directory structure.

        Daytona's list_files() returns FileInfo objects (name, is_dir, size_bytes, mod_time)
        so we must manually build full paths and recursively traverse directories.
        """
        sandbox = self.get_sandbox()
        local_artifacts_dir.mkdir(parents=True, exist_ok=True)

        copied: List[str] = []

        def walk(remote_dir: str, local_dir: Path):
            """Recursive DFS copying all files from remote_dir → local_dir."""
            entries = sandbox.fs.list_files(remote_dir)

            for entry in entries:
                remote_path = f"{remote_dir}/{entry.name}"
                local_path = local_dir / entry.name

                if entry.is_dir:
                    # Create local directory and recurse
                    local_path.mkdir(parents=True, exist_ok=True)
                    walk(remote_path, local_path)
                else:
                    # Download file bytes and write locally
                    content = sandbox.fs.download_file(remote_path)
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(content)
                    copied.append(str(local_path))

        # Start recursion from remote_root
        walk(remote_root, local_artifacts_dir)

        return copied
    
    from pathlib import Path

    
    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance. Use with caution - this will allow
        creation of a new sandbox instance.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.stop_and_archive(copy_artifacts=False)
            cls._instance = None

