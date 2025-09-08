import os
import re
import lzma
import base64
import json
import platform
import argparse
import sys
import hashlib
import datetime
from pathlib import Path


def is_binary_file(file_path):
    """
    判断文件是否为二进制文件 - 改进的跨平台检测
    """
    try:
        # 检查文件扩展名 - 某些扩展名明确表示二进制文件
        _, ext = os.path.splitext(file_path.lower())
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db', '.sqlite',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.webp',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.jar', '.war', '.ear', '.class', '.dex', '.apk',
            '.wasm', '.o', '.obj', '.lib', '.a'
        }
        
        if ext in binary_extensions:
            return True  # 明确的二进制文件扩展名
        
        # 检查文件扩展名 - 某些扩展名明确表示文本文件
        text_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
            '.md', '.rst', '.csv', '.sql', '.sh', '.bat', '.ps1', '.java', '.c', 
            '.cpp', '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift',
            '.kt', '.scala', '.clj', '.hs', '.ml', '.fs', '.vb', '.pl', '.r',
            '.m', '.mm', '.tsx', '.jsx', '.vue', '.svelte', '.ts', '.coffee',
            '.sass', '.scss', '.less', '.styl', '.ini', '.cfg', '.conf', '.log',
            '.properties', '.gitignore', '.dockerignore', '.editorconfig'
        }
        
        if ext in text_extensions:
            return False  # 明确的文本文件扩展名
        
        # 首先尝试以文本方式读取文件
        # 这是最可靠的方法来判断文件是否为文本
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # 尝试读取前1024个字符
            return False  # 如果成功读取，则为文本文件
        except UnicodeDecodeError:
            pass  # UTF-8解码失败，继续其他检测
        
        # 尝试其他常见编码
        common_encodings = ['utf-16', 'utf-16-le', 'utf-16-be', 'latin1', 'cp1252']
        for encoding in common_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read(1024)
                    # 检查内容是否看起来像文本
                    if content and content.isprintable() or '\n' in content or '\t' in content:
                        return False  # 成功解码且看起来像文本
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # 如果所有编码都失败，进行字节级检测
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if len(chunk) == 0:
                return False  # 空文件视为文本文件
            
            # 字节级启发式检测
            null_count = chunk.count(0)
            if null_count > 0:  # 如果包含空字节，很可能是二进制
                return True
            
            # 检查是否包含大量非可打印字符
            printable_count = sum(1 for b in chunk if 32 <= b <= 126 or b in (9, 10, 13))
            if len(chunk) > 0 and printable_count < len(chunk) * 0.7:  # 如果少于70%是可打印字符
                return True
            
            # 检查是否包含连续的控制字符
            control_chars = sum(1 for b in chunk if b < 32 and b not in (9, 10, 13))
            if control_chars > len(chunk) * 0.1:  # 如果超过10%是控制字符
                return True
            
            return False  # 默认视为文本文件
            
    except Exception:
        return False  # 出错时默认为文本文件


def gather_files_to_txt(input_path, show_progress_callback=None):
    """
    将文件夹或单个文件内容合并到一个txt文件中
    
    :param input_path: 要处理的文件夹路径或文件路径(可以是文件列表)
    :return: 输出文件的Path对象
    """
    input_path = get_safe_path(input_path)
    
    # 处理输入是文件的情况
    if os.path.isfile(input_path):
        # 检查是否为文件列表文件
        is_file_list = False
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                # 简单判断是否为文件列表：第一行是否为有效文件路径
                if lines and os.path.exists(lines[0]):
                    is_file_list = True
        except:
            pass
        
        if is_file_list:
            # 读取输入文件中的文件列表
            with open(input_path, 'r', encoding='utf-8') as f:
                file_list = [line.strip() for line in f if line.strip()]
            
            # 确定输出文件路径
            base_name = os.path.basename(input_path)
            output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_from_list_{base_name}.txt")))
            
            files_to_process = []
            for file_path in file_list:
                if os.path.exists(file_path):
                    relative_path = os.path.basename(file_path)
                    files_to_process.append((relative_path, file_path))
        else:
            # 单个文件
            base_name = os.path.basename(input_path)
            output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_file_{base_name}.txt")))
            files_to_process = [(base_name, input_path)]
    else:
        # 处理文件夹的情况
        folder_name = os.path.basename(os.path.normpath(input_path))
        output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_files_{folder_name}.txt")))
        base_path = os.path.normpath(input_path)
        files_to_process = []
        
        # 收集所有文件和空目录
        for root, dirs, files in os.walk(input_path):
            # 添加文件
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace('\\', '/')
                files_to_process.append((relative_path, file_path))
            
            # 添加空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                # 检查是否为空目录
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace('\\', '/')
                    files_to_process.append((relative_path, dir_path))
    
    # 写入文件内容，使用更紧凑的格式
    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write("UNCOMPRESSED\n")  # 简化格式标识符
        total_files = len(files_to_process)
        processed_count = 0
        
        for relative_path, file_path in files_to_process:
            try:
                out_f.write(f"\n@{relative_path}\n")  # 简化标记
                # 检查是否为目录
                if os.path.isdir(file_path):
                    out_f.write("[EMPTY_DIRECTORY]\n")
                # 检查是否为二进制文件
                elif is_binary_file(file_path):
                    # 二进制文件使用base64编码
                    with open(file_path, 'rb') as in_f:
                        content = base64.b64encode(in_f.read()).decode('ascii')
                        out_f.write(f"B\n{content}\n")  # 简化二进制标记
                else:
                    # 文本文件直接读取
                    with open(file_path, 'r', encoding='utf-8') as in_f:
                        content = in_f.read()
                        out_f.write(content)
                out_f.write("\n")
                
                processed_count += 1
            except Exception as e:
                out_f.write(f"\n!{relative_path}\n{str(e)}\n")  # 简化错误标记
            
            if show_progress_callback:
                show_progress_callback(processed_count, total_files)

    return output_file


