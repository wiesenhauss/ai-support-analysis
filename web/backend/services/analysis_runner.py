"""
Analysis Job Runner Service.
Manages background analysis jobs with progress tracking.
"""

import sys
import os
import asyncio
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.schemas.analysis import AnalysisStatus, AnalysisOptions, AnalysisJobStatus


class AnalysisJobManager:
    """
    Manages background analysis jobs.
    
    Runs the main-analysis-process.py script and tracks progress
    by parsing its output.
    """
    
    def __init__(self, max_workers: int = 2):
        self.jobs: Dict[str, AnalysisJobStatus] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = asyncio.Lock()
    
    async def start_analysis(
        self,
        job_id: str,
        file_path: str,
        options: AnalysisOptions,
        api_key: str
    ) -> AnalysisJobStatus:
        """
        Start a new analysis job.
        
        Args:
            job_id: Unique identifier for the job
            file_path: Path to the CSV file to analyze
            options: Analysis options
            api_key: OpenAI API key
            
        Returns:
            Initial job status
        """
        async with self._lock:
            # Create job status
            status = AnalysisJobStatus(
                job_id=job_id,
                status=AnalysisStatus.PENDING,
                progress=0.0,
                current_step="Initializing",
                started_at=datetime.utcnow(),
                logs=[]
            )
            self.jobs[job_id] = status
        
        # Run analysis in thread pool
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            self.executor,
            self._run_analysis_sync,
            job_id, file_path, options, api_key
        )
        
        return status
    
    def _run_analysis_sync(
        self,
        job_id: str,
        file_path: str,
        options: AnalysisOptions,
        api_key: str
    ):
        """Synchronous analysis runner (runs in thread pool)."""
        try:
            # Update status to running
            self.jobs[job_id].status = AnalysisStatus.RUNNING
            self.jobs[job_id].current_step = "Starting analysis"
            self._add_log(job_id, "Analysis started")
            
            # Build command
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "main-analysis-process.py"),
                f"-file={file_path}"
            ]
            
            if options.limit:
                cmd.append(f"-limit={options.limit}")
            
            if options.threads:
                cmd.append(f"--threads={options.threads}")
            
            # Set environment with API key
            env = os.environ.copy()
            env["OPENAI_API_KEY"] = api_key
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=str(PROJECT_ROOT)
            )
            self.processes[job_id] = process
            
            # Read output and parse progress
            total_rows = None
            processed = 0
            
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                self._add_log(job_id, line)
                
                # Parse progress from output
                # Example: "Processing row 50/1000"
                progress_match = re.search(r'(\d+)/(\d+)', line)
                if progress_match:
                    processed = int(progress_match.group(1))
                    total_rows = int(progress_match.group(2))
                    
                    self.jobs[job_id].processed_rows = processed
                    self.jobs[job_id].total_rows = total_rows
                    self.jobs[job_id].progress = (processed / total_rows) * 100 if total_rows > 0 else 0
                
                # Parse step changes
                if "cleanup" in line.lower():
                    self.jobs[job_id].current_step = "Data cleanup"
                elif "analyzing" in line.lower() or "processing" in line.lower():
                    self.jobs[job_id].current_step = "Analyzing tickets"
                elif "saving" in line.lower():
                    self.jobs[job_id].current_step = "Saving results"
                elif "complete" in line.lower():
                    self.jobs[job_id].current_step = "Complete"
                
                # Check for output file
                if "output" in line.lower() and ".csv" in line.lower():
                    # Try to extract output file path
                    csv_match = re.search(r'[^\s]+\.csv', line)
                    if csv_match:
                        self.jobs[job_id].output_file = csv_match.group(0)
            
            # Wait for completion
            process.wait()
            
            # Update final status
            if process.returncode == 0:
                self.jobs[job_id].status = AnalysisStatus.COMPLETED
                self.jobs[job_id].progress = 100.0
                self.jobs[job_id].current_step = "Complete"
                self._add_log(job_id, "Analysis completed successfully")
            else:
                self.jobs[job_id].status = AnalysisStatus.FAILED
                self.jobs[job_id].error_message = f"Process exited with code {process.returncode}"
                self._add_log(job_id, f"Analysis failed with exit code {process.returncode}")
            
            self.jobs[job_id].completed_at = datetime.utcnow()
            
        except Exception as e:
            self.jobs[job_id].status = AnalysisStatus.FAILED
            self.jobs[job_id].error_message = str(e)
            self.jobs[job_id].completed_at = datetime.utcnow()
            self._add_log(job_id, f"Error: {str(e)}")
        finally:
            # Clean up process reference
            if job_id in self.processes:
                del self.processes[job_id]
    
    def _add_log(self, job_id: str, message: str):
        """Add a log message to the job."""
        if job_id in self.jobs:
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            self.jobs[job_id].logs.append(f"[{timestamp}] {message}")
            # Keep only last 1000 log lines
            if len(self.jobs[job_id].logs) > 1000:
                self.jobs[job_id].logs = self.jobs[job_id].logs[-1000:]
    
    def get_job_status(self, job_id: str) -> Optional[AnalysisJobStatus]:
        """Get the status of a job."""
        return self.jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        async with self._lock:
            if job_id not in self.jobs:
                return False
            
            # Kill process if running
            if job_id in self.processes:
                process = self.processes[job_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                del self.processes[job_id]
            
            # Update status
            self.jobs[job_id].status = AnalysisStatus.CANCELLED
            self.jobs[job_id].completed_at = datetime.utcnow()
            self._add_log(job_id, "Job cancelled by user")
            
            return True
    
    def list_jobs(self) -> List[AnalysisJobStatus]:
        """List all jobs."""
        return list(self.jobs.values())
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        cutoff = datetime.utcnow()
        to_remove = []
        
        for job_id, status in self.jobs.items():
            if status.completed_at:
                age = (cutoff - status.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]


# Singleton instance
_job_manager_instance: Optional[AnalysisJobManager] = None


def get_job_manager() -> AnalysisJobManager:
    """Get the singleton job manager instance."""
    global _job_manager_instance
    
    if _job_manager_instance is None:
        _job_manager_instance = AnalysisJobManager()
    
    return _job_manager_instance
