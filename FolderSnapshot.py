# -*- coding: utf-8 -*>
import os
import re
import sys
import lzma
import base64
import platform
import tempfile
import subprocess
import json
import io
from pathlib import Path

# ==============================================================================
# Core Logic (Streaming Snapshot and Restore)
# ==============================================================================

def _create_snapshot_stream(input_path, show_progress_callback=None):
    """
    核心创建逻辑：从输入路径生成快照流 (generator)。
    这种方式可以避免将所有内容加载到内存中。
    """
    input_path = Path(input_path).resolve()
    
    # 收集所有文件和目录
    paths_to_process = []
    if input_path.is_file():
        paths_to_process.append(input_path)
        base_path = input_path.parent
    else:
        base_path = input_path
        for root, dirs, files in os.walk(input_path):
            root_path = Path(root)
            # 先处理目录，再处理文件
            for d in sorted(dirs):
                paths_to_process.append(root_path / d)
            for f in sorted(files):
                paths_to_process.append(root_path / f)

    total_paths = len(paths_to_process)
    
    for i, p in enumerate(paths_to_process):
        relative_path = p.relative_to(base_path).as_posix()
        
        yield b"--- entry ---\n"
        
        if p.is_dir():
            meta = {"path": relative_path, "type": "dir"}
            yield json.dumps(meta).encode('utf-8') + b'\n'
            
        elif p.is_file():
            try:
                content_bytes = p.read_bytes()
                # 尝试解码以判断是否为文本。如果失败，则视为二进制。
                content_bytes.decode('utf-8')
                meta = {"path": relative_path, "type": "file", "encoding": "utf-8", "size": len(content_bytes)}
                yield json.dumps(meta).encode('utf-8') + b'\n'
                yield content_bytes
            except UnicodeDecodeError:
                # 视为二进制文件，使用base64编码
                content_bytes = p.read_bytes()
                encoded_content = base64.b64encode(content_bytes)
                meta = {"path": relative_path, "type": "file", "encoding": "base64", "size": len(encoded_content)}
                yield json.dumps(meta).encode('utf-8') + b'\n'
                yield encoded_content
        
        if show_progress_callback:
            show_progress_callback(i + 1, total_paths)

def _restore_from_snapshot_stream(input_stream, output_folder):
    """
    核心恢复逻辑：从流中读取快照内容并恢复文件结构 (真正流式处理，非常健壮)。
    """
    output_path = Path(output_folder).resolve()
    output_path.mkdir(exist_ok=True)
    
    processed_entries = 0
    print("开始恢复，由于采用流式处理，无法预先计算总数。")

    while True:
        # 1. 寻找条目标记
        line = input_stream.readline()
        if not line:
            break # 正常到达文件末尾

        if line.strip() != b"--- entry ---":
            continue

        # 2. 读取元数据行
        meta_line = input_stream.readline()
        if not meta_line:
            print_colored("\n警告: 快照文件在条目标记后意外结束。", 'yellow')
            break

        try:
            # 3. 解析元数据
            meta = json.loads(meta_line.decode('utf-8'))
            relative_path = meta.get('path')
            entry_type = meta.get('type')

            if not relative_path or not entry_type:
                raise KeyError("元数据缺少 'path' 或 'type' 字段")

            full_path = output_path / relative_path
            
            if entry_type == 'dir':
                full_path.mkdir(parents=True, exist_ok=True)
            elif entry_type == 'file':
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                size = meta.get('size', 0)
                encoding = meta.get('encoding')

                # 4. 根据大小读取文件内容
                content = input_stream.read(size)
                if len(content) != size:
                    print_colored(f"\n警告: 快照文件不完整，文件 {relative_path} 可能已损坏。", 'yellow')
                    continue

                # 5. 解码并写入文件
                if encoding == 'base64':
                    file_content = base64.b64decode(content)
                else:
                    file_content = content
                
                full_path.write_bytes(file_content)
            
            processed_entries += 1
            show_progress_indeterminate(processed_entries, "恢复进度:")

        except (json.JSONDecodeError, KeyError, UnicodeDecodeError, base64.binascii.Error) as e:
            print_colored(f"\n警告: 格式错误的条目，已跳过。错误: {e}", 'yellow')
            continue
        except Exception as e:
            print_colored(f"\n处理条目时发生未知错误: {e}", 'red')
            continue

    print() # Newline after progress indicator
    print_colored(f"恢复完成! 共处理 {processed_entries} 个条目。", 'green')
    return True