def gather_files_to_txt_compressed(input_path, show_progress_callback=None):
    """将文件夹或文件内容在内存中合并并压缩，然后写入一个txt文件"""
    input_path = get_safe_path(input_path)
    
    # 确定输出文件路径
    if os.path.isfile(input_path):
        base_name = os.path.basename(input_path)
        initial_output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"compressed_{base_name}.txt")))
        files_to_process = [(os.path.basename(input_path), input_path)]
    else:
        folder_name = os.path.basename(os.path.normpath(input_path))
        initial_output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"compressed_files_{folder_name}.txt")))
        base_path = os.path.normpath(input_path)
        files_to_process = []
        
        # 收集所有文件和空目录
        for root, dirs, files in os.walk(input_path):
            # 添加文件
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace('\\', '/')
                files_to_process.append((relative_path, file_path))
            
            # 添加空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                # 检查是否为空目录
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace('\\', '/')
                    files_to_process.append((relative_path, dir_path))

    output_file = Path(get_unique_filepath(str(initial_output_file)))

    # 在内存中构建内容，使用更紧凑的格式
    content_parts = []
    total_files = len(files_to_process)
    original_size = 0  # 记录原始文件总大小
    processed_count = 0
    
    for relative_path, file_path in files_to_process:
        try:
            content_parts.append(f"\n@{relative_path}\n")  # 简化标记，移除@F前缀
            # 检查是否为目录
            if os.path.isdir(file_path):
                original_size += 0  # 目录大小为0
                content_parts.append("[EMPTY_DIRECTORY]\n")
            else:
                original_size += os.path.getsize(file_path)  # 直接获取文件大小
                # 检查是否为二进制文件
                if is_binary_file(file_path):
                    # 二进制文件使用base64编码
                    with open(file_path, 'rb') as in_f:
                        content = base64.b64encode(in_f.read()).decode('ascii')
                        content_parts.append(f"B\n{content}\n")  # 简化二进制标记
                else:
                    # 文本文件直接读取
                    with open(file_path, 'r', encoding='utf-8') as in_f:
                        content = in_f.read()
                        content_parts.append(content)
            content_parts.append("\n")
            
            processed_count += 1
        except Exception as e:
            content_parts.append(f"\n!{relative_path}\n{str(e)}\n")  # 简化错误标记
        
        if show_progress_callback:
            show_progress_callback(processed_count, total_files)

    # 使用自定义分隔符而不是长分隔线
    full_content = "".join(content_parts)
    compressed_content = compress_text(full_content)
    
    # 将压缩标识添加到压缩后的内容开头，使用更短的标识符
    compressed_content = "COMPRESSED\n" + compressed_content
    
    compressed_size = len(compressed_content.encode('utf-8'))  # 获取压缩后大小
    
    # 计算并显示压缩比例
    if original_size > 0:
        ratio = (1 - compressed_size / original_size) * 100
        print_colored(f"压缩比例: 原始大小 {original_size/1024:.2f} KB → 压缩后 {compressed_size/1024:.2f} KB (减少 {ratio:.2f}%) ", 'blue')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(compressed_content)
        
    return output_file


