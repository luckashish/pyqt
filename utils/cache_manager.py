"""
Cache Manager Utility
Handles clearing of application cache and compiled python files.
"""
import os
import shutil
from utils.logger import logger

def clear_cache(root_dir="."):
    """
    Recursively deletes __pycache__ directories and .pyc files.
    Also clears the application 'cache' directory if it exists.
    
    Args:
        root_dir (str): Root directory to start searching from.
        
    Returns:
        int: Number of files/directories deleted.
    """
    deleted_count = 0
    
    # 1. Clear __pycache__ and .pyc files
    for root, dirs, files in os.walk(root_dir):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            cache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                logger.info(f"Deleted cache directory: {cache_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {cache_path}: {e}")
        
        # Remove standalone .pyc files (if any)
        for file in files:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted compiled file: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
                    
    # 2. Clear application cache directory
    app_cache_dir = os.path.join(root_dir, "cache")
    if os.path.exists(app_cache_dir):
        try:
            # Delete all contents but keep the directory
            for item in os.listdir(app_cache_dir):
                item_path = os.path.join(app_cache_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            logger.info(f"Cleared application cache directory: {app_cache_dir}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to clear app cache {app_cache_dir}: {e}")
            
    return deleted_count
