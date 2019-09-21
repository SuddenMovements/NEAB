import os
from shutil import rmtree


def safe_create_folder(path):
    """
    Safely Creating Nested Folders

    Args:
        path (str): folder path
    """

    def safe_create_single_folder(name):
        if not os.path.exists(name):
            os.mkdir(name)

    all_paths = path.split('/')
    current_path = ''
    for p in all_paths:
        current_path += p + '/'
        safe_create_single_folder(current_path)

def safe_delete_folder(path):
    """
    Recursively Deleting Folder (Start From Root Path)

    Args:
        path (str): root path for deletion.
    """

    if os.path.exists(path):
        rmtree(path)