def restore_files_from_txt(txt_path, output_folder):
    """
    从合并的文本文件恢复原始文件
    现在可以自动判断是压缩文件还是普通文本文件
    """
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return
    
    # 读取文件前几行判断文件类型
    with open(txt_path, 'r', encoding='utf-8') as f:
        first_lines = [f.readline().strip() for _ in range(3)]
    
    first_line = first_lines[0] if first_lines else ""
    
    # 检查是否为旧版本格式
    if first_line == "=== SNAPSHOT_FORMAT: COMPRESSED ===":
        restore_files_from_old_compressed_txt(txt_path, output_folder)
        return
    elif first_line == "=== SNAPSHOT_FORMAT: UNCOMPRESSED ===":
        restore_files_from_old_txt(txt_path, output_folder)
        return
    
    # 新版本格式处理
    if first_line == "COMPRESSED":
        restore_files_from_compressed_txt(txt_path, output_folder)
        return  # 压缩恢复完成后直接返回
    elif first_line == "UNCOMPRESSED":
        # 移除格式标识行后调用原始恢复逻辑
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read().split('\n', 1)[1]  # 跳过第一行
        
        os.makedirs(output_folder, exist_ok=True)
        
        # 分割文件和目录块 - 使用新的简化@格式
        parts = []
        current_item = None
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查是否为有效的文件标记（@后跟路径，不是CSS的@规则）
            # 检查是否为有效的文件标记（@后跟路径，不是CSS的@规则或Python装饰器）
            if (line.startswith('@') and len(line) > 1 and 
                not line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face')) and
                not line[1:].strip().startswith(('app.route', 'staticmethod', 'classmethod', 'property')) and
                not 'def ' in line and not 'class ' in line):
                if current_item:
                    parts.extend(current_item)
                
                file_path = line[1:]  # 移除@前缀
                
                # 收集内容直到下一个有效的文件标记或错误标记
                content_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # 如果遇到新的文件标记或错误标记，停止收集
                    if (next_line.startswith('@') and len(next_line) > 1 and not next_line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face'))) or next_line.startswith('!'):
                        break
                    content_lines.append(next_line)
                    i += 1
                
                # 处理内容
                if content_lines and content_lines[0] == 'B':
                    # 二进制文件
                    content_block = "[BINARY_FILE_BASE64]\n" + '\n'.join(content_lines[1:])
                elif content_lines and content_lines[0] == '[EMPTY_DIRECTORY]':
                    # 空目录
                    content_block = "[EMPTY_DIRECTORY]"
                else:
                    # 文本文件，保持所有内容包括行尾空白
                    content_block = '\n'.join(content_lines)
                
                current_item = ["文件", file_path, content_block]
            elif line.startswith('!'):
                # 错误文件
                if current_item:
                    parts.extend(current_item)
                
                file_path = line[1:]  # 移除!前缀
                error_content = lines[i+1] if i+1 < len(lines) else ""
                current_item = ["文件", file_path, f"ERROR: {error_content}"]
                i += 2

            else:
                # 如果不是文件标记，可能是之前文件内容的一部分，继续处理
                if current_item:
                    # 将当前行添加到当前项目的内容中
                    current_item[2] += '\n' + line
                i += 1
        
        # 添加最后一个项目
        if current_item:
            parts.extend(current_item)
        
        # 确保我们有正确的格式：类型、路径、内容循环
        if len(parts) % 3 != 0:
            print_colored("警告: 快照文件格式可能已损坏。", 'yellow')
            return
            
        total_blocks = len(parts) // 3
        if total_blocks == 0:
            print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
            return
    else:
        print_colored("错误: 无法识别的文件格式!", 'red')
        return  # 添加返回语句，避免继续执行后面的代码

    # 恢复逻辑 - 增强错误恢复和验证
    show_progress(0, total_blocks, "恢复进度:")
    
    # 错误跟踪和统计
    success_count = 0
    error_count = 0
    error_details = []
    
    for i in range(0, len(parts), 3):
        if i + 2 >= len(parts):
            break
            
        block_type = parts[i]      # "文件" 或 "目录"
        file_path = parts[i+1]     # 路径
        content_block = parts[i+2]  # 内容
        
        # 清理文件路径，处理Windows不支持的字符
        sanitized_file_path = sanitize_file_path(file_path)
        full_path = os.path.join(output_folder, sanitized_file_path)
        
        try:
            if content_block.strip() == "[EMPTY_DIRECTORY]":
                # 创建空目录
                os.makedirs(full_path, exist_ok=True)
                success_count += 1
                
            else:  # 文件
                # 确保父目录存在
                parent_dir = os.path.dirname(full_path)
                if parent_dir:  # 只有当父目录不为空时才创建
                    os.makedirs(parent_dir, exist_ok=True)
                
                # 检查是否为二进制文件
                if content_block.strip().startswith("[BINARY_FILE_BASE64]"): 
                    # 二进制文件
                    base64_content = content_block.split('\n', 1)[1]
                    
                    # 备份已存在的文件
                    if os.path.exists(full_path):
                        backup_existing_file(full_path)
                    
                    with open(full_path, 'wb') as f:
                        f.write(base64.b64decode(base64_content.encode('ascii')))
                    success_count += 1
                    
                else:
                    # 文本文件，保持原始内容
                    
                    # 备份已存在的文件
                    if os.path.exists(full_path):
                        backup_existing_file(full_path)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content_block)
                    success_count += 1
                    
        except OSError as e:
            # 文件系统错误（权限、磁盘空间等）
            error_msg = f"文件系统错误: {sanitized_file_path} - {str(e)}"
            # 提供更具体的权限错误信息
            if e.errno == 13:  # Permission denied
                error_msg += " (权限被拒绝，请检查文件权限或以管理员身份运行)"
            elif e.errno == 28:  # No space left on device
                error_msg += " (磁盘空间不足，请清理磁盘空间)"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except (ValueError, base64.binascii.Error) as e:
            # Base64 解码错误
            error_msg = f"Base64解码错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except UnicodeDecodeError as e:
            # 编码错误
            error_msg = f"编码错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except Exception as e:
            # 其他未知错误
            error_msg = f"未知错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
        
        show_progress(i // 3 + 1, total_blocks, "恢复进度:")
    
    # 生成恢复报告
    print()
    print_colored(f"恢复完成: {success_count} 个文件成功, {error_count} 个文件失败", 
                 'green' if error_count == 0 else 'yellow')
    
    if error_count > 0:
        print_colored("\n错误详情:", 'yellow')
        for error in error_details[:5]:  # 只显示前5个错误
            print_colored(f"  - {error}", 'yellow')
        if error_count > 5:
            print_colored(f"  - ... 还有 {error_count - 5} 个错误", 'yellow')
    
    # 创建详细的恢复报告文件
    create_restore_report(success_count, error_count, error_details, output_folder)
    
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')


def compress_text(text):
    """压缩文本内容，智能选择最佳压缩策略"""
    import zlib
    import bz2
    
    # 预处理：保持所有原始内容，不移除空白
    processed_text = text
    
    original_bytes = processed_text.encode('utf-8')
    original_size = len(original_bytes)
    
    # 对于小文件（<2KB），使用简单快速的压缩
    if original_size < 2048:
        print_colored("使用快速压缩模式（小文件优化）...", 'blue')
        try:
            # 使用简单的LZMA压缩，类似旧版本
            compressed = lzma.compress(original_bytes, preset=6)  # 中等压缩级别，平衡速度和效果
            encoded = base64.b85encode(compressed).decode('ascii')
            return encoded  # 直接返回，兼容旧格式
        except:
            return processed_text  # 压缩失败则返回原文
    
    # 对于大文件，使用多算法优化
    print_colored("使用多算法优化模式（大文件优化）...", 'blue')
    
    # 重新组织内容以提高压缩率
    def reorganize_content(text):
        lines = text.split('\n')
        text_sections = []
        binary_sections = []
        directory_sections = []
        current_section = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('@'):
                # 保存当前section
                if current_section:
                    section_content = '\n'.join(current_section)
                    if 'B\n' in section_content:
                        binary_sections.append(section_content)
                    elif '[EMPTY_DIRECTORY]' in section_content:
                        directory_sections.append(section_content)
                    else:
                        text_sections.append(section_content)
                
                # 开始新section
                current_section = [line]
                i += 1
                
                # 收集section内容
                while i < len(lines) and not lines[i].startswith('@') and not lines[i].startswith('!'):
                    current_section.append(lines[i])
                    i += 1
                continue
            i += 1
        
        # 添加最后一个section
        if current_section:
            section_content = '\n'.join(current_section)
            if 'B\n' in section_content:
                binary_sections.append(section_content)
            elif '[EMPTY_DIRECTORY]' in section_content:
                directory_sections.append(section_content)
            else:
                text_sections.append(section_content)
        
        # 重新组织：目录 -> 文本文件 -> 二进制文件
        return '\n'.join(directory_sections + text_sections + binary_sections)
    
    reorganized_text = reorganize_content(processed_text)
    reorganized_bytes = reorganized_text.encode('utf-8')
    
    # 测试多种压缩算法
    results = []
    
    # 1. LZMA压缩
    try:
        lzma_compressed = lzma.compress(
            reorganized_bytes,
            format=lzma.FORMAT_XZ,
            preset=9 | lzma.PRESET_EXTREME,
            check=lzma.CHECK_CRC32
        )
        lzma_encoded = base64.b85encode(lzma_compressed).decode('ascii')
        results.append(('LZMA', lzma_encoded, len(lzma_encoded)))
        print_colored(f"  LZMA: {len(lzma_encoded)} 字符", 'blue')
    except Exception as e:
        print_colored(f"  LZMA失败: {e}", 'yellow')
    
    # 2. BZ2压缩
    try:
        bz2_compressed = bz2.compress(reorganized_bytes, compresslevel=9)
        bz2_encoded = base64.b85encode(bz2_compressed).decode('ascii')
        results.append(('BZ2', bz2_encoded, len(bz2_encoded)))
        print_colored(f"  BZ2: {len(bz2_encoded)} 字符", 'blue')
    except Exception as e:
        print_colored(f"  BZ2失败: {e}", 'yellow')
    
    # 3. ZLIB压缩
    try:
        zlib_compressed = zlib.compress(reorganized_bytes, level=9)
        zlib_encoded = base64.b85encode(zlib_compressed).decode('ascii')
        results.append(('ZLIB', zlib_encoded, len(zlib_encoded)))
        print_colored(f"  ZLIB: {len(zlib_encoded)} 字符", 'blue')
    except Exception as e:
        print_colored(f"  ZLIB失败: {e}", 'yellow')
    
    if not results:
        print_colored("警告: 所有压缩算法都失败，使用原始文本", 'yellow')
        return f"RAW:{processed_text}"
    
    # 选择最佳结果
    best_method, best_compressed, best_size = min(results, key=lambda x: x[2])
    print_colored(f"选择最佳算法: {best_method} (压缩后 {best_size} 字符)", 'green')
    
    return f"{best_method}:{best_compressed}"


def restore_files_from_compressed_txt(txt_path, output_folder):
    """从压缩的文本文件恢复原始文件"""
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return

    # 读取压缩内容
    print("正在读取并解压缩文件...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line != "COMPRESSED":
            print_colored("错误: 文件格式不正确!", 'red')
            return
        # 读取剩余内容
        compressed_content = f.read()
    
    try:
        # 解析压缩格式和数据
        if ':' in compressed_content:
            method, encoded_data = compressed_content.split(':', 1)
        else:
            # 兼容旧格式，默认使用LZMA
            method = 'LZMA'
            encoded_data = compressed_content
        
        # 先解码base85
        compressed = base64.b85decode(encoded_data.encode('ascii'))
        
        # 根据压缩方法解压
        if method == 'LZMA':
            decompressed_content = lzma.decompress(compressed).decode('utf-8')
        elif method == 'BZ2':
            import bz2
            decompressed_content = bz2.decompress(compressed).decode('utf-8')
        elif method == 'ZLIB':
            import zlib
            decompressed_content = zlib.decompress(compressed).decode('utf-8')
        elif method == 'RAW':
            # 原始文本，无需解压
            decompressed_content = encoded_data
        else:
            print_colored(f"错误: 不支持的压缩方法 {method}", 'red')
            return
        
        # 显示解压比例和使用的算法
        compressed_size = len(compressed_content.encode('utf-8'))
        original_size = len(decompressed_content.encode('utf-8'))
        if compressed_size > 0:
            ratio = (original_size / compressed_size) * 100
            print_colored(f"解压比例: 压缩文件 {compressed_size/1024:.2f} KB → 解压后 {original_size/1024:.2f} KB (原始大小的 {ratio:.2f}%) [算法: {method}]", 'blue')
            
    except Exception as e:
        print_colored(f"解压缩失败: {str(e)}", 'red')
        return
    
    # 恢复文件内容
    os.makedirs(output_folder, exist_ok=True)
    
    # 分割文件和目录块 - 使用新的简化@格式
    parts = []
    current_item = None
    lines = decompressed_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否为有效的文件标记（@后跟路径，不是CSS的@规则或Python装饰器）
        if (line.startswith('@') and len(line) > 1 and 
            not line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face')) and
            not line[1:].strip().startswith(('app.route', 'staticmethod', 'classmethod', 'property')) and
            not 'def ' in line and not 'class ' in line):
            if current_item:
                parts.extend(current_item)
            
            file_path = line[1:]  # 移除@前缀
            
            # 收集内容直到下一个有效的文件标记或错误标记
            content_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # 如果遇到新的文件标记或错误标记，停止收集
                if (next_line.startswith('@') and len(next_line) > 1 and not next_line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face'))) or next_line.startswith('!'):
                    break
                content_lines.append(next_line)
                i += 1
            
            # 处理内容
            if content_lines and content_lines[0] == 'B':
                # 二进制文件
                content = "[BINARY_FILE_BASE64]\n" + '\n'.join(content_lines[1:])
            elif content_lines and content_lines[0] == '[EMPTY_DIRECTORY]':
                # 空目录
                content = "[EMPTY_DIRECTORY]"
            else:
                # 文本文件，移除最后的空行（如果有的话）
                if content_lines and content_lines[-1] == '':
                    content_lines = content_lines[:-1]
                content = '\n'.join(content_lines)
            
            current_item = ["文件", file_path, content]
            continue
        elif line.startswith('!'):
            # 错误文件
            if current_item:
                parts.extend(current_item)
            
            file_path = line[1:]  # 移除!前缀
            error_content = lines[i+1] if i+1 < len(lines) else ""
            current_item = ["文件", file_path, f"ERROR: {error_content}"]
            i += 2

        else:
            # 如果不是文件标记，可能是之前文件内容的一部分，继续处理
            if current_item:
                # 将当前行添加到当前项目的内容中
                current_item[2] += '\n' + line
            i += 1
    
    # 添加最后一个项目
    if current_item:
        parts.extend(current_item)
    
    # 确保我们有正确的格式：类型、路径、内容循环
    if len(parts) % 3 != 0:
        print_colored("警告: 快照文件格式可能已损坏。", 'yellow')
        return
        
    total_blocks = len(parts) // 3
    if total_blocks == 0:
        print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
        return

    # 恢复逻辑 - 增强错误恢复和验证
    show_progress(0, total_blocks, "恢复进度:")
    
    # 错误跟踪和统计
    success_count = 0
    error_count = 0
    error_details = []
    
    for i in range(0, len(parts), 3):
        if i + 2 >= len(parts):
            break
            
        block_type = parts[i]      # "文件" 或 "目录"
        file_path = parts[i+1]     # 路径
        content_block = parts[i+2]  # 内容
        
        # 清理文件路径，处理Windows不支持的字符
        sanitized_file_path = sanitize_file_path(file_path)
        full_path = os.path.join(output_folder, sanitized_file_path)
        
        try:
            if content_block.strip() == "[EMPTY_DIRECTORY]":
                # 创建空目录
                os.makedirs(full_path, exist_ok=True)
                success_count += 1
                
            else:  # 文件
                # 确保父目录存在
                parent_dir = os.path.dirname(full_path)
                if parent_dir:  # 只有当父目录不为空时才创建
                    os.makedirs(parent_dir, exist_ok=True)
                
                # 检查是否为二进制文件
                if content_block.strip().startswith("[BINARY_FILE_BASE64]"): 
                    # 二进制文件
                    base64_content = content_block.split('\n', 1)[1]
                    with open(full_path, 'wb') as f:
                        f.write(base64.b64decode(base64_content.encode('ascii')))
                    success_count += 1
                    
                else:
                    # 文本文件，保持原始内容
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content_block)
                    success_count += 1
                    
        except OSError as e:
            # 文件系统错误（权限、磁盘空间等）
            error_msg = f"文件系统错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except (ValueError, base64.binascii.Error) as e:
            # Base64 解码错误
            error_msg = f"Base64解码错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except UnicodeDecodeError as e:
            # 编码错误
            error_msg = f"编码错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except Exception as e:
            # 其他未知错误
            error_msg = f"未知错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
        
        show_progress(i // 3 + 1, total_blocks, "恢复进度:")
    
    # 生成恢复报告
    print()
    print_colored(f"恢复完成: {success_count} 个文件成功, {error_count} 个文件失败", 
                 'green' if error_count == 0 else 'yellow')
    
    if error_count > 0:
        print_colored("\n错误详情:", 'yellow')
        for error in error_details[:5]:  # 只显示前5个错误
            print_colored(f"  - {error}", 'yellow')
        if error_count > 5:
            print_colored(f"  - ... 还有 {error_count - 5} 个错误", 'yellow')
    
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')


def get_unique_filepath(filepath):
    """如果文件路径已存在，则在扩展名前附加'_<数字>'以创建唯一路径"""
    if not os.path.exists(filepath):
        return filepath
    
    filepath = Path(filepath)
    directory = filepath.parent
    name = filepath.stem
    extension = filepath.suffix
    
    counter = 1
    while True:
        new_name = f"{name}_{counter}{extension}"
        new_filepath = directory / new_name
        if not new_filepath.exists():
            return str(new_filepath)  # 返回字符串而不是Path对象
        counter += 1


def backup_existing_file(file_path):
    """备份已存在的文件，避免覆盖"""
    if not os.path.exists(file_path):
        return True  # 文件不存在，无需备份
    
    try:
        # 创建备份目录
        backup_dir = os.path.join(os.path.dirname(file_path), ".snapshot_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, f"{filename}.backup_{timestamp}")
        
        # 复制文件到备份位置
        import shutil
        shutil.copy2(file_path, backup_path)
        
        print_colored(f"已备份原文件: {file_path} → {backup_path}", 'blue')
        return True
        
    except Exception as e:
        print_colored(f"警告: 备份文件 {file_path} 失败: {str(e)}", 'yellow')
        return False


def validate_snapshot_file(file_path):
    """验证快照文件的完整性和有效性"""
    if not os.path.isfile(file_path):
        return False, "文件不存在"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
            if first_line == "COMPRESSED":
                # 压缩格式验证
                compressed_content = f.read()
                if ':' in compressed_content:
                    method, encoded_data = compressed_content.split(':', 1)
                    if method not in ['LZMA', 'BZ2', 'ZLIB', 'RAW']:
                        return False, f"不支持的压缩方法: {method}"
                    
                    # 验证base85编码
                    try:
                        base64.b85decode(encoded_data.encode('ascii'))
                    except (ValueError, base64.binascii.Error):
                        return False, "Base85编码格式错误"
                
                return True, "压缩格式验证通过"
                
            else:
                # 普通文本格式验证
                content = first_line + f.read()
                lines = content.split('\n')
                
                # 检查是否有有效的文件标记
                file_markers = [line for line in lines if 
                               line.startswith('@') and len(line) > 1 and 
                               not line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face')) and
                               not line[1:].strip().startswith(('app.route', 'staticmethod', 'classmethod', 'property')) and
                               not 'def ' in line and not 'class ' in line]
                
                if not file_markers:
                    return False, "未找到有效的文件标记"
                
                return True, "文本格式验证通过"
                
    except UnicodeDecodeError:
        return False, "文件编码错误，不是有效的UTF-8文本文件"
    except Exception as e:
        return False, f"验证过程中发生错误: {str(e)}"


def print_colored(text, color):
    """跨平台彩色打印文本"""
    if platform.system() == 'Windows':
        try:
            import colorama
            colorama.init()
            colors = {
                'red': colorama.Fore.RED,
                'green': colorama.Fore.GREEN,
                'yellow': colorama.Fore.YELLOW,
                'blue': colorama.Fore.BLUE,
                'end': colorama.Style.RESET_ALL
            }
            print(f"{colors.get(color, '')}{text}{colors['end']}")
        except ImportError:
            print(text)  # 没有安装colorama则使用普通文本
    else:
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'end': '\033[0m'
        }
        print(f"{colors.get(color, '')}{text}{colors['end']}")


def get_safe_path(path):
    """获取安全的跨平台路径"""
    return str(Path(path))

def sanitize_filename(filename):
    """清理文件名，移除Windows不支持的字符"""
    import re
    
    # Windows不允许的字符：< > : " | ? * \ /
    # 注意：在字符类中，反斜杠需要转义
    invalid_chars = r'[<>:"|?*\\/]'
    
    # 替换不合法字符为下划线
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # 处理连续的下划线，替换为单个下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # 移除开头和结尾的空格和点
    sanitized = sanitized.strip(' .')
    
    # Windows保留名称
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # 检查是否为保留名称
    name_without_ext = os.path.splitext(sanitized)[0].upper()
    if name_without_ext in reserved_names:
        sanitized = f"_{sanitized}"
    
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed_file"
    
    # 限制文件名长度（更安全的限制）
    # macOS通常支持255字节的文件名，但为了跨平台兼容性，使用更保守的限制
    max_filename_length = 150  # 更安全的限制
    if len(sanitized) > max_filename_length:
        name, ext = os.path.splitext(sanitized)
        # 确保截断后仍然有空间给扩展名
        max_name_length = max_filename_length - len(ext)
        if max_name_length > 0:
            sanitized = name[:max_name_length] + ext
        else:
            # 如果扩展名太长，只保留截断的名称
            sanitized = name[:max_filename_length]
    
    return sanitized

def sanitize_file_path(file_path):
    """清理文件路径，处理Windows不支持的字符"""
    # 分割路径为目录和文件名部分
    path_parts = file_path.split(os.sep)
    
    # 清理每个路径部分
    sanitized_parts = []
    for part in path_parts:
        if part:  # 跳过空字符串
            sanitized_part = sanitize_filename(part)
            sanitized_parts.append(sanitized_part)
    
    # 重新组合路径
    return os.sep.join(sanitized_parts)


def validate_path(path):
    """验证路径是否存在"""
    if not os.path.exists(path):
        print_colored(f"错误: 路径 '{path}' 不存在", 'red')
        return False
    return True


def calculate_file_checksum(file_path, algorithm='sha256'):
    """计算文件的校验和"""
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        print_colored(f"警告: 计算文件 {file_path} 校验和时出错: {str(e)}", 'yellow')
        return None


def verify_file_integrity(original_path, restored_path):
    """验证恢复文件的完整性"""
    if not os.path.exists(restored_path):
        return False, "恢复文件不存在"
    
    original_checksum = calculate_file_checksum(original_path)
    restored_checksum = calculate_file_checksum(restored_path)
    
    if original_checksum is None or restored_checksum is None:
        return False, "无法计算校验和"
    
    if original_checksum == restored_checksum:
        return True, "校验和匹配"
    else:
        return False, f"校验和不匹配: 原始={original_checksum[:8]}, 恢复={restored_checksum[:8]}"


def show_progress(current, total, prefix=""):
    """显示进度条"""
    percent = int(current * 100 / total) if total > 0 else 0
    bar_length = 50
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r{prefix} [{bar}] {percent}%", end='')
    if current == total:
        print()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="文件快照工具 - 支持高压缩率备份和恢复",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式模式
  python FolderSnapshot.py
  
  # 创建压缩快照
  python FolderSnapshot.py --type compress --input /path/to/folder
  
  # 创建无压缩快照
  python FolderSnapshot.py --type snapshot --input /path/to/folder
  
  # 恢复快照
  python FolderSnapshot.py --type restore --input snapshot.txt --output /restore/path
  
  # 指定输出文件
  python FolderSnapshot.py --type compress --input /path/to/folder --output backup.txt
  
  # 静默模式（无进度条）
  python FolderSnapshot.py --type compress --input /path/to/folder --quiet
        """
    )
    
    parser.add_argument(
        '--type', '-t',
        choices=['snapshot', 'compress', 'restore'],
        help='操作类型: snapshot=创建无压缩快照, compress=创建压缩快照, restore=恢复快照'
    )
    
    parser.add_argument(
        '--input', '-i',
        help='输入路径: 对于snapshot/compress是源文件夹或文件路径，对于restore是快照文件路径'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出路径: 对于snapshot/compress是输出文件路径（可选），对于restore是恢复目标文件夹'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，不显示进度条'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='FolderSnapshot v3.1 - 高压缩率文件快照工具'
    )
    
    return parser.parse_args()


def get_custom_output_path(input_path, operation_type):
    """在交互式模式中获取自定义输出路径"""
    # 生成默认路径作为提示
    default_path = generate_default_output_path(input_path, operation_type)
    
    print_colored(f"\n💡 默认输出路径: {default_path}", 'blue')
    custom_path = input("请输入自定义输出路径 (直接回车使用默认路径): ").strip()
    
    if not custom_path:
        # 用户直接回车，使用默认路径
        return default_path
    
    # 处理用户输入的路径
    custom_path = get_safe_path(custom_path)
    
    # 如果用户输入的是目录，自动生成文件名
    if os.path.isdir(custom_path):
        filename = os.path.basename(default_path)
        custom_path = os.path.join(custom_path, filename)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(custom_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 避免文件冲突
    custom_path = get_unique_filepath(custom_path)
    
    return custom_path


def run_interactive_mode():
    """运行交互式模式"""
    print_colored("=== 文件快照工具 (v3.1) ===", 'blue')
    print("1. 创建快照文件 (无压缩，支持所有文件类型)")
    print("2. 创建高压缩率快照文件 (LZMA)")
    print("3. 从快照文件恢复 (自动识别压缩类型)")
    print_colored("0. 退出", 'yellow')
    
    while True:
        choice = input("\n请选择功能 (1/2/3/0): ").strip()
        
        if choice == "0":
            print_colored("已退出程序", 'green')
            break
            
        if choice not in ("1", "2", "3"):
            print_colored("无效的选择，请重新输入!", 'red')
            continue
            
        try:
            def progress_callback(current, total):
                show_progress(current, total, "处理进度:")

            if choice == "1":
                # 创建无压缩快照
                path = input("请输入要处理的文件夹或文件路径: ").strip()
                if not validate_path(path): 
                    continue
                
                # 获取输出路径
                output_path = get_custom_output_path(path, 'snapshot')
                print_colored(f"📁 将保存到: {output_path}", 'blue')
                
                # 创建快照
                temp_output_file = gather_files_to_txt(path, show_progress_callback=progress_callback)
                
                # 移动到指定路径
                import shutil
                shutil.move(str(temp_output_file), output_path)
                
                print() # 换行
                print_colored(f"✅ 操作完成! 输出文件: {output_path}", 'green')
                
                # 显示文件大小
                file_size = os.path.getsize(output_path)
                print_colored(f"📄 文件大小: {file_size/1024:.2f} KB", 'blue')

            elif choice == "2":
                # 创建压缩快照
                path = input("请输入要处理的文件夹或文件路径: ").strip()
                if not validate_path(path): 
                    continue
                
                # 获取输出路径
                output_path = get_custom_output_path(path, 'compress')
                print_colored(f"📁 将保存到: {output_path}", 'blue')
                
                # 创建压缩快照
                temp_output_file = gather_files_to_txt_compressed(path, show_progress_callback=progress_callback)
                
                # 移动到指定路径
                import shutil
                shutil.move(str(temp_output_file), output_path)
                
                print() # 换行
                print_colored(f"✅ 操作完成! 输出文件: {output_path}", 'green')
                
                # 显示文件大小
                file_size = os.path.getsize(output_path)
                print_colored(f"📄 文件大小: {file_size/1024:.2f} KB", 'blue')
                
            elif choice == "3":
                # 恢复快照
                txt_path = input("请输入快照文件路径: ").strip()
                if not validate_path(txt_path): 
                    continue
                
                # 获取恢复目标路径
                print_colored(f"\n💡 请指定恢复目标目录", 'blue')
                output_folder = input("请输入要恢复到的文件夹路径: ").strip()
                
                if not output_folder:
                    print_colored("错误: 必须指定恢复目标路径!", 'red')
                    continue
                
                # 确保目标目录存在
                os.makedirs(output_folder, exist_ok=True)
                
                print_colored(f"📁 将恢复到: {output_folder}", 'blue')
                restore_files_from_txt(txt_path, output_folder)  # 自动判断文件类型

        except Exception as e:
            print_colored(f"\n❌ 发生严重错误: {str(e)}", 'red')
            import traceback
            if input("是否显示详细错误信息? (y/N): ").strip().lower() == 'y':
                traceback.print_exc()
            continue


def generate_default_output_path(input_path, operation_type):
    """生成默认输出路径"""
    from datetime import datetime
    
    input_path = Path(input_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if input_path.is_file():
        # 单个文件
        base_name = input_path.stem
        if operation_type == 'compress':
            return str(input_path.parent / f"{base_name}_compressed_{timestamp}.txt")
        else:
            return str(input_path.parent / f"{base_name}_snapshot_{timestamp}.txt")
    else:
        # 目录
        folder_name = input_path.name
        if operation_type == 'compress':
            return str(input_path.parent / f"{folder_name}_compressed_{timestamp}.txt")
        else:
            return str(input_path.parent / f"{folder_name}_snapshot_{timestamp}.txt")


def run_command_line_mode(args):
    """运行命令行模式"""
    # 设置进度回调
    progress_callback = None if args.quiet else lambda current, total: show_progress(current, total, "处理进度:")
    
    try:
        if args.type in ['snapshot', 'compress']:
            # 创建快照
            if not args.input:
                print_colored("错误: 需要指定输入路径 --input", 'red')
                return False
                
            if not validate_path(args.input):
                return False
            
            print_colored(f"正在处理: {args.input}", 'blue')
            
            if args.type == 'snapshot':
                # 创建无压缩快照
                output_file = gather_files_to_txt(args.input, show_progress_callback=progress_callback)
            else:
                # 创建压缩快照
                output_file = gather_files_to_txt_compressed(args.input, show_progress_callback=progress_callback)
            
            # 处理输出路径
            if args.output:
                import shutil
                final_output = get_safe_path(args.output)
                
                # 如果输出路径是目录，生成文件名
                if os.path.isdir(final_output):
                    filename = os.path.basename(str(output_file))
                    final_output = os.path.join(final_output, filename)
                
                # 确保输出目录存在
                output_dir = os.path.dirname(final_output)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                # 如果目标文件已存在，生成唯一文件名
                final_output = get_unique_filepath(final_output)
                
                shutil.move(str(output_file), final_output)
                output_file = final_output
            else:
                # 如果没有指定输出路径，使用更友好的默认命名
                default_output = generate_default_output_path(args.input, args.type)
                default_output = get_unique_filepath(default_output)
                
                import shutil
                shutil.move(str(output_file), default_output)
                output_file = default_output
            
            if not args.quiet:
                print() # 换行
            print_colored(f"✅ 操作完成! 输出文件: {output_file}", 'green')
            
            # 显示文件大小信息
            if not args.quiet:
                file_size = os.path.getsize(output_file)
                print_colored(f"📄 文件大小: {file_size/1024:.2f} KB", 'blue')
            
            return True
            
        elif args.type == 'restore':
            # 恢复快照
            if not args.input:
                print_colored("错误: 需要指定快照文件路径 --input", 'red')
                return False
                
            if not args.output:
                print_colored("错误: 需要指定恢复目标路径 --output", 'red')
                return False
                
            if not validate_path(args.input):
                return False
            
            print_colored(f"正在恢复: {args.input} → {args.output}", 'blue')
            restore_files_from_txt(args.input, args.output)
            return True
            
    except Exception as e:
        print_colored(f"❌ 操作失败: {str(e)}", 'red')
        return False


def create_restore_report(success_count, error_count, error_details, output_folder):
    """创建详细的恢复报告文件"""
    report_path = os.path.join(output_folder, "restore_report.txt")
    
    try:
        with open(report_path, 'w', encoding='utf-8') as report_file:
            report_file.write("=== 文件夹快照恢复报告 ===\n\n")
            report_file.write(f"恢复时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"目标目录: {output_folder}\n")
            report_file.write(f"成功文件: {success_count}\n")
            report_file.write(f"失败文件: {error_count}\n")
            report_file.write(f"成功率: {(success_count/(success_count + error_count)*100):.2f}%\n\n")
            
            if error_count > 0:
                report_file.write("=== 错误详情 ===\n")
                for i, error in enumerate(error_details, 1):
                    report_file.write(f"{i}. {error}\n")
            
            report_file.write("\n=== 恢复摘要 ===\n")
            if error_count == 0:
                report_file.write("✅ 所有文件恢复成功！")
            else:
                report_file.write(f"⚠️  {error_count} 个文件恢复失败，请检查错误详情。")
        
        print_colored(f"恢复报告已保存到: {report_path}", 'blue')
        return True
        
    except Exception as e:
        print_colored(f"警告: 创建恢复报告失败: {str(e)}", 'yellow')
        return False

def restore_files_from_old_txt(txt_path, output_folder):
    """从旧版本未压缩的文本文件恢复原始文件"""
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return
    
    # 读取文件内容，跳过格式标识行
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read().split('\n', 2)[2]  # 跳过前两行格式标识
    
    os.makedirs(output_folder, exist_ok=True)
    
    # 使用正则表达式分割文件块
    import re
    file_blocks = re.split(r'=== 文件: (.+?) ===\n', content)[1:]
    
    total_blocks = len(file_blocks) // 2
    if total_blocks == 0:
        print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
        return
    
    # 恢复逻辑
    show_progress(0, total_blocks, "恢复进度:")
    
    # 错误跟踪和统计
    success_count = 0
    error_count = 0
    error_details = []
    
    for i in range(0, len(file_blocks), 2):
        if i + 1 >= len(file_blocks):
            break
            
        file_path = file_blocks[i].strip().replace('\\', '/')
        file_content = file_blocks[i+1].split('\n' + "="*50)[0]
        
        # 清理文件路径，处理Windows不支持的字符
        sanitized_file_path = sanitize_file_path(file_path)
        full_path = os.path.join(output_folder, sanitized_file_path)
        
        try:
            # 确保父目录存在
            parent_dir = os.path.dirname(full_path)
            if parent_dir:  # 只有当父目录不为空时才创建
                os.makedirs(parent_dir, exist_ok=True)
            
            # 写入文件内容
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            success_count += 1
            
        except OSError as e:
            # 文件系统错误（权限、磁盘空间等）
            error_msg = f"文件系统错误: {sanitized_file_path} - {str(e)}"
            if e.errno == 13:  # Permission denied
                error_msg += " (权限被拒绝，请检查文件权限或以管理员身份运行)"
            elif e.errno == 28:  # No space left on device
                error_msg += " (磁盘空间不足，请清理磁盘空间)"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except Exception as e:
            # 其他未知错误
            error_msg = f"未知错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
        
        show_progress(i // 2 + 1, total_blocks, "恢复进度:")
    
    # 生成恢复报告
    print()
    print_colored(f"恢复完成: {success_count} 个文件成功, {error_count} 个文件失败", 
                 'green' if error_count == 0 else 'yellow')
    
    if error_count > 0:
        print_colored("\n错误详情:", 'yellow')
        for error in error_details[:5]:  # 只显示前5个错误
            print_colored(f"  - {error}", 'yellow')
        if error_count > 5:
            print_colored(f"  - ... 还有 {error_count - 5} 个错误", 'yellow')
    
    # 创建详细的恢复报告文件
    create_restore_report(success_count, error_count, error_details, output_folder)
    
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')

def restore_files_from_old_compressed_txt(txt_path, output_folder):
    """从旧版本压缩的文本文件恢复原始文件"""
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return

    # 读取压缩内容
    print("正在读取并解压缩文件...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line != "=== SNAPSHOT_FORMAT: COMPRESSED ===":
            print_colored("错误: 文件格式不正确!", 'red')
            return
        f.readline()  # 跳过空行
        compressed_content = f.read()
    
    try:
        # 解压内容
        compressed = base64.b85decode(compressed_content.encode('utf-8'))
        decompressed_content = lzma.decompress(compressed).decode('utf-8')
        
        # 显示解压比例
        compressed_size = len(compressed_content.encode('utf-8'))
        original_size = len(decompressed_content.encode('utf-8'))
        if compressed_size > 0:
            ratio = (original_size / compressed_size) * 100
            print_colored(f"解压比例: 压缩文件 {compressed_size/1024:.2f} KB → 解压后 {original_size/1024:.2f} KB (原始大小的 {ratio:.2f}%)", 'blue')
            
    except Exception as e:
        print_colored(f"解压缩失败: {str(e)}", 'red')
        return
    
    # 恢复文件内容
    os.makedirs(output_folder, exist_ok=True)
    
    # 使用正则表达式分割文件块
    import re
    file_blocks = re.split(r'=== 文件: (.+?) ===\n', decompressed_content)[1:]
    
    total_blocks = len(file_blocks) // 2
    if total_blocks == 0:
        print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
        return

    # 恢复逻辑
    show_progress(0, total_blocks, "恢复进度:")
    
    # 错误跟踪和统计
    success_count = 0
    error_count = 0
    error_details = []
    
    for i in range(0, len(file_blocks), 2):
        if i + 1 >= len(file_blocks):
            break
            
        file_path = file_blocks[i].strip().replace('\\', '/')
        file_content = file_blocks[i+1].split('\n' + "="*50)[0]
        
        # 清理文件路径，处理Windows不支持的字符
        sanitized_file_path = sanitize_file_path(file_path)
        full_path = os.path.join(output_folder, sanitized_file_path)
        
        try:
            # 确保父目录存在
            parent_dir = os.path.dirname(full_path)
            if parent_dir:  # 只有当父目录不为空时才创建
                os.makedirs(parent_dir, exist_ok=True)
            
            # 写入文件内容
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            success_count += 1
            
        except OSError as e:
            # 文件系统错误（权限、磁盘空间等）
            error_msg = f"文件系统错误: {sanitized_file_path} - {str(e)}"
            if e.errno == 13:  # Permission denied
                error_msg += " (权限被拒绝，请检查文件权限或以管理员身份运行)"
            elif e.errno == 28:  # No space left on device
                error_msg += " (磁盘空间不足，请清理磁盘空间)"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
            
        except Exception as e:
            # 其他未知错误
            error_msg = f"未知错误: {sanitized_file_path} - {str(e)}"
            print_colored(f"警告: {error_msg}", 'yellow')
            error_count += 1
            error_details.append(error_msg)
        
        show_progress(i // 2 + 1, total_blocks, "恢复进度:")
    
    # 生成恢复报告
    print()
    print_colored(f"恢复完成: {success_count} 个文件成功, {error_count} 个文件失败", 
                 'green' if error_count == 0 else 'yellow')
    
    if error_count > 0:
        print_colored("\n错误详情:", 'yellow')
        for error in error_details[:5]:  # 只显示前5个错误
            print_colored(f"  - {error}", 'yellow')
        if error_count > 5:
            print_colored(f"  - ... 还有 {error_count - 5} 个错误", 'yellow')
    
    # 创建详细的恢复报告文件
    create_restore_report(success_count, error_count, error_details, output_folder)
    
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')


# 主函数
if __name__ == "__main__":
    # 检查并尝试安装colorama (仅Windows)
    if platform.system() == 'Windows':
        try:
            import colorama
        except ImportError:
            print("检测到Windows系统，建议安装colorama以获得更好的彩色输出支持")
            print("可以通过运行: pip install colorama 来安装")
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 如果没有指定操作类型，运行交互式模式
    if not args.type:
        run_interactive_mode()
    else:
        # 运行命令行模式
        success = run_command_line_mode(args)
        sys.exit(0 if success else 1)