# ==============================================================================
# High-Level Functions (File I/O and Editor-based Text)
# ==============================================================================

def gather_files_to_txt(input_path, show_progress_callback=None):
    path = Path(input_path)
    if path.is_file():
        base_name = path.name
        initial_output_file = path.parent / f"snapshot_{base_name}.txt"
    else:
        folder_name = path.name
        initial_output_file = path.parent / f"snapshot_{folder_name}.txt"
    
    output_file = get_unique_filepath(initial_output_file)
    
    with open(output_file, 'wb') as f:
        for chunk in _create_snapshot_stream(input_path, show_progress_callback):
            f.write(chunk)
            
    return output_file

METADATA_SEPARATOR = b"---SNAPSHOT_METADATA_END---\n"

def gather_files_to_txt_compressed(input_path, show_progress_callback=None):
    path = Path(input_path)
    if path.is_file():
        base_name = path.name
        initial_output_file = path.parent / f"compressed_snapshot_{base_name}.txt"
    else:
        folder_name = path.name
        initial_output_file = path.parent / f"compressed_snapshot_{folder_name}.txt"
        
    output_file = get_unique_filepath(initial_output_file)

    with io.BytesIO() as buffer:
        for chunk in _create_snapshot_stream(input_path, show_progress_callback):
            buffer.write(chunk)
        buffer.seek(0)
        raw_snapshot_bytes = buffer.read()

    compressed_bytes = compress_data(raw_snapshot_bytes)

    metadata = {
        "version": "1.0",
        "compression_method": "lzma", # Always LZMA in this version
        "original_size": len(raw_snapshot_bytes) 
    }
    metadata_json = json.dumps(metadata).encode('utf-8')

    with open(output_file, 'wb') as f:
        f.write(metadata_json)
        f.write(b'\n')
        f.write(METADATA_SEPARATOR)
        f.write(compressed_bytes)
        
    return output_file

def restore_files_from_txt(txt_path, output_folder):
    if not validate_path(txt_path): return
    with open(txt_path, 'rb') as f:
        _restore_from_snapshot_stream(f, output_folder)

def restore_files_from_compressed_txt(txt_path, output_folder):
    if not validate_path(txt_path): return
    print("正在读取并解压缩文件...")
    try:
        with open(txt_path, 'rb') as f:
            # Read metadata
            metadata_bytes = b""
            while True:
                line = f.readline()
                if line.strip() == METADATA_SEPARATOR.strip(): # Compare stripped versions
                    break
                if not line: # EOF before separator
                    raise ValueError("Invalid snapshot file format: Metadata separator not found.")
                metadata_bytes += line
            
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            # In this version, we only support lzma, but we still read the method for compatibility
            compression_method = metadata.get("compression_method", "lzma") 

            compressed_content = f.read() # Read the rest of the file

        decompressed_bytes = decompress_data(compressed_content)
        with io.BytesIO(decompressed_bytes) as stream:
            _restore_from_snapshot_stream(stream, output_folder)
    except (lzma.LZMAError, ValueError, json.JSONDecodeError, base64.binascii.Error) as e:
        print_colored(f"解压缩失败或内容格式无效: {str(e)}", 'red')
    except Exception as e:
        print_colored(f"恢复过程中发生未知错误: {e}", 'red')
        import traceback
        traceback.print_exc()

