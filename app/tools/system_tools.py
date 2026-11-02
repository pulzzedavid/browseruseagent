"""
System interaction tools for the Browser Use Agent
"""

import logging
import os
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemTools:
    """System interaction tools for file operations and system commands"""
    
    def __init__(self):
        self.is_initialized = False
        self.safe_directories = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
            str(Path.cwd()),
            "screenshots",
            "logs",
            "temp"
        ]
        
    async def initialize(self):
        """Initialize system tools"""
        try:
            # Create necessary directories
            for directory in ["screenshots", "logs", "temp"]:
                Path(directory).mkdir(exist_ok=True)
            
            self.is_initialized = True
            logger.info("System tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system tools: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure system tools are initialized"""
        if not self.is_initialized:
            raise RuntimeError("System tools not initialized")
    
    def _is_safe_path(self, path: str) -> bool:
        """Check if a path is safe to operate on"""
        try:
            path_obj = Path(path).resolve()
            
            # Check if path is within safe directories
            for safe_dir in self.safe_directories:
                safe_path = Path(safe_dir).resolve()
                if path_obj.is_relative_to(safe_path):
                    return True
            
            # Allow operations in current working directory
            if path_obj.is_relative_to(Path.cwd()):
                return True
                
            return False
            
        except Exception:
            return False
    
    async def file_operation(self, operation: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Perform file system operations"""
        self._ensure_initialized()
        
        try:
            if not self._is_safe_path(path):
                return {
                    "success": False,
                    "operation": operation,
                    "path": path,
                    "error": "Path is not safe to operate on"
                }
            
            start_time = datetime.now()
            
            if operation == "read":
                result = await self._read_file(path)
            elif operation == "write":
                if content is None:
                    return {
                        "success": False,
                        "operation": operation,
                        "path": path,
                        "error": "Content is required for write operations"
                    }
                result = await self._write_file(path, content)
            elif operation == "delete":
                result = await self._delete_file(path)
            elif operation == "list":
                result = await self._list_directory(path)
            else:
                return {
                    "success": False,
                    "operation": operation,
                    "path": path,
                    "error": f"Unsupported operation: {operation}"
                }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result.update({
                "operation": operation,
                "path": path,
                "execution_time_ms": execution_time
            })
            
            logger.info(f"File operation '{operation}' on '{path}' completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"File operation '{operation}' on '{path}' failed: {e}")
            return {
                "success": False,
                "operation": operation,
                "path": path,
                "error": str(e),
                "execution_time_ms": 0
            }
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file"""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File does not exist"
                }
            
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": "Path is not a file"
                }
            
            # Check file size (limit to 1MB for safety)
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:
                return {
                    "success": False,
                    "error": "File is too large (max 1MB)"
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "file_size": file_size,
                "file_type": file_path.suffix,
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file"""
        try:
            file_path = Path(path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "bytes_written": len(content.encode('utf-8')),
                "file_created": not file_path.exists() or file_path.stat().st_size == 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file"""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File does not exist"
                }
            
            if not file_path.is_file():
                return {
                    "success": False,
                    "error": "Path is not a file"
                }
            
            file_size = file_path.stat().st_size
            file_path.unlink()
            
            return {
                "success": True,
                "file_deleted": True,
                "deleted_size": file_size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents"""
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": "Directory does not exist"
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": "Path is not a directory"
                }
            
            items = []
            for item in dir_path.iterdir():
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_hidden": item.name.startswith('.')
                    })
                except Exception:
                    # Skip items we can't access
                    continue
            
            # Sort items: directories first, then files, both alphabetically
            items.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))
            
            return {
                "success": True,
                "items": items,
                "total_items": len(items),
                "path": str(dir_path.resolve())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def system_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a system command"""
        self._ensure_initialized()
        
        try:
            # Validate command for safety
            if not self._is_safe_command(command):
                return {
                    "success": False,
                    "command": command,
                    "error": "Command is not safe to execute"
                }
            
            start_time = datetime.now()
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                result = {
                    "success": True,
                    "command": command,
                    "return_code": process.returncode,
                    "stdout": stdout.decode('utf-8', errors='ignore'),
                    "stderr": stderr.decode('utf-8', errors='ignore'),
                    "execution_time_ms": execution_time
                }
                
                logger.info(f"System command '{command}' executed successfully")
                return result
                
            except asyncio.TimeoutError:
                process.terminate()
                return {
                    "success": False,
                    "command": command,
                    "error": f"Command timed out after {timeout} seconds",
                    "execution_time_ms": 0
                }
                
        except Exception as e:
            logger.error(f"System command '{command}' failed: {e}")
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "execution_time_ms": 0
            }
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe to execute"""
        # List of potentially dangerous commands
        dangerous_commands = [
            'rm -rf', 'sudo', 'chmod', 'chown', 'dd', 'format',
            'mkfs', 'fdisk', 'mount', 'umount', 'shutdown', 'reboot',
            'killall', 'pkill', 'kill', 'nohup', 'screen', 'tmux'
        ]
        
        command_lower = command.lower()
        
        # Check for dangerous commands
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return False
        
        # Check for shell redirections that could be dangerous
        dangerous_patterns = ['>', '>>', '<', '|', '&', ';', '&&', '||']
        for pattern in dangerous_patterns:
            if pattern in command:
                return False
        
        # Only allow simple commands
        allowed_commands = [
            'ls', 'cat', 'head', 'tail', 'grep', 'find', 'pwd',
            'echo', 'date', 'whoami', 'hostname', 'uname', 'ps',
            'df', 'du', 'free', 'top', 'htop', 'tree'
        ]
        
        command_parts = command.strip().split()
        if not command_parts:
            return False
        
        base_command = command_parts[0]
        return base_command in allowed_commands
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            info = {
                "platform": os.name,
                "current_directory": str(Path.cwd()),
                "home_directory": str(Path.home()),
                "available_disk_space": await self._get_disk_space(),
                "safe_directories": self.safe_directories
            }
            
            return {
                "success": True,
                "system_info": info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_disk_space(self) -> Dict[str, Any]:
        """Get available disk space for current directory"""
        try:
            current_path = Path.cwd()
            statvfs = os.statvfs(current_path)
            
            # Calculate available space
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            
            return {
                "free_bytes": free_bytes,
                "total_bytes": total_bytes,
                "free_gb": round(free_bytes / (1024**3), 2),
                "total_gb": round(total_bytes / (1024**3), 2),
                "usage_percent": round((1 - free_bytes / total_bytes) * 100, 2)
            }
            
        except Exception:
            return {"error": "Unable to get disk space information"}
