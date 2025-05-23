import hou
import os
import shutil
import re
from collections import defaultdict

def asset_packer():
    hip_path = hou.hipFile.path()
    if not hip_path:
        hou.ui.displayMessage("Please save the .hip file before running this tool.", severity=hou.severityType.Error)
        return
    hip_dir = os.path.dirname(hip_path)
    output_folder_name = "_assets"
    keep_structure = False
    overwrite_existing = True
    file_exts = {
        "Geometry": [".abc", ".obj", ".fbx", ".bgeo", ".vdb"],
        "Textures": [".jpg", ".jpeg", ".png", ".exr", ".tif", ".tiff", ".hdr"],
        "Video": [".mov", ".mp4", ".avi"],
        "Misc": [".csv", ".json", ".txt"]
    }
    all_extensions = []
    for category, exts in file_exts.items():
        all_extensions.extend(exts)
    labels = ["Output Folder", "Keep folder structure", "Overwrite existing"]
    defaults = [output_folder_name, "0", "1"]
    input_result = hou.ui.readMultiInput(
        "Asset Packer Configuration",
        labels,
        initial_contents=defaults,
        buttons=("Continue", "Cancel"),
        title="Asset Packer"
    )
    if input_result[0] == 1:
        return
    output_folder_name = input_result[1][0]
    keep_structure = input_result[1][1] == "1"
    overwrite_existing = input_result[1][2] == "1"
    file_type_choices = ["Geometry", "Textures", "Video", "Misc"]
    checked = [True, True, True, True]
    file_types_result = hou.ui.selectFromList(
        file_type_choices,
        default_choices=range(len(file_type_choices)),
        message="Select file types to collect:",
        title="File Types",
        num_visible_rows=len(file_type_choices),
        clear_on_cancel=True,
        column_header="File Types"
    )
    if not file_types_result:
        return
    selected_extensions = []
    for index in file_types_result:
        category = file_type_choices[index]
        selected_extensions.extend(file_exts[category])
    assets_folder = os.path.join(hip_dir, output_folder_name)
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)
    all_nodes = hou.node("/").allSubChildren()
    total_nodes = len(all_nodes)
    found_files = set()
    update_list = []
    hou.ui.displayMessage("Scanning scene... This may take a few minutes for large scenes.", severity=hou.severityType.ImportantMessage, buttons=("Please wait",))
    node_count = 0
    for node in all_nodes:
        node_count += 1
        if node_count % 100 == 0:
            print(f"Scanned {node_count}/{total_nodes} nodes...")
        for parm in node.parms():
            try:
                value = parm.eval()
                if not isinstance(value, str):
                    continue
                file_path = os.path.normpath(os.path.expandvars(value))
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path.lower())[1]
                    if ext in selected_extensions:
                        abs_path = os.path.abspath(file_path)
                        if keep_structure:
                            rel_from_hip = os.path.relpath(abs_path, start=hip_dir)
                            new_path = os.path.join(assets_folder, rel_from_hip)
                            new_dir = os.path.dirname(new_path)
                            if not os.path.exists(new_dir):
                                os.makedirs(new_dir)
                        else:
                            file_name = os.path.basename(abs_path)
                            new_path = os.path.join(assets_folder, file_name)
                        found_files.add((abs_path, new_path))
                        update_list.append((parm, new_path))
            except:
                continue
    if not found_files:
        hou.ui.displayMessage("No files found to copy.", severity=hou.severityType.Warning)
        return
    file_list = "\n".join([f"{os.path.basename(src)}" for src, _ in list(found_files)[:20]])
    if len(found_files) > 20:
        file_count = len(found_files)
        file_list += f"\n...\n(and {file_count - 20} more files)"
    msg = f"Found {len(found_files)} files.\n\nFile list:\n{file_list}"
    confirm = hou.ui.displayMessage(msg, buttons=("Copy & Update", "Copy Only", "Cancel"), default_choice=0, close_choice=2)
    if confirm == 2:
        return
    copied_count = 0
    failed_copy = []
    hou.ui.displayMessage(f"Copying {len(found_files)} files to {output_folder_name}... This may take a while for many files.", severity=hou.severityType.ImportantMessage, buttons=("Please wait",))
    for i, (src, dst) in enumerate(found_files):
        if i % 10 == 0:
            print(f"Copying: {i+1}/{len(found_files)} files...")
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            try:
                os.makedirs(dst_dir)
            except:
                failed_copy.append(src)
                continue
        try:
            if not os.path.exists(dst) or overwrite_existing:
                shutil.copy2(src, dst)
                copied_count += 1
        except:
            failed_copy.append(src)
    if confirm == 0:
        updated_count = 0
        hou.ui.displayMessage(f"Updating {len(update_list)} paths...", severity=hou.severityType.ImportantMessage, buttons=("Please wait",))
        for i, (parm, new_path) in enumerate(update_list):
            if i % 50 == 0:
                print(f"Updating: {i+1}/{len(update_list)} paths...")
            try:
                rel_path = os.path.relpath(new_path, hip_dir)
                rel_path_formatted = rel_path.replace("\\", "/")
                parm_value = "$HIP/" + rel_path_formatted
                parm.set(parm_value)
                updated_count += 1
            except:
                continue
    stats = f"Copied: {copied_count}/{len(found_files)} files\n"
    if failed_copy:
        stats += f"Failed: {len(failed_copy)} files\n"
    if confirm == 0:
        stats += f"Updated: {updated_count}/{len(update_list)} paths to '$HIP/{output_folder_name}/...'"
    hou.ui.displayMessage(f"Done!\n\n{stats}", severity=hou.severityType.ImportantMessage)
    hou.ui.displayMessage("Remember to save the .hip file to keep the updated paths!", severity=hou.severityType.Message)

asset_packer()