def restore_from_editor_text():
    editor_content_str = get_text_from_editor()
    if not editor_content_str:
        print_colored("编辑器内容为空，操作已取消。", 'yellow')
        return

    output_folder = input("请输入要恢复到的文件夹路径: ").strip()
    if not output_folder:
        print_colored("错误: 未指定输出文件夹，操作已取消。", 'red')
        return

    # Try to parse as compressed with metadata
    try:
        # Convert string content to bytes for stream processing
        editor_content_bytes = editor_content_str.encode('utf-8')
        
        # Attempt to read metadata
        metadata_bytes = b""
        content_stream = io.BytesIO(editor_content_bytes)
        while True:
            line = content_stream.readline()
            if line.strip() == METADATA_SEPARATOR.strip(): # Compare stripped versions
                break
            if not line: # EOF before separator
                raise ValueError("Metadata separator not found.")
            metadata_bytes += line
        
        metadata = json.loads(metadata_bytes.decode('utf-8'))
        # In this version, we only support lzma, but we still read the method for compatibility
        compression_method = metadata.get("compression_method", "lzma") 
        
        compressed_data_from_editor = content_stream.read() # Rest of the stream is compressed data

        print_colored(f"检测到压缩格式 ({compression_method})，开始恢复...", 'green')
        decompressed_bytes = decompress_data(compressed_data_from_editor)
        with io.BytesIO(decompressed_bytes) as stream:
            _restore_from_snapshot_stream(stream, output_folder)
        return

    except (lzma.LZMAError, ValueError, json.JSONDecodeError, base64.binascii.Error):
        # If metadata parsing or decompression fails, try as uncompressed
        print("解压失败或无元数据，正在尝试作为未压缩内容进行解析...")
        if "--- entry ---" in editor_content_str:
            print_colored("检测到未压缩格式，开始恢复...", 'green')
            with io.BytesIO(editor_content_str.encode('utf-8')) as stream:
                _restore_from_snapshot_stream(stream, output_folder)
        else:
            print_colored("错误: 无法识别编辑器中的内容。既不是有效的压缩快照，也不是标准的未压缩快照格式。", 'red')
    except Exception as e:
        print_colored(f"从编辑器恢复时发生未知错误: {e}", 'red')
        import traceback
        traceback.print_exc()

# ==============================================================================
# Utility Functions
# ==============================================================================

def compress_data(data_bytes):
    """使用LZMA和b85编码获得高压缩率"""
    # 预设9是最高压缩级别
    filters = [{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}]
    compressed = lzma.compress(data_bytes, format=lzma.FORMAT_XZ, filters=filters)
    return base64.b85encode(compressed)

def decompress_data(compressed_data):
    """解压使用b85和LZMA压缩的数据"""
    decoded_bytes = base64.b85decode(compressed_data)
    return lzma.decompress(decoded_bytes, format=lzma.FORMAT_XZ)

def get_text_from_editor():
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
    if not editor:
        if platform.system() == 'Windows':
            editor = 'notepad'
        else:
            for e in ['vim', 'vi', 'nano']:
                if subprocess.run(['which', e], capture_output=True, text=True).returncode == 0:
                    editor = e
                    break
            else:
                editor = 'vi'

    print_colored(f"即将使用 '{os.path.basename(editor)}' 打开一个临时文件...", 'yellow')
    print_colored("请在编辑器中输入或粘贴您的内容，保存并关闭编辑器后，程序将自动继续。", 'blue')
    
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as tf:
            temp_filename = tf.name
            tf.write("# 请在此处粘贴或输入您的内容。\n")
            tf.write("# 完成后，请保存文件并关闭编辑器。\n")
            tf.write("\n")
        
        subprocess.run([editor, temp_filename], check=True)
        
        with open(temp_filename, 'r', encoding='utf-8') as tf:
            lines = tf.readlines()
            content_lines = [line for line in lines if not line.strip().startswith('#')]
            return "".join(content_lines)

    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print_colored(f"\n错误: 无法启动文本编辑器 '{editor}'。", 'red')
        print_colored(f"请确保您的 VISUAL/EDITOR 环境变量已正确设置，或编辑器在系统 PATH 中。", 'red')
        return None
    except Exception as e:
        print_colored(f"\n从编辑器读取内容时发生未知错误: {e}", 'red')
        return None
    finally:
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.remove(temp_filename)

def get_unique_filepath(filepath):
    path = Path(filepath)
    if not path.exists():
        return path
    directory = path.parent
    name = path.stem
    extension = path.suffix
    counter = 1
    while True:
        new_name = f"{name}_{counter}{extension}"
        new_filepath = directory / new_name
        if not new_filepath.exists():
            return new_filepath
        counter += 1

