import os
import sys

# Define default ignore lists at the module level
DEFAULT_IGNORE_DIRS = ['.git', '__pycache__', 'venv', 'node_modules', '.idea', '.vscode']
DEFAULT_IGNORE_FILES = ['.DS_Store', 'Thumbs.db', '.gitignore', 'package-lock.json', 'yarn.lock']

# Global set to store absolute paths of items that must be ignored (script itself, output folder, etc.)
_IGNORE_TARGETS = set()

def _add_to_ignore_targets(path):
    """Adds an absolute path to the global ignore targets set."""
    _IGNORE_TARGETS.add(os.path.abspath(path))

def collect_eligible_files(project_path, ignore_dirs, ignore_files, file_extensions):
    """
    Collects a sorted list of relative paths for all eligible files.
    Files and directories in _IGNORE_TARGETS are always excluded.
    """
    eligible_files = []
    
    for root, dirs, files in os.walk(project_path):
        current_abs_root = os.path.abspath(root)

        # Filter out user-specified ignore directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # Also filter out directories that are part of _IGNORE_TARGETS
        # If the current root itself is an ignored target (e.g., the output folder), skip it
        if current_abs_root in _IGNORE_TARGETS:
            dirs[:] = []  # Don't recurse into this directory
            files[:] = [] # Don't list files from this directory
            continue
        
        # Remove any subdirectories from `dirs` that are explicitly ignored targets
        dirs_to_remove = []
        for d in dirs:
            if os.path.join(current_abs_root, d) in _IGNORE_TARGETS:
                dirs_to_remove.append(d)
        dirs[:] = [d for d in dirs if d not in dirs_to_remove]


        for file in files:
            file_abs_path = os.path.abspath(os.path.join(root, file))
            
            # Check if file is in ignore_files list (by filename)
            # or if it's in _IGNORE_TARGETS set (by absolute path, for script itself and output files)
            if file in ignore_files or file_abs_path in _IGNORE_TARGETS:
                continue

            # Check if file extension is required
            if file_extensions and not any(file.endswith(ext) for ext in file_extensions):
                continue

            eligible_files.append(os.path.relpath(file_abs_path, project_path))
            
    eligible_files.sort()
    return eligible_files


def get_project_structure_string(project_path, eligible_files, ignore_dirs, ignore_files):
    """Generates the formatted project structure string."""
    structure_lines = ["我的项目结构如下：\n"]

    # Use a set for quick lookup of eligible files' relative paths
    eligible_files_set = set(eligible_files)

    for root, dirs, files in os.walk(project_path):
        current_abs_root = os.path.abspath(root)

        # Filter out user-specified ignore directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        # Ensure we don't process directories that are explicitly ignored targets
        if current_abs_root in _IGNORE_TARGETS:
            dirs[:] = []
            files[:] = []
            continue
        
        # Remove any subdirectories from `dirs` that are explicitly ignored targets
        dirs_to_remove = []
        for d in dirs:
            if os.path.join(current_abs_root, d) in _IGNORE_TARGETS:
                dirs_to_remove.append(d)
        dirs[:] = [d for d in dirs if d not in dirs_to_remove]


        level = current_abs_root.replace(os.path.abspath(project_path), '').count(os.sep)
        indent = '    ' * level

        # Avoid printing folder icon for the project root itself
        if current_abs_root != os.path.abspath(project_path):
            structure_lines.append(f"{indent}📁 {os.path.basename(root)}/\n")

        # Sort files within the current directory for consistent output
        for file in sorted(files):
            file_abs_path = os.path.abspath(os.path.join(root, file))
            relative_file_path = os.path.relpath(file_abs_path, project_path)

            # Only include files that are both eligible and not an ignored target
            if relative_file_path in eligible_files_set and \
               file_abs_path not in _IGNORE_TARGETS:
                
                # Files directly in the root don't need extra indentation for the first level
                file_indent = indent if current_abs_root != os.path.abspath(project_path) else ''
                structure_lines.append(f"{file_indent}    📄 {file}\n")
    
    return "".join(structure_lines)


