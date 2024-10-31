import os
import pathlib
from typing import Dict, Tuple
import logging

class DirectoryManager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_directory_structure(self, input_path: str, base_output_path: str) -> Dict[str, str]:
        """Creates appropriate directory structure based on input type"""
        try:
            base_output_path = os.path.abspath(base_output_path)
            
            # Get the directory name from input path
            if os.path.isfile(input_path):
                dir_name = os.path.splitext(os.path.basename(input_path))[0]
            else:
                dir_name = os.path.basename(input_path)
            
            # Create main output directory
            main_dir = os.path.join(base_output_path, dir_name)
            os.makedirs(main_dir, exist_ok=True)
            
            # Create and return paths for subdirectories
            subdirs = {
                'frames': os.path.join(main_dir, 'frames'),
                'audio': os.path.join(main_dir, 'audio'),
                'logs': os.path.join(main_dir, 'logs')
            }
            
            # Create all subdirectories
            for dir_path in subdirs.values():
                os.makedirs(dir_path, exist_ok=True)
                self.logger.info(f"Created directory: {dir_path}")
                
            return subdirs
            
        except Exception as e:
            self.logger.error(f"Error creating directory structure: {str(e)}")
            raise

    def get_output_paths(self, input_path: str, output_base_path: str) -> Dict[str, str]:
        """Returns paths for frames, audio, and logs directories"""
        return self.create_directory_structure(input_path, output_base_path)