def print_colored(text, color):
    if platform.system() == 'Windows':
        try:
            import colorama
            colorama.init()
            colors = {'red': colorama.Fore.RED, 'green': colorama.Fore.GREEN, 'yellow': colorama.Fore.YELLOW, 'blue': colorama.Fore.BLUE, 'end': colorama.Style.RESET_ALL}
            print(f"{colors.get(color, '')}{text}{colors['end']}")
        except ImportError:
            print(text)
    else:
        colors = {'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m', 'blue': '\033[94m', 'end': '\033[0m'}
        print(f"{colors.get(color, '')}{text}{colors['end']}")

def validate_path(path):
    if not os.path.exists(path):
        print_colored(f"错误: 路径 '{path}' 不存在", 'red')
        return False
    return True

def show_progress(current, total, prefix=""):
    percent = int(current * 100 / total) if total > 0 else 0
    bar_length = 40
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r{prefix} [{bar}] {percent}% ({current}/{total})", end='')
    if current == total:
        print()

def show_progress_indeterminate(current, prefix=""):
    spinner = ['-', '\\', '|', '/']
    print(f"\r{prefix} {spinner[current % 4]} 已处理 {current} 个条目...", end='')

# ==============================================================================
# Main Execution Block
# ==============================================================================

if __name__ == "__main__":
    if platform.system() == 'Windows':
        try:
            import colorama
        except ImportError:
            print("提示: 建议安装colorama以获得彩色输出 (pip install colorama)")
    
    print_colored("=== 文件快照工具 (v5.1 高效安全版) by WilsonShi ===", 'blue')
    print("--- 从文件创建/恢复 ---")
    print("1. 创建快照文件 (无压缩，支持所有文件类型)")
    print("2. 创建高压缩率快照文件 (LZMA)")
    print("3. 从快照文件恢复") 
    print("4. 从压缩快照恢复")
    print("--- 通过文本编辑器恢复 ---")
    print("5. 通过编辑器粘贴内容恢复 (自动判断格式)")
    print_colored("0. 退出", 'yellow')
    
    while True:
        choice = input("\n请选择功能 (0-5): ").strip()
        
        if choice == "0":
            print_colored("已退出程序", 'green')
            break
            
        if choice not in [str(i) for i in range(1, 6)]:
            print_colored("无效的选择，请重新输入!", 'red')
            continue
            
        try:
            def progress_callback(current, total):
                show_progress(current, total, "处理进度:")

            if choice == "1":
                path = input("请输入要处理的文件夹或文件路径: ").strip()
                if not validate_path(path): continue
                output_file = gather_files_to_txt(path, show_progress_callback=progress_callback)
                print()
                print_colored(f"操作完成! 输出文件: {output_file}", 'green')

            elif choice == "2":
                path = input("请输入要处理的文件夹或文件路径: ").strip()
                if not validate_path(path): continue
                output_file = gather_files_to_txt_compressed(path, show_progress_callback=progress_callback)
                print()
                print_colored(f"操作完成! 输出文件: {output_file}", 'green')
                
            elif choice == "3":
                txt_path = input("请输入快照文件路径: ").strip()
                if not validate_path(txt_path): continue
                output_folder = input("请输入要恢复到的文件夹路径: ").strip()
                if not output_folder:
                    print_colored("错误: 未指定输出文件夹。", 'red')
                    continue
                restore_files_from_txt(txt_path, output_folder)

            elif choice == "4":
                txt_path = input("请输入压缩快照文件路径: ").strip()
                if not validate_path(txt_path): continue
                output_folder = input("请输入要恢复到的文件夹路径: ").strip()
                if not output_folder:
                    print_colored("错误: 未指定输出文件夹。", 'red')
                    continue
                restore_files_from_compressed_txt(txt_path, output_folder)
            
            elif choice == "5":
                restore_from_editor_text()

        except FileNotFoundError as e:
            print_colored(f"\n文件未找到错误: {e}", 'red')
        except PermissionError as e:
            print_colored(f"\n权限错误: {e}", 'red')
        except KeyboardInterrupt:
            print_colored("\n\n操作被用户中断。", 'yellow')
        except Exception as e:
            print_colored(f"\n发生未知严重错误: {e}", 'red')
            import traceback
            traceback.print_exc()