def generate_segmented_prompts_content(project_path, output_folder_path, 
                                     ignore_dirs_input=None, ignore_files_input=None, file_extensions=None):
    """
    Generates a list of prompt segments.
    
    Args:
        project_path (str): The root directory of the project.
        output_folder_path (str): The absolute path to the folder where segments will be saved.
        ignore_dirs_input (list, optional): List of directory names to ignore.
        ignore_files_input (list, optional): List of file names to ignore.
        file_extensions (list, optional): List of file extensions to include.
    
    Returns:
        list: A list of strings, where each string is a prompt segment's content.
    """
    # Use provided ignore lists or default ones
    current_ignore_dirs = ignore_dirs_input if ignore_dirs_input is not None else DEFAULT_IGNORE_DIRS
    current_ignore_files = ignore_files_input if ignore_files_input is not None else DEFAULT_IGNORE_FILES

    # Step 1: Collect all eligible files
    eligible_files = collect_eligible_files(
        project_path, current_ignore_dirs, current_ignore_files, file_extensions
    )

    all_segments_content = []

    # Step 2: Generate project structure string
    project_structure_str = get_project_structure_string(project_path, eligible_files, current_ignore_dirs, current_ignore_files)

    # Step 3: Create the first combined segment: Intro + Project Structure + First File Content
    first_segment_parts = []
    
    first_segment_parts.append("我现在需要你作为助手，帮我看一下我的程序，我会依次发送给你文件结构和各个文件的源代码。\n")
    first_segment_parts.append(project_structure_str)

    if eligible_files:
        first_file_rel_path = eligible_files[0]
        first_file_abs_path = os.path.join(project_path, first_file_rel_path)
        try:
            with open(first_file_abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            first_segment_parts.append(f"\n--- 文件: {first_file_rel_path} ---\n```\n{content}\n```\n")
        except Exception as e:
            first_segment_parts.append(f"\n--- 文件: {first_file_rel_path} (无法读取或编码问题) ---\n错误: {e}\n")
    
    all_segments_content.append("".join(first_segment_parts))

    # Step 4: Create segments for the remaining files (excluding the last one)
    for i in range(1, len(eligible_files) - 1): # Iterate up to the second to last file
        file_rel_path = eligible_files[i]
        file_abs_path = os.path.join(project_path, file_rel_path)
        file_segment_parts = []
        try:
            with open(file_abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            file_segment_parts.append(f"--- 文件: {file_rel_path} ---\n```\n{content}\n```\n")
        except Exception as e:
            file_segment_parts.append(f"\n--- 文件: {file_rel_path} (无法读取或编码问题) ---\n错误: {e}\n")
        all_segments_content.append("".join(file_segment_parts))

    # Step 5: Create the final combined segment: Last File Content + User Question
    final_segment_parts = []
    if len(eligible_files) > 1: # If there's more than just the first file
        last_file_rel_path = eligible_files[-1] # Get the very last eligible file
        last_file_abs_path = os.path.join(project_path, last_file_rel_path)
        try:
            with open(last_file_abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            final_segment_parts.append(f"--- 文件: {last_file_rel_path} ---\n```\n{content}\n```\n")
        except Exception as e:
            final_segment_parts.append(f"\n--- 文件: {last_file_rel_path} (无法读取或编码问题) ---\n错误: {e}\n")

    # Add the user question placeholder to the final segment
    final_segment_parts.append("\n我的问题是：[请在此处详细描述您的问题，例如：请帮我优化'main.py'中的数据处理逻辑，或者请帮我找出并修复'utils.js'中的一个bug。]\n")
    final_segment_parts.append("请您基于我提供的现有代码，帮助我解决上述问题。")
    all_segments_content.append("".join(final_segment_parts))


    return all_segments_content

if __name__ == "__main__":
    # Get the project root directory (where this script is located)
    project_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Define the subfolder where segment TXT files will be saved
    output_folder_name = "ai_prompt_segments"
    output_folder_path = os.path.join(project_directory, output_folder_name)

    # Add the script itself and the output folder to the global ignore targets
    _add_to_ignore_targets(os.path.abspath(sys.argv[0])) # The script itself
    _add_to_ignore_targets(output_folder_path) # The folder containing the segments

    print(f"Analyzing project directory: {project_directory}")

    # Generate the raw content segments
    raw_segments = generate_segmented_prompts_content(
        project_directory,
        output_folder_path,
        # Customize ignore directories, files, or file extensions here if needed
        # ignore_dirs_input=['.git', '__pycache__'], 
        # ignore_files_input=['.gitignore', 'README.md'],
        # file_extensions=['.py', '.js'] 
    )

    total_segments = len(raw_segments)

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder_path, exist_ok=True)

    # Write each segment to a separate file within the output folder
    try:
        for i, segment_content in enumerate(raw_segments):
            segment_number = i + 1
            segment_filename = f"prompt_segment_{segment_number}_of_{total_segments}.txt"
            segment_filepath = os.path.join(output_folder_path, segment_filename)
            
            # Add the [X/N] tag to the beginning of each segment content
            formatted_segment = f"[{segment_number}/{total_segments}] {segment_content}"

            with open(segment_filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_segment)
        
        print(f"\n--- AI Prompt segments successfully generated and saved to: {output_folder_path} ---")
        print(f"Please open the files in this folder and copy-paste them one by one to your AI.")
        print("Remember to replace the placeholder for your question in the last segment.")

    except Exception as e:
        print(f"\n--- Error writing segments to files: {e} ---")
        print("\nDisplaying generated prompt content (not saved to files):")
        # Fallback to printing if file writing fails
        for i, segment_content in enumerate(raw_segments):
            segment_number = i + 1
            print(f"[{segment_number}/{total_segments}] {segment_content}")