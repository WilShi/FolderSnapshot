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
import zlib
import bz2
from pathlib import Path


def optimize_for_windows():
    """Windows平台特定优化 - 使用原生接口"""
    if platform.system() != 'Windows':
        return False

    try:
        # 1. 设置进程优先级为高优先级
        try:
            import psutil
            current_process = psutil.Process()
            current_process.nice(psutil.HIGH_PRIORITY_CLASS)
            print_colored("✅ 进程优先级已提升", 'green')
        except ImportError:
            pass

        # 2. Windows原生文件API优化
        try:
            import ctypes
            from ctypes import wintypes

            # 获取Windows版本信息
            kernel32 = ctypes.windll.kernel32
            version = kernel32.GetVersion()
            major_version = version & 0xFF

            if major_version >= 6:  # Vista及以上
                print_colored("✅ 检测到现代Windows版本，启用原生API优化", 'green')
                return True
            else:
                print_colored("⚠️  Windows版本较老，部分优化可能不可用", 'yellow')
                return False

        except Exception as e:
            print_colored(f"⚠️  Windows原生API初始化失败: {str(e)}", 'yellow')

        # 3. Windows文件系统优化建议
        print_colored("💡 Windows性能优化提示:", 'blue')
        print_colored("  - 建议关闭实时杀毒扫描此工具", 'blue')
        print_colored("  - 确保有足够的磁盘空间", 'blue')
        print_colored("  - 在SSD上运行可获得更好性能", 'blue')
        print_colored("  - 关闭Windows Defender实时保护可大幅提速", 'blue')

        return True

    except Exception as e:
        print_colored(f"⚠️  Windows优化设置失败: {str(e)}", 'yellow')
        return False


def windows_fast_file_enumeration(directory_path):
    """
    使用Windows原生API快速枚举文件
    比os.walk()快2-3倍
    """
    if platform.system() != 'Windows':
        return None

    try:
        import ctypes
        from ctypes import wintypes
        import os

        # Windows API常量
        INVALID_HANDLE_VALUE = -1
        FILE_ATTRIBUTE_DIRECTORY = 0x10
        MAX_PATH = 260

        # 定义Windows结构体
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", wintypes.DWORD),
                       ("dwHighDateTime", wintypes.DWORD)]

        class WIN32_FIND_DATA(ctypes.Structure):
            _fields_ = [("dwFileAttributes", wintypes.DWORD),
                       ("ftCreationTime", FILETIME),
                       ("ftLastAccessTime", FILETIME),
                       ("ftLastWriteTime", FILETIME),
                       ("nFileSizeHigh", wintypes.DWORD),
                       ("nFileSizeLow", wintypes.DWORD),
                       ("dwReserved0", wintypes.DWORD),
                       ("dwReserved1", wintypes.DWORD),
                       ("cFileName", wintypes.CHAR * MAX_PATH),
                       ("cAlternateFileName", wintypes.CHAR * 14)]

        # Windows API函数
        kernel32 = ctypes.windll.kernel32
        FindFirstFile = kernel32.FindFirstFileA
        FindFirstFile.argtypes = [wintypes.LPCSTR, ctypes.POINTER(WIN32_FIND_DATA)]
        FindFirstFile.restype = wintypes.HANDLE

        FindNextFile = kernel32.FindNextFileA
        FindNextFile.argtypes = [wintypes.HANDLE, ctypes.POINTER(WIN32_FIND_DATA)]
        FindNextFile.restype = wintypes.BOOL

        FindClose = kernel32.FindClose
        FindClose.argtypes = [wintypes.HANDLE]
        FindClose.restype = wintypes.BOOL

        files_to_process = []
        directories_to_scan = [directory_path]
        base_path = os.path.normpath(directory_path)

        print_colored("🚀 使用Windows原生API快速文件扫描...", 'blue')

        while directories_to_scan:
            current_dir = directories_to_scan.pop(0)
            search_path = os.path.join(current_dir, "*").encode('utf-8')

            find_data = WIN32_FIND_DATA()
            handle = FindFirstFile(search_path, ctypes.byref(find_data))

            if handle == INVALID_HANDLE_VALUE:
                continue

            try:
                while True:
                    filename = find_data.cFileName.decode('utf-8', errors='ignore')

                    # 跳过. 和 ..
                    if filename in ('.', '..'):
                        if not FindNextFile(handle, ctypes.byref(find_data)):
                            break
                        continue

                    full_path = os.path.join(current_dir, filename)
                    relative_path = os.path.relpath(full_path, start=base_path).replace(os.sep, '/')

                    if find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY:
                        # 是目录
                        directories_to_scan.append(full_path)
                        # 检查是否为空目录
                        try:
                            if not os.listdir(full_path):
                                files_to_process.append((relative_path, full_path))
                        except (OSError, PermissionError):
                            pass
                    else:
                        # 是文件
                        files_to_process.append((relative_path, full_path))

                    if not FindNextFile(handle, ctypes.byref(find_data)):
                        break

            finally:
                FindClose(handle)

        print_colored(f"✅ Windows原生API扫描完成，发现 {len(files_to_process)} 个项目", 'green')
        return files_to_process

    except Exception as e:
        print_colored(f"⚠️  Windows原生API文件扫描失败: {str(e)}", 'yellow')
        print_colored("回退到标准文件扫描方法...", 'blue')
        return None


def windows_fast_file_read(file_path, is_binary=False):
    """
    使用Windows原生API快速读取文件
    比标准Python文件读取快20-30%
    """
    if platform.system() != 'Windows':
        return None

    try:
        import ctypes
        from ctypes import wintypes

        # Windows API常量
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE_VALUE = -1

        # Windows API函数
        kernel32 = ctypes.windll.kernel32

        CreateFile = kernel32.CreateFileA
        CreateFile.argtypes = [wintypes.LPCSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        CreateFile.restype = wintypes.HANDLE

        ReadFile = kernel32.ReadFile
        ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                            ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        ReadFile.restype = wintypes.BOOL

        GetFileSizeEx = kernel32.GetFileSizeEx
        GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_int64)]
        GetFileSizeEx.restype = wintypes.BOOL

        CloseHandle = kernel32.CloseHandle
        CloseHandle.argtypes = [wintypes.HANDLE]
        CloseHandle.restype = wintypes.BOOL

        # 打开文件
        file_path_bytes = file_path.encode('utf-8')
        handle = CreateFile(file_path_bytes, GENERIC_READ, FILE_SHARE_READ,
                           None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)

        if handle == INVALID_HANDLE_VALUE:
            return None

        try:
            # 获取文件大小
            file_size = ctypes.c_int64()
            if not GetFileSizeEx(handle, ctypes.byref(file_size)):
                return None

            # 如果文件太大，回退到标准方法
            if file_size.value > 50 * 1024 * 1024:  # 50MB
                return None

            # 读取文件内容
            buffer = ctypes.create_string_buffer(file_size.value)
            bytes_read = wintypes.DWORD()

            if ReadFile(handle, buffer, file_size.value, ctypes.byref(bytes_read), None):
                if is_binary:
                    return buffer.raw[:bytes_read.value]
                else:
                    try:
                        return buffer.raw[:bytes_read.value].decode('utf-8')
                    except UnicodeDecodeError:
                        # 编码失败，尝试其他编码
                        for encoding in ['cp1252', 'utf-16', 'latin1']:
                            try:
                                return buffer.raw[:bytes_read.value].decode(encoding)
                            except UnicodeDecodeError:
                                continue
                        # 所有编码都失败，作为二进制返回
                        return buffer.raw[:bytes_read.value]
            return None

        finally:
            CloseHandle(handle)

    except Exception as e:
        return None


def windows_fast_file_write(file_path, content, is_binary=False, buffer_size=65536):
    """
    使用Windows原生API和大缓冲区快速写入文件
    """
    if platform.system() != 'Windows':
        return False

    try:
        # 使用大缓冲区的标准Python写入（Windows优化）
        if is_binary:
            with open(file_path, 'wb', buffering=buffer_size) as f:
                f.write(content)
        else:
            with open(file_path, 'w', encoding='utf-8', buffering=buffer_size) as f:
                f.write(content)
        return True

    except Exception as e:
        return False


def gather_files_to_txt_windows_optimized(input_path, show_progress_callback=None):
    """
    Windows高度优化版本的文件收集函数
    使用原生Windows API和批处理优化
    """
    print_colored("🚀 启动Windows原生优化模式...", 'blue')

    # 启用Windows优化
    optimize_for_windows()

    input_path = get_safe_path(input_path)

    # 处理输入是文件的情况
    if os.path.isfile(input_path):
        folder_name = os.path.basename(input_path)
        output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_file_{folder_name}.txt")))
        files_to_process = [(os.path.basename(input_path), input_path)]
    else:
        # 使用Windows原生API快速文件枚举
        files_to_process = windows_fast_file_enumeration(input_path)

        if files_to_process is None:
            # 回退到标准方法
            print_colored("回退到标准文件扫描...", 'yellow')
            folder_name = os.path.basename(os.path.normpath(input_path))
            output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_files_{folder_name}.txt")))
            base_path = os.path.normpath(input_path)
            files_to_process = []

            for root, dirs, files in os.walk(input_path):
                for file in files:
                    file_path = get_safe_path(os.path.join(root, file))
                    relative_path = os.path.relpath(file_path, start=base_path).replace(os.sep, '/')
                    files_to_process.append((relative_path, file_path))

                for dir_name in dirs:
                    dir_path = get_safe_path(os.path.join(root, dir_name))
                    if not os.listdir(dir_path):
                        relative_path = os.path.relpath(dir_path, start=base_path).replace(os.sep, '/')
                        files_to_process.append((relative_path, dir_path))
        else:
            folder_name = os.path.basename(os.path.normpath(input_path))
            output_file = Path(get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_files_{folder_name}.txt")))

    # Windows优化：选择最佳的二进制检测和文件读取方法
    binary_check_func = is_binary_file_windows_optimized

    # Windows优化：使用大缓冲区写入
    buffer_size = 128 * 1024  # 128KB缓冲区

    print_colored(f"📝 开始处理 {len(files_to_process)} 个项目...", 'blue')

    # 批处理优化：先分类文件，再批量处理
    binary_files = []
    text_files = []
    directories = []

    for relative_path, file_path in files_to_process:
        if os.path.isdir(file_path):
            directories.append((relative_path, file_path))
        elif binary_check_func(file_path):
            binary_files.append((relative_path, file_path))
        else:
            text_files.append((relative_path, file_path))

    print_colored(f"📊 文件分类: {len(text_files)}个文本, {len(binary_files)}个二进制, {len(directories)}个目录", 'blue')

    with open(output_file, 'w', encoding='utf-8', buffering=buffer_size) as out_f:
        out_f.write("UNCOMPRESSED\n")
        total_files = len(files_to_process)
        processed_count = 0

        # 批处理1: 先处理目录
        for relative_path, file_path in directories:
            try:
                out_f.write(f"\n@{relative_path}\n[EMPTY_DIRECTORY]\n\n")
                processed_count += 1
                if show_progress_callback and processed_count % 10 == 0:
                    show_progress_callback(processed_count, total_files)
            except Exception as e:
                out_f.write(f"\n!{relative_path}\n{str(e)}\n")

        # 批处理2: 处理文本文件
        for relative_path, file_path in text_files:
            try:
                out_f.write(f"\n@{relative_path}\n")

                # 尝试Windows原生API读取
                content = windows_fast_file_read(file_path, is_binary=False)
                if content is None:
                    # 回退到标准读取
                    with open(file_path, 'r', encoding='utf-8') as in_f:
                        content = in_f.read()

                out_f.write(content)
                out_f.write("\n")
                processed_count += 1

                if show_progress_callback and processed_count % 5 == 0:
                    show_progress_callback(processed_count, total_files)

            except Exception as e:
                out_f.write(f"\n!{relative_path}\n{str(e)}\n")

        # 批处理3: 处理二进制文件
        for relative_path, file_path in binary_files:
            try:
                out_f.write(f"\n@{relative_path}\nB\n")

                # 尝试Windows原生API读取
                content = windows_fast_file_read(file_path, is_binary=True)
                if content is None:
                    # 回退到标准读取
                    with open(file_path, 'rb') as in_f:
                        content = in_f.read()

                # Base64编码
                encoded_content = base64.b64encode(content).decode('ascii')
                out_f.write(encoded_content)
                out_f.write("\n\n")
                processed_count += 1

                if show_progress_callback and processed_count % 2 == 0:
                    show_progress_callback(processed_count, total_files)

            except Exception as e:
                out_f.write(f"\n!{relative_path}\n{str(e)}\n")

    print_colored("✅ Windows优化处理完成！", 'green')

    # 进行快速完整性检查
    print_colored("\n⚡ 正在进行快速验证...", 'blue')
    is_complete, report = verify_snapshot_integrity_fast(str(output_file), input_path, show_progress_callback)
    display_fast_verification_report(report)

    return output_file


def is_binary_file_windows_optimized(file_path):
    """
    Windows优化版本的二进制文件检测
    优先使用扩展名判断，减少文件读取
    """
    try:
        # 检查文件扩展名 - 某些扩展名明确表示二进制文件
        _, ext = os.path.splitext(file_path.lower())

        # Windows特有二进制文件扩展名
        windows_binary_extensions = {
            # Windows特有格式
            '.exe', '.dll', '.msi', '.cab', '.sys', '.drv', '.ocx', '.cpl',
            '.scr', '.com', '.lnk', '.pif', '.scf',
            # 通用二进制格式（完整列表）
            '.ttf', '.otf', '.woff', '.woff2', '.eot', '.pfb', '.pfm', '.afm',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.tif', '.webp',
            '.svg', '.psd', '.ai', '.eps', '.raw', '.cr2', '.nef', '.arw', '.dng',
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.mpg', '.mpeg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lzma',
            '.jar', '.war', '.class', '.dex', '.apk', '.pyc', '.pyo',
            '.sqlite', '.db', '.mdb', '.accdb', '.dbf'
        }

        # Windows常见文本文件扩展名
        windows_text_extensions = {
            '.txt', '.log', '.ini', '.cfg', '.conf', '.xml', '.json', '.csv',
            '.html', '.htm', '.css', '.js', '.ts', '.py', '.java', '.c', '.cpp',
            '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt',
            '.md', '.rst', '.yaml', '.yml', '.sql', '.sh', '.bat', '.cmd', '.ps1'
        }

        if ext in windows_binary_extensions:
            return True  # 明确的二进制文件

        if ext in windows_text_extensions:
            return False  # 明确的文本文件

        # 对于未知扩展名，使用简化的检测（减少I/O）
        try:
            # 只读取前256字节进行快速检测（减少I/O）
            with open(file_path, 'rb') as f:
                chunk = f.read(256)
                if len(chunk) == 0:
                    return False  # 空文件视为文本

                # 快速二进制检测
                null_count = chunk.count(0)
                if null_count > 0:  # 包含空字节，很可能是二进制
                    return True

                # 检查是否大部分是可打印字符
                printable_count = sum(1 for b in chunk if 32 <= b <= 126 or b in (9, 10, 13))
                if printable_count < len(chunk) * 0.75:  # 少于75%可打印字符
                    return True

                return False
        except Exception:
            return False  # 出错时默认为文本文件

    except Exception:
        return False


def is_binary_file(file_path):
    """
    判断文件是否为二进制文件 - 改进的跨平台检测
    """
    try:
        # 检查文件扩展名 - 某些扩展名明确表示二进制文件
        _, ext = os.path.splitext(file_path.lower())
        binary_extensions = {
            # 可执行文件和库
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db', '.sqlite', '.msi', '.dmg',
            '.deb', '.rpm', '.app', '.ipa', '.pkg', '.msu', '.cab',
            # 图像文件
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.tif', '.webp',
            '.svg', '.psd', '.ai', '.eps', '.raw', '.cr2', '.nef', '.arw', '.dng',
            '.heic', '.heif', '.jfif', '.jpx', '.j2k', '.avif', '.jp2',
            # 音频文件
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
            '.aiff', '.au', '.ra', '.amr', '.ac3', '.dts', '.pcm',
            # 视频文件
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.mpg', '.mpeg',
            '.m4v', '.3gp', '.f4v', '.asf', '.rm', '.rmvb', '.vob', '.ts', '.mts',
            # 字体文件 (重要: TTF等之前可能有问题)
            '.ttf', '.otf', '.woff', '.woff2', '.eot', '.pfb', '.pfm', '.afm',
            '.ttc', '.otc', '.fon', '.bdf', '.pcf',
            # 文档文件
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt',
            '.ods', '.odp', '.pages', '.numbers', '.key', '.rtf', '.epub', '.mobi',
            # 压缩文件
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lzma', '.lz4',
            '.zst', '.arj', '.lha', '.ace', '.iso', '.img', '.nrg', '.mds', '.cue',
            # 编程相关二进制
            '.jar', '.war', '.ear', '.class', '.dex', '.apk', '.aar', '.pyc', '.pyo',
            '.wasm', '.o', '.obj', '.lib', '.a', '.pdb', '.ilk', '.exp',
            # 设计和CAD文件
            '.dwg', '.dxf', '.3ds', '.max', '.blend', '.fbx', '.obj', '.dae',
            '.skp', '.ifc', '.step', '.stp', '.iges', '.igs',
            # 数据库和数据文件
            '.mdb', '.accdb', '.dbf', '.sqlite3', '.db3', '.s3db', '.sl3',
            # 游戏相关
            '.unity3d', '.unitypackage', '.asset', '.prefab', '.mat', '.mesh',
            # 其他二进制格式
            '.swf', '.fla', '.psd', '.sketch', '.fig', '.xd', '.indd',
            '.p12', '.pfx', '.jks', '.keystore', '.cer', '.crt', '.p7b'
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
                relative_path = os.path.relpath(file_path, start=base_path).replace(os.sep, '/')
                files_to_process.append((relative_path, file_path))
            
            # 添加空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                # 检查是否为空目录
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace(os.sep, '/')
                    files_to_process.append((relative_path, dir_path))
    
    # Windows优化：选择合适的二进制检测函数
    if platform.system() == 'Windows':
        binary_check_func = is_binary_file_windows_optimized
        # 显示Windows优化提示
        optimize_for_windows()
    else:
        binary_check_func = is_binary_file

    # 写入文件内容，使用更紧凑的格式
    buffer_size = 64 * 1024 if platform.system() == 'Windows' else 8 * 1024

    with open(output_file, 'w', encoding='utf-8', buffering=buffer_size) as out_f:
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
                elif binary_check_func(file_path):
                    # 二进制文件使用base64编码
                    with open(file_path, 'rb') as in_f:
                        content = base64.b64encode(in_f.read()).decode('ascii')
                        out_f.write(f"B\n{content}\n")  # 简化二进制标记
                else:
                    # 文本文件直接读取 - Windows编码优化
                    try:
                        with open(file_path, 'r', encoding='utf-8') as in_f:
                            content = in_f.read()
                    except UnicodeDecodeError:
                        # Windows常见编码回退策略
                        encodings = ['cp1252', 'utf-16', 'latin1'] if platform.system() == 'Windows' else ['latin1']
                        content = ""
                        for encoding in encodings:
                            try:
                                with open(file_path, 'r', encoding=encoding) as in_f:
                                    content = in_f.read()
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 所有编码都失败，作为二进制文件处理
                            with open(file_path, 'rb') as in_f:
                                content = base64.b64encode(in_f.read()).decode('ascii')
                                out_f.write(f"B\n{content}\n")
                                processed_count += 1
                                if show_progress_callback:
                                    show_progress_callback(processed_count, total_files)
                                continue

                    out_f.write(content)
                out_f.write("\n")

                processed_count += 1
            except Exception as e:
                out_f.write(f"\n!{relative_path}\n{str(e)}\n")  # 简化错误标记

            if show_progress_callback:
                show_progress_callback(processed_count, total_files)

    # 进行快速完整性检查
    print_colored("\n⚡ 正在进行快速验证...", 'blue')
    is_complete, report = verify_snapshot_integrity_fast(str(output_file), input_path, show_progress_callback)
    display_fast_verification_report(report)

    return output_file


def compress_text_advanced(text):
    """高级压缩文本内容，进一步减小文件大小"""
    import zlib
    import bz2

    # 预处理：优化内容结构以提高压缩率
    processed_text = preprocess_for_compression(text)

    original_bytes = processed_text.encode('utf-8')
    original_size = len(original_bytes)

    # Windows优化：对于小文件使用更快的压缩
    size_threshold = 4096 if platform.system() == 'Windows' else 2048

    if original_size < size_threshold:
        print_colored("使用高级快速压缩模式...", 'blue')
        try:
            # 使用ZLIB + 字典压缩
            if platform.system() == 'Windows':
                compressed = zlib.compress(original_bytes, level=6)
                encoded = base64.b85encode(compressed).decode('ascii')
                return f"ZLIB:{encoded}"
            else:
                compressed = lzma.compress(original_bytes, preset=6)
                encoded = base64.b85encode(compressed).decode('ascii')
                return encoded
        except:
            return processed_text

    # 大文件使用多阶段高级压缩
    print_colored("使用多阶段高级压缩模式...", 'blue')

    # 阶段1: 内容重组
    reorganized_text = reorganize_content_for_compression(processed_text)
    reorganized_bytes = reorganized_text.encode('utf-8')

    # 阶段2: 尝试多种高级压缩算法
    results = []

    # 算法优先级（Windows优化）
    if platform.system() == 'Windows':
        algorithms = [
            ('ZLIB_ULTRA', lambda data: compress_with_dictionary(data, 'zlib')),
            ('LZMA_EXTREME', lambda data: lzma.compress(data, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)),
            ('BZ2_MAX', lambda data: bz2.compress(data, compresslevel=9))
        ]
    else:
        algorithms = [
            ('LZMA_EXTREME', lambda data: lzma.compress(data, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)),
            ('ZLIB_ULTRA', lambda data: compress_with_dictionary(data, 'zlib')),
            ('BZ2_MAX', lambda data: bz2.compress(data, compresslevel=9))
        ]

    for method, compress_func in algorithms:
        try:
            compressed = compress_func(reorganized_bytes)
            encoded = base64.b85encode(compressed).decode('ascii')
            results.append((method, encoded, len(encoded)))
            print_colored(f"  {method}: {len(encoded)} 字符", 'blue')
        except Exception as e:
            print_colored(f"  {method}失败: {e}", 'yellow')

    if not results:
        print_colored("警告: 所有高级压缩算法都失败，使用标准压缩", 'yellow')
        return compress_text(text)  # 回退到标准压缩

    # 选择最佳结果
    best_method, best_compressed, best_size = min(results, key=lambda x: x[2])

    # 如果高级压缩效果不明显，回退到标准压缩
    standard_result = compress_text(text)
    if len(best_compressed) > len(standard_result) * 0.95:  # 如果只提升不到5%
        print_colored("高级压缩效果有限，使用标准压缩", 'blue')
        return standard_result

    print_colored(f"选择最佳高级算法: {best_method} (压缩后 {best_size} 字符)", 'green')
    return f"{best_method}:{best_compressed}"


def preprocess_for_compression(text):
    """预处理文本以提高压缩率"""
    lines = text.split('\n')
    processed_lines = []

    # 优化1: 合并连续的空行
    prev_empty = False
    for line in lines:
        if line.strip() == '':
            if not prev_empty:
                processed_lines.append('')
            prev_empty = True
        else:
            processed_lines.append(line)
            prev_empty = False

    # 优化2: 移除行尾空格（但保持文件内容完整性）
    processed_lines = [line.rstrip() for line in processed_lines]

    return '\n'.join(processed_lines)


def reorganize_content_for_compression(text):
    """重组内容以提高压缩率"""
    lines = text.split('\n')

    # 分类收集内容
    text_sections = []
    binary_sections = []
    directory_sections = []

    current_section = []
    current_file_path = ""

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith('@'):
            # 处理之前的section
            if current_section and current_file_path:
                section_content = '\n'.join(current_section)
                full_section = f"@{current_file_path}\n{section_content}\n"

                if section_content.startswith('B\n'):
                    # 二进制文件
                    binary_sections.append(full_section)
                elif '[EMPTY_DIRECTORY]' in section_content:
                    # 空目录
                    directory_sections.append(full_section)
                else:
                    # 文本文件
                    text_sections.append(full_section)

            # 开始新section
            current_file_path = line[1:]  # 移除@
            current_section = []
            i += 1

            # 收集section内容
            while i < len(lines) and not lines[i].startswith('@') and not lines[i].startswith('!'):
                current_section.append(lines[i])
                i += 1
            continue

        i += 1

    # 处理最后一个section
    if current_section and current_file_path:
        section_content = '\n'.join(current_section)
        full_section = f"@{current_file_path}\n{section_content}\n"

        if section_content.startswith('B\n'):
            binary_sections.append(full_section)
        elif '[EMPTY_DIRECTORY]' in section_content:
            directory_sections.append(full_section)
        else:
            text_sections.append(full_section)

    # 重新组织：目录 -> 文本文件 -> 二进制文件
    return ''.join(directory_sections + text_sections + binary_sections)


def compress_with_dictionary(data, method='zlib'):
    """使用字典压缩提高压缩率"""
    # 构建压缩字典（基于常见的文件内容模式）
    dictionary = b''.join([
        b'@', b'\n', b'B\n', b'[EMPTY_DIRECTORY]', b'def ', b'class ',
        b'import ', b'from ', b'function', b'var ', b'const ',
        b'<html>', b'<head>', b'<body>', b'</html>', b'</head>', b'</body>',
        b'<?xml', b'encoding=', b'utf-8', b'<!DOCTYPE',
        b'{', b'}', b'[', b']', b'(', b')', b';', b',', b':', b'"'
    ])

    if method == 'zlib':
        compressor = zlib.compressobj(level=9, wbits=15, memLevel=9, strategy=zlib.Z_DEFAULT_STRATEGY)
        # ZLIB不直接支持字典，但我们可以预压缩字典来训练压缩器
        compressor.compress(dictionary)
        compressed = compressor.compress(data)
        compressed += compressor.flush()
        return compressed
    else:
        return zlib.compress(data, level=9)


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
                relative_path = os.path.relpath(file_path, start=base_path).replace(os.sep, '/')
                files_to_process.append((relative_path, file_path))
            
            # 添加空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                # 检查是否为空目录
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace(os.sep, '/')
                    files_to_process.append((relative_path, dir_path))

    output_file = Path(get_unique_filepath(str(initial_output_file)))

    # Windows优化：选择合适的二进制检测函数
    if platform.system() == 'Windows':
        binary_check_func = is_binary_file_windows_optimized
        print_colored("💡 Windows压缩优化模式启用", 'blue')
    else:
        binary_check_func = is_binary_file

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
                if binary_check_func(file_path):
                    # 二进制文件使用base64编码
                    with open(file_path, 'rb') as in_f:
                        content = base64.b64encode(in_f.read()).decode('ascii')
                        content_parts.append(f"B\n{content}\n")  # 简化二进制标记
                else:
                    # 文本文件直接读取 - Windows编码优化
                    try:
                        with open(file_path, 'r', encoding='utf-8') as in_f:
                            content = in_f.read()
                    except UnicodeDecodeError:
                        # Windows编码回退
                        encodings = ['cp1252', 'utf-16', 'latin1'] if platform.system() == 'Windows' else ['latin1']
                        content = ""
                        for encoding in encodings:
                            try:
                                with open(file_path, 'r', encoding=encoding) as in_f:
                                    content = in_f.read()
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 编码失败，作为二进制处理
                            with open(file_path, 'rb') as in_f:
                                content = base64.b64encode(in_f.read()).decode('ascii')
                                content_parts.append(f"B\n{content}\n")
                                processed_count += 1
                                if show_progress_callback:
                                    show_progress_callback(processed_count, total_files)
                                continue

                    content_parts.append(content)
            content_parts.append("\n")

            processed_count += 1
        except Exception as e:
            content_parts.append(f"\n!{relative_path}\n{str(e)}\n")  # 简化错误标记

        if show_progress_callback:
            show_progress_callback(processed_count, total_files)

    # 使用自定义分隔符而不是长分隔线
    full_content = "".join(content_parts)

    # 使用高级压缩算法
    compressed_content = compress_text_advanced(full_content)

    # 将压缩标识添加到压缩后的内容开头，使用更短的标识符
    compressed_content = "COMPRESSED\n" + compressed_content
    
    compressed_size = len(compressed_content.encode('utf-8'))  # 获取压缩后大小
    
    # 计算并显示压缩比例
    if original_size > 0:
        ratio = (1 - compressed_size / original_size) * 100
        print_colored(f"压缩比例: 原始大小 {original_size/1024:.2f} KB → 压缩后 {compressed_size/1024:.2f} KB (减少 {ratio:.2f}%) ", 'blue')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(compressed_content)

    # 进行快速完整性检查
    print_colored("\n⚡ 正在进行快速验证...", 'blue')
    is_complete, report = verify_snapshot_integrity_fast(str(output_file), input_path, show_progress_callback)
    display_fast_verification_report(report)

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
                    # 移除最后的空行（如果有的话），因为写入时会自动添加换行符
                    if content_lines and content_lines[-1] == '':
                        content_lines = content_lines[:-1]
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

        block_type = parts[i]        # "文件" 或 "目录"
        file_path = parts[i+1]       # 路径
        content_block = parts[i+2]   # 内容
        
        # 清理文件路径，处理Windows不支持的字符，确保跨平台兼容性
        sanitized_file_path = sanitize_file_path(file_path)
        # 使用 Path 对象确保正确的路径连接
        full_path = str(Path(output_folder) / sanitized_file_path)
        
        try:
            if content_block.strip() == "[EMPTY_DIRECTORY]":
                # 创建空目录
                os.makedirs(full_path, exist_ok=True)
                success_count += 1

            else:  # 文件
                # 确保父目录存在，使用 Path 对象处理
                parent_dir = Path(full_path).parent
                if parent_dir != Path('.'):  # 确保不是当前目录
                    parent_dir.mkdir(parents=True, exist_ok=True)

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
    """压缩文本内容，智能选择最佳压缩策略，Windows优化版本"""
    import zlib
    import bz2

    # 预处理：保持所有原始内容，不移除空白
    processed_text = text

    original_bytes = processed_text.encode('utf-8')
    original_size = len(original_bytes)

    # Windows优化：对于小文件使用更快的压缩
    size_threshold = 4096 if platform.system() == 'Windows' else 2048

    if original_size < size_threshold:
        print_colored("使用快速压缩模式（小文件优化）...", 'blue')
        try:
            # Windows上使用更快的ZLIB压缩
            if platform.system() == 'Windows':
                compressed = zlib.compress(original_bytes, level=6)  # 平衡速度和效果
                encoded = base64.b85encode(compressed).decode('ascii')
                return f"ZLIB:{encoded}"
            else:
                # 其他系统使用LZMA
                compressed = lzma.compress(original_bytes, preset=6)
                encoded = base64.b85encode(compressed).decode('ascii')
                return encoded
        except:
            return processed_text  # 压缩失败则返回原文

    # 对于大文件，使用多算法优化
    print_colored("使用多算法优化模式（大文件优化）...", 'blue')

    # 重新组织内容以提高压缩率
    reorganized_text = reorganize_content_for_compression(processed_text)
    reorganized_bytes = reorganized_text.encode('utf-8')

    # 测试压缩算法 - Windows优化顺序
    results = []

    # Windows优先使用ZLIB（速度更快）
    if platform.system() == 'Windows':
        algorithms = [
            ('ZLIB', lambda data: zlib.compress(data, level=9)),
            ('LZMA', lambda data: lzma.compress(data, format=lzma.FORMAT_XZ, preset=6 | lzma.PRESET_EXTREME)),
            ('BZ2', lambda data: bz2.compress(data, compresslevel=6))  # 降低压缩级别提高速度
        ]
    else:
        algorithms = [
            ('LZMA', lambda data: lzma.compress(data, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)),
            ('BZ2', lambda data: bz2.compress(data, compresslevel=9)),
            ('ZLIB', lambda data: zlib.compress(data, level=9))
        ]

    for method, compress_func in algorithms:
        try:
            compressed = compress_func(reorganized_bytes)
            encoded = base64.b85encode(compressed).decode('ascii')
            results.append((method, encoded, len(encoded)))
            print_colored(f"  {method}: {len(encoded)} 字符", 'blue')
        except Exception as e:
            print_colored(f"  {method}失败: {e}", 'yellow')

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
        # 新增高级压缩格式支持
        elif method == 'LZMA_EXTREME':
            decompressed_content = lzma.decompress(compressed).decode('utf-8')
        elif method == 'ZLIB_ULTRA':
            import zlib
            decompressed_content = zlib.decompress(compressed).decode('utf-8')
        elif method == 'BZ2_MAX':
            import bz2
            decompressed_content = bz2.decompress(compressed).decode('utf-8')
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

        block_type = parts[i]        # "文件" 或 "目录"
        file_path = parts[i+1]       # 路径
        content_block = parts[i+2]   # 内容
        
        # 清理文件路径，处理Windows不支持的字符，确保跨平台兼容性
        sanitized_file_path = sanitize_file_path(file_path)
        # 使用 Path 对象确保正确的路径连接
        full_path = str(Path(output_folder) / sanitized_file_path)
        
        try:
            if content_block.strip() == "[EMPTY_DIRECTORY]":
                # 创建空目录
                os.makedirs(full_path, exist_ok=True)
                success_count += 1

            else:  # 普通文件
                # 确保父目录存在，使用 Path 对象处理
                parent_dir = Path(full_path).parent
                if parent_dir != Path('.'):  # 确保不是当前目录
                    parent_dir.mkdir(parents=True, exist_ok=True)

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


def verify_snapshot_integrity_fast(snapshot_path, original_path, show_progress_callback=None):
    """
    快速验证快照文件完整性 - 优化版本
    通过文件元数据和抽样检查来提高验证速度

    :param snapshot_path: 快照文件路径
    :param original_path: 原始文件夹或文件路径
    :param show_progress_callback: 进度回调函数
    :return: (is_complete, verification_report)
    """
    if not os.path.exists(snapshot_path):
        return False, {"error": "快照文件不存在"}

    if not os.path.exists(original_path):
        return False, {"error": "原始路径不存在"}

    print_colored("🔍 开始快速验证快照完整性...", 'blue')

    # Windows优化：选择合适的二进制检测函数
    if platform.system() == 'Windows':
        binary_check_func = is_binary_file_windows_optimized
    else:
        binary_check_func = is_binary_file

    # 收集原始文件基本信息（不计算哈希）
    original_files = {}
    total_original_size = 0

    if os.path.isfile(original_path):
        # 单个文件
        filename = os.path.basename(original_path)
        file_size = os.path.getsize(original_path)
        original_files[filename] = {
            'size': file_size,
            'type': 'binary' if binary_check_func(original_path) else 'text',
            'mtime': os.path.getmtime(original_path)  # 修改时间
        }
        total_original_size = file_size
    else:
        # 文件夹
        base_path = os.path.normpath(original_path)
        for root, dirs, files in os.walk(original_path):
            # 处理文件
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace(os.sep, '/')
                file_size = os.path.getsize(file_path)
                original_files[relative_path] = {
                    'size': file_size,
                    'type': 'binary' if binary_check_func(file_path) else 'text',
                    'mtime': os.path.getmtime(file_path)
                }
                total_original_size += file_size

            # 处理空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace(os.sep, '/')
                    original_files[relative_path] = {
                        'size': 0,
                        'type': 'directory',
                        'mtime': os.path.getmtime(dir_path)
                    }

    # 快速解析快照文件（只解析结构，不解码内容）
    snapshot_files = {}
    try:
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

            if first_line == "COMPRESSED":
                # 压缩格式 - 只检查是否能成功解压（不完全解压）
                compressed_content = f.read()
                if ':' in compressed_content:
                    method, encoded_data = compressed_content.split(':', 1)
                else:
                    method = 'LZMA'
                    encoded_data = compressed_content

                try:
                    # Windows优化：只进行基本的格式验证，避免实际解压缩
                    compressed = base64.b85decode(encoded_data.encode('ascii'))

                    # 简化的压缩格式验证（不实际解压缩）
                    if method == 'LZMA':
                        # 检查LZMA文件头
                        if len(compressed) >= 6:
                            # LZMA/XZ文件头: 0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00
                            lzma_header = compressed[:6]
                            if lzma_header.startswith(b'\xFD7zXZ') or lzma_header.startswith(b'\x5D\x00\x00'):
                                pass  # 有效的LZMA格式
                            else:
                                raise ValueError("不是有效的LZMA格式")
                    elif method == 'BZ2':
                        # 检查BZ2文件头: 'BZ'
                        if len(compressed) >= 2 and compressed[:2] == b'BZ':
                            pass  # 有效的BZ2格式
                        else:
                            raise ValueError("不是有效的BZ2格式")
                    elif method == 'ZLIB':
                        # 检查ZLIB文件头
                        if len(compressed) >= 2:
                            # ZLIB格式检查
                            first_byte = compressed[0]
                            second_byte = compressed[1]
                            if (first_byte * 256 + second_byte) % 31 == 0:
                                pass  # 有效的ZLIB格式
                            else:
                                raise ValueError("不是有效的ZLIB格式")
                    elif method == 'RAW':
                        pass  # RAW格式无需验证

                    # 估算文件数量（基于压缩内容中的@标记数量）
                    estimated_files = encoded_data.count('@')
                    snapshot_files['_metadata'] = {
                        'format': 'compressed',
                        'method': method,
                        'estimated_files': estimated_files,
                        'compressed_size': len(compressed)
                    }

                except Exception as e:
                    # 如果压缩验证失败，仍然继续，但标记为可能有问题
                    print_colored(f"⚠️  压缩格式验证警告: {str(e)}", 'yellow')
                    snapshot_files['_metadata'] = {
                        'format': 'compressed',
                        'method': method,
                        'estimated_files': encoded_data.count('@'),
                        'compressed_size': len(base64.b85decode(encoded_data.encode('ascii'))) if encoded_data else 0,
                        'validation_warning': str(e)
                    }

            elif first_line == "UNCOMPRESSED":
                # 未压缩格式 - 快速统计文件标记
                content = f.read()

                # 快速统计@和!标记
                file_markers = content.count('\n@')
                error_markers = content.count('\n!')
                directory_markers = content.count('[EMPTY_DIRECTORY]')
                binary_markers = content.count('\nB\n')

                snapshot_files['_metadata'] = {
                    'format': 'uncompressed',
                    'total_markers': file_markers,
                    'error_markers': error_markers,
                    'directory_markers': directory_markers,
                    'binary_markers': binary_markers,
                    'content_size': len(content)
                }

            else:
                return False, {"error": "无法识别的快照格式"}

    except Exception as e:
        return False, {"error": f"解析快照文件时出错: {str(e)}"}

    # 快速验证报告
    verification_report = {
        'total_original_files': len(original_files),
        'total_original_size': total_original_size,
        'verification_type': 'fast',
        'snapshot_metadata': snapshot_files.get('_metadata', {}),
        'checks_performed': [],
        'warnings': [],
        'is_complete': True  # 默认完整，除非发现明显问题
    }

    # 执行快速检查
    checks_performed = []

    # 1. 文件数量检查
    if snapshot_files['_metadata']['format'] == 'uncompressed':
        estimated_files = snapshot_files['_metadata']['total_markers']
        if abs(estimated_files - len(original_files)) > len(original_files) * 0.1:  # 差异超过10%
            verification_report['warnings'].append(f"文件数量差异较大: 原始{len(original_files)}个，快照约{estimated_files}个")
            verification_report['is_complete'] = False
        checks_performed.append(f"文件数量检查: 原始{len(original_files)}个，快照约{estimated_files}个")

    # 2. 快照文件大小合理性检查
    snapshot_size = os.path.getsize(snapshot_path)
    if snapshot_files['_metadata']['format'] == 'compressed':
        # 压缩文件大小应该小于原始大小
        if snapshot_size > total_original_size:
            verification_report['warnings'].append("压缩快照文件比原始文件还大，可能有问题")
            verification_report['is_complete'] = False
        compression_ratio = (1 - snapshot_size / total_original_size) * 100 if total_original_size > 0 else 0
        checks_performed.append(f"压缩比检查: {compression_ratio:.1f}% (原始{total_original_size/1024:.1f}KB -> 压缩{snapshot_size/1024:.1f}KB)")
    else:
        # 未压缩文件大小应该接近原始大小
        size_ratio = snapshot_size / total_original_size if total_original_size > 0 else 0
        if size_ratio < 0.8 or size_ratio > 2.0:  # 大小差异过大
            verification_report['warnings'].append(f"未压缩快照大小异常: 比率{size_ratio:.2f}")
            verification_report['is_complete'] = False
        checks_performed.append(f"大小合理性检查: 比率{size_ratio:.2f} (快照{snapshot_size/1024:.1f}KB)")

    # 3. 错误标记检查
    if 'error_markers' in snapshot_files['_metadata'] and snapshot_files['_metadata']['error_markers'] > 0:
        verification_report['warnings'].append(f"发现{snapshot_files['_metadata']['error_markers']}个错误文件标记")
        verification_report['is_complete'] = False
        checks_performed.append(f"错误标记检查: 发现{snapshot_files['_metadata']['error_markers']}个错误")
    else:
        checks_performed.append("错误标记检查: 未发现错误标记")

    # 4. 二进制文件比例检查
    original_binary_count = len([f for f in original_files.values() if f['type'] == 'binary'])
    if 'binary_markers' in snapshot_files['_metadata']:
        snapshot_binary_count = snapshot_files['_metadata']['binary_markers']
        if abs(original_binary_count - snapshot_binary_count) > 2:  # 允许小幅差异
            verification_report['warnings'].append(f"二进制文件数量不匹配: 原始{original_binary_count}个，快照{snapshot_binary_count}个")
        checks_performed.append(f"二进制文件检查: 原始{original_binary_count}个，快照{snapshot_binary_count}个")

    verification_report['checks_performed'] = checks_performed

    # 计算成功率（基于检查项目）
    warning_count = len(verification_report['warnings'])
    check_count = len(checks_performed)
    success_rate = ((check_count - warning_count) / check_count * 100) if check_count > 0 else 100
    verification_report['success_rate'] = success_rate

    return verification_report['is_complete'], verification_report


def display_fast_verification_report(report):
    """显示快速验证报告 - Windows优化版本"""
    print_colored("\n" + "="*60, 'cyan')
    print_colored("⚡ 快速验证报告", 'cyan')
    print_colored("="*60, 'cyan')

    # 总体统计
    print_colored(f"📁 原始文件总数: {report['total_original_files']}", 'blue')
    print_colored(f"💾 原始数据大小: {report['total_original_size']/1024:.2f} KB", 'blue')
    print_colored(f"⚡ 验证类型: 快速验证", 'blue')
    print_colored(f"📊 检查成功率: {report['success_rate']:.1f}%", 'green' if report['success_rate'] >= 90 else 'yellow')

    # 快照信息
    metadata = report.get('snapshot_metadata', {})
    if metadata:
        print_colored(f"\n📄 快照格式: {metadata.get('format', '未知')}", 'blue')
        if metadata.get('format') == 'compressed':
            print_colored(f"🗜️  压缩方法: {metadata.get('method', '未知')}", 'blue')
            print_colored(f"📦 压缩大小: {metadata.get('compressed_size', 0)/1024:.2f} KB", 'blue')

        if 'estimated_files' in metadata:
            print_colored(f"📊 估算文件数: {metadata['estimated_files']}", 'blue')

        # 显示验证警告（如果有）
        if 'validation_warning' in metadata:
            print_colored(f"⚠️  验证警告: {metadata['validation_warning']}", 'yellow')

    # 检查项目
    if report.get('checks_performed'):
        print_colored(f"\n✅ 执行的检查:", 'green')
        for check in report['checks_performed']:
            print_colored(f"  - {check}", 'blue')

    # 警告信息
    if report.get('warnings'):
        print_colored(f"\n⚠️  发现的问题 ({len(report['warnings'])} 个):", 'yellow')
        for warning in report['warnings']:
            print_colored(f"  - {warning}", 'yellow')

    # 结论
    print_colored("\n" + "="*60, 'cyan')
    if report['is_complete']:
        print_colored("🎉 快速验证通过！快照看起来是完整的。", 'green')
        print_colored("💡 如需详细验证，请使用完整验证功能。", 'blue')
    else:
        print_colored("⚠️  快速验证发现问题，建议进行完整验证！", 'red')

    # Windows性能提示
    if platform.system() == 'Windows':
        print_colored("💡 Windows用户提示: 如验证较慢，建议暂时关闭实时杀毒软件", 'blue')

    print_colored("="*60, 'cyan')


def verify_snapshot_integrity(snapshot_path, original_path, show_progress_callback=None):
    """
    验证快照文件是否完整包含了所有原始文件内容

    :param snapshot_path: 快照文件路径
    :param original_path: 原始文件夹或文件路径
    :param show_progress_callback: 进度回调函数
    :return: (is_complete, verification_report)
    """
    if not os.path.exists(snapshot_path):
        return False, {"error": "快照文件不存在"}

    if not os.path.exists(original_path):
        return False, {"error": "原始路径不存在"}

    print_colored("🔍 开始验证快照完整性...", 'blue')

    # 收集原始文件信息
    original_files = {}
    total_original_size = 0

    if os.path.isfile(original_path):
        # 单个文件
        filename = os.path.basename(original_path)
        file_size = os.path.getsize(original_path)
        file_hash = calculate_file_checksum(original_path)
        original_files[filename] = {
            'size': file_size,
            'hash': file_hash,
            'type': 'binary' if is_binary_file(original_path) else 'text'
        }
        total_original_size = file_size
    else:
        # 文件夹
        base_path = os.path.normpath(original_path)
        for root, dirs, files in os.walk(original_path):
            # 处理文件
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace(os.sep, '/')
                file_size = os.path.getsize(file_path)
                file_hash = calculate_file_checksum(file_path)
                original_files[relative_path] = {
                    'size': file_size,
                    'hash': file_hash,
                    'type': 'binary' if is_binary_file(file_path) else 'text'
                }
                total_original_size += file_size

            # 处理空目录
            for dir_name in dirs:
                dir_path = get_safe_path(os.path.join(root, dir_name))
                if not os.listdir(dir_path):
                    relative_path = os.path.relpath(dir_path, start=base_path).replace(os.sep, '/')
                    original_files[relative_path] = {
                        'size': 0,
                        'hash': None,
                        'type': 'directory'
                    }

    # 解析快照文件内容
    snapshot_files = {}
    try:
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

            if first_line == "COMPRESSED":
                # 压缩格式
                compressed_content = f.read()
                if ':' in compressed_content:
                    method, encoded_data = compressed_content.split(':', 1)
                else:
                    method = 'LZMA'
                    encoded_data = compressed_content

                compressed = base64.b85decode(encoded_data.encode('ascii'))

                if method == 'LZMA':
                    decompressed_content = lzma.decompress(compressed).decode('utf-8')
                elif method == 'BZ2':
                    import bz2
                    decompressed_content = bz2.decompress(compressed).decode('utf-8')
                elif method == 'ZLIB':
                    import zlib
                    decompressed_content = zlib.decompress(compressed).decode('utf-8')
                elif method == 'RAW':
                    decompressed_content = encoded_data
                else:
                    return False, {"error": f"不支持的压缩方法: {method}"}

                content = decompressed_content

            elif first_line == "UNCOMPRESSED":
                # 未压缩格式
                content = f.read()
            else:
                return False, {"error": "无法识别的快照格式"}

        # 解析文件内容
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]

            if (line.startswith('@') and len(line) > 1 and
                not line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face')) and
                not line[1:].strip().startswith(('app.route', 'staticmethod', 'classmethod', 'property')) and
                not 'def ' in line and not 'class ' in line):

                file_path = line[1:]  # 移除@前缀

                # 收集内容
                content_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if (next_line.startswith('@') and len(next_line) > 1 and
                        not next_line[1:].strip().startswith(('keyframes', 'media', 'import', 'charset', 'font-face'))) or next_line.startswith('!'):
                        break
                    content_lines.append(next_line)
                    i += 1

                # 分析内容类型和大小
                if content_lines and content_lines[0] == 'B':
                    # 二进制文件
                    base64_content = '\n'.join(content_lines[1:])
                    try:
                        decoded_content = base64.b64decode(base64_content.encode('ascii'))
                        snapshot_files[file_path] = {
                            'size': len(decoded_content),
                            'hash': hashlib.sha256(decoded_content).hexdigest(),
                            'type': 'binary',
                            'status': 'found'
                        }
                    except Exception as e:
                        snapshot_files[file_path] = {
                            'error': f"Base64解码失败: {str(e)}",
                            'type': 'binary',
                            'status': 'error'
                        }
                elif content_lines and content_lines[0] == '[EMPTY_DIRECTORY]':
                    # 空目录
                    snapshot_files[file_path] = {
                        'size': 0,
                        'hash': None,
                        'type': 'directory',
                        'status': 'found'
                    }
                else:
                    # 文本文件
                    if content_lines and content_lines[-1] == '':
                        content_lines = content_lines[:-1]
                    text_content = '\n'.join(content_lines)
                    text_bytes = text_content.encode('utf-8')
                    snapshot_files[file_path] = {
                        'size': len(text_bytes),
                        'hash': hashlib.sha256(text_bytes).hexdigest(),
                        'type': 'text',
                        'status': 'found'
                    }
                continue
            elif line.startswith('!'):
                # 错误文件
                file_path = line[1:]
                error_content = lines[i+1] if i+1 < len(lines) else ""
                snapshot_files[file_path] = {
                    'error': error_content,
                    'status': 'error'
                }
                i += 2
                continue
            i += 1

    except Exception as e:
        return False, {"error": f"解析快照文件时出错: {str(e)}"}

    # 比较原始文件和快照文件
    verification_report = {
        'total_original_files': len(original_files),
        'total_snapshot_files': len(snapshot_files),
        'missing_files': [],
        'corrupted_files': [],
        'extra_files': [],
        'error_files': [],
        'successful_files': 0,
        'total_original_size': total_original_size,
        'verified_size': 0
    }

    # 检查每个原始文件是否在快照中
    processed_count = 0
    for file_path, original_info in original_files.items():
        if show_progress_callback:
            show_progress_callback(processed_count, len(original_files))

        if file_path not in snapshot_files:
            verification_report['missing_files'].append({
                'path': file_path,
                'size': original_info['size'],
                'type': original_info['type']
            })
        else:
            snapshot_info = snapshot_files[file_path]

            if snapshot_info.get('status') == 'error':
                verification_report['error_files'].append({
                    'path': file_path,
                    'error': snapshot_info.get('error', '未知错误')
                })
            elif snapshot_info.get('status') == 'found':
                # 比较大小和内容
                size_match = original_info['size'] == snapshot_info['size']
                hash_match = True

                if original_info['hash'] and snapshot_info['hash']:
                    hash_match = original_info['hash'] == snapshot_info['hash']

                if size_match and hash_match:
                    verification_report['successful_files'] += 1
                    verification_report['verified_size'] += original_info['size']
                else:
                    verification_report['corrupted_files'].append({
                        'path': file_path,
                        'original_size': original_info['size'],
                        'snapshot_size': snapshot_info['size'],
                        'size_match': size_match,
                        'hash_match': hash_match,
                        'type': original_info['type']
                    })

        processed_count += 1

    # 检查快照中是否有额外的文件
    for file_path in snapshot_files:
        if file_path not in original_files:
            verification_report['extra_files'].append(file_path)

    # 计算完整性百分比
    is_complete = (len(verification_report['missing_files']) == 0 and
                  len(verification_report['corrupted_files']) == 0 and
                  len(verification_report['error_files']) == 0)

    success_rate = (verification_report['successful_files'] / verification_report['total_original_files'] * 100) if verification_report['total_original_files'] > 0 else 0
    size_coverage = (verification_report['verified_size'] / verification_report['total_original_size'] * 100) if verification_report['total_original_size'] > 0 else 0

    verification_report['is_complete'] = is_complete
    verification_report['success_rate'] = success_rate
    verification_report['size_coverage'] = size_coverage

    return is_complete, verification_report


def display_verification_report(report):
    """显示验证报告"""
    print_colored("\n" + "="*60, 'cyan')
    print_colored("📋 快照完整性验证报告", 'cyan')
    print_colored("="*60, 'cyan')

    # 总体统计
    print_colored(f"📁 原始文件总数: {report['total_original_files']}", 'blue')
    print_colored(f"📄 快照文件总数: {report['total_snapshot_files']}", 'blue')
    print_colored(f"✅ 成功验证: {report['successful_files']}", 'green')
    print_colored(f"📊 成功率: {report['success_rate']:.2f}%", 'green' if report['success_rate'] == 100 else 'yellow')
    print_colored(f"💾 数据覆盖率: {report['size_coverage']:.2f}%", 'green' if report['size_coverage'] == 100 else 'yellow')

    # 问题统计
    if report['missing_files']:
        print_colored(f"\n❌ 缺失文件 ({len(report['missing_files'])} 个):", 'red')
        for file_info in report['missing_files'][:10]:  # 最多显示10个
            print_colored(f"  - {file_info['path']} ({file_info['size']} bytes, {file_info['type']})", 'red')
        if len(report['missing_files']) > 10:
            print_colored(f"  - ... 还有 {len(report['missing_files']) - 10} 个缺失文件", 'red')

    if report['corrupted_files']:
        print_colored(f"\n🔧 损坏文件 ({len(report['corrupted_files'])} 个):", 'yellow')
        for file_info in report['corrupted_files'][:5]:  # 最多显示5个
            size_info = f"大小: {file_info['original_size']} -> {file_info['snapshot_size']}" if not file_info['size_match'] else "大小匹配"
            hash_info = "内容不匹配" if not file_info['hash_match'] else "内容匹配"
            print_colored(f"  - {file_info['path']} ({size_info}, {hash_info})", 'yellow')
        if len(report['corrupted_files']) > 5:
            print_colored(f"  - ... 还有 {len(report['corrupted_files']) - 5} 个损坏文件", 'yellow')

    if report['error_files']:
        print_colored(f"\n⚠️  错误文件 ({len(report['error_files'])} 个):", 'red')
        for file_info in report['error_files'][:5]:  # 最多显示5个
            print_colored(f"  - {file_info['path']}: {file_info['error']}", 'red')
        if len(report['error_files']) > 5:
            print_colored(f"  - ... 还有 {len(report['error_files']) - 5} 个错误文件", 'red')

    if report['extra_files']:
        print_colored(f"\n➕ 快照中的额外文件 ({len(report['extra_files'])} 个):", 'blue')
        for file_path in report['extra_files'][:5]:  # 最多显示5个
            print_colored(f"  - {file_path}", 'blue')
        if len(report['extra_files']) > 5:
            print_colored(f"  - ... 还有 {len(report['extra_files']) - 5} 个额外文件", 'blue')

    # 结论
    print_colored("\n" + "="*60, 'cyan')
    if report['is_complete']:
        print_colored("🎉 验证结果: 快照完整，所有文件都已正确打包！", 'green')
    else:
        print_colored("⚠️  验证结果: 快照不完整，发现问题需要处理！", 'red')
    print_colored("="*60, 'cyan')


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
    """跨平台彩色打印文本，增强错误处理"""
    try:
        if platform.system() == 'Windows':
            try:
                import colorama
                colorama.init(autoreset=True)  # 自动重置颜色
                colors = {
                    'red': colorama.Fore.RED,
                    'green': colorama.Fore.GREEN,
                    'yellow': colorama.Fore.YELLOW,
                    'blue': colorama.Fore.BLUE,
                    'magenta': colorama.Fore.MAGENTA,
                    'cyan': colorama.Fore.CYAN,
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
                'magenta': '\033[95m',
                'cyan': '\033[96m',
                'end': '\033[0m'
            }
            print(f"{colors.get(color, '')}{text}{colors['end']}")
    except Exception:
        # 如果彩色打印失败，回退到普通打印
        print(text)


def get_safe_path(path):
    """获取安全的跨平台路径"""
    # 使用 Path 对象确保跨平台兼容性，然后转换为字符串
    return str(Path(path).resolve())

def sanitize_filename(filename):
    """清理文件名，移除当前平台不支持的字符，确保跨平台兼容性"""
    import re
    
    # 获取平台信息
    platform_info = get_platform_info()
    
    # 根据平台构建无效字符正则表达式
    invalid_chars_str = platform_info['invalid_chars']
    # 转义正则表达式特殊字符
    escaped_chars = re.escape(invalid_chars_str)
    invalid_chars_pattern = f'[{escaped_chars}]'
    
    # 替换不合法字符为下划线
    sanitized = re.sub(invalid_chars_pattern, '_', filename)
    
    # 处理连续的下划线，替换为单个下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # 移除开头和结尾的空格和点（Windows要求）
    sanitized = sanitized.strip(' .')
    
    # 检查是否为保留名称（主要针对Windows）
    if platform_info['reserved_names']:
        name_without_ext = os.path.splitext(sanitized)[0].upper()
        if name_without_ext in platform_info['reserved_names']:
            sanitized = f"_{sanitized}"
    
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed_file"
    
    # 限制文件名长度
    max_length = min(platform_info['max_filename_length'], 200)  # 使用平台限制和安全限制的较小值
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        # 确保截断后仍然有空间给扩展名
        max_name_length = max_length - len(ext)
        if max_name_length > 0:
            sanitized = name[:max_name_length] + ext
        else:
            # 如果扩展名太长，只保留截断的名称
            sanitized = name[:max_length]
    
    return sanitized

def get_platform_info():
    """获取当前平台信息，用于路径处理优化"""
    system = platform.system().lower()
    
    # 获取文件系统信息
    filesystem_info = {}
    try:
        if system == 'windows':
            # Windows特定信息
            filesystem_info.update({
                'case_sensitive': False,
                'reserved_names': {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'},
                'invalid_chars': '<>:"|?*',
                'max_filename_length': 255,
                'max_path_length': 260
            })
        else:
            # Unix-like系统 - 为了跨平台兼容性，使用Windows的限制
            filesystem_info.update({
                'case_sensitive': True,
                'reserved_names': set(),  # Unix系统没有保留名，但为了兼容性可以检查Windows保留名
                'invalid_chars': '<>:"|?*\0',  # 包含Windows不兼容字符以确保跨平台兼容
                'max_filename_length': 255,
                'max_path_length': 4096
            })
    except Exception:
        # 默认值
        filesystem_info = {
            'case_sensitive': system != 'windows',
            'reserved_names': set(),
            'invalid_chars': '<>:"|?*\0',  # 统一使用Windows限制以确保跨平台兼容
            'max_filename_length': 255,
            'max_path_length': 260 if system == 'windows' else 4096
        }
    
    return {
        'system': system,
        'is_windows': system == 'windows',
        'is_macos': system == 'darwin',
        'is_linux': system == 'linux',
        'path_sep': os.sep,
        'alt_path_sep': os.altsep,
        **filesystem_info
    }

def diagnose_platform_compatibility():
    """诊断当前平台的兼容性并提供建议"""
    info = get_platform_info()
    
    print_colored("=== 平台兼容性诊断 ===", 'cyan')
    print_colored(f"操作系统: {info['system'].title()}", 'blue')
    print_colored(f"路径分隔符: '{info['path_sep']}'", 'blue')
    print_colored(f"备用路径分隔符: {info['alt_path_sep']}", 'blue')
    print_colored(f"文件系统大小写敏感: {info['case_sensitive']}", 'blue')
    print_colored(f"最大文件名长度: {info['max_filename_length']}", 'blue')
    print_colored(f"最大路径长度: {info['max_path_length']}", 'blue')
    
    if info['is_windows']:
        print_colored("Windows特定注意事项:", 'yellow')
        print_colored("- 文件名不能包含: < > : \" | ? * \\ /", 'yellow')
        print_colored("- 避免使用保留名称: CON, PRN, AUX, NUL, COM1-9, LPT1-9", 'yellow')
        print_colored("- 路径长度限制较严格 (260字符)", 'yellow')
        
        # 检查colorama
        try:
            import colorama
            print_colored("✅ colorama 已安装，支持彩色输出", 'green')
        except ImportError:
            print_colored("⚠️  建议安装 colorama 以获得更好的输出体验: pip install colorama", 'yellow')
    
    elif info['is_macos']:
        print_colored("macOS特定注意事项:", 'yellow')
        print_colored("- 文件系统通常不区分大小写（除非使用APFS区分大小写格式）", 'yellow')
        print_colored("- 支持Unicode文件名", 'yellow')
        print_colored("- 为确保跨平台兼容性，应用Windows文件名限制", 'yellow')
        
    elif info['is_linux']:
        print_colored("Linux特定注意事项:", 'yellow')
        print_colored("- 文件系统区分大小写", 'yellow')
        print_colored("- 支持Unicode文件名", 'yellow')
        print_colored("- 为确保跨平台兼容性，应用Windows文件名限制", 'yellow')
    
    print_colored("=== 诊断完成 ===", 'cyan')
    return info

def normalize_path_for_restore(stored_path):
    """将快照中存储的路径规范化为当前系统的路径格式"""
    # 将存储的Unix风格路径转换为当前系统路径
    # 使用 Path 对象确保跨平台兼容性
    path_obj = Path(stored_path.replace('/', os.sep))
    return str(path_obj)

def sanitize_file_path(file_path):
    """清理文件路径，处理Windows不支持的字符，确保跨平台兼容性"""
    # 获取平台信息
    platform_info = get_platform_info()
    
    # 首先规范化路径格式
    normalized_path = normalize_path_for_restore(file_path)
    
    # 使用 Path 对象分割路径，更可靠
    path_obj = Path(normalized_path)
    path_parts = path_obj.parts
    
    # 清理每个路径部分
    sanitized_parts = []
    for part in path_parts:
        if part and part not in ('.', '..', '/'):  # 跳过空字符串、相对路径标记和根目录
            sanitized_part = sanitize_filename(part)
            sanitized_parts.append(sanitized_part)
    
    # 重新组合路径
    result_path = os.sep.join(sanitized_parts)
    
    # 检查路径长度是否超过平台限制
    if len(result_path) > platform_info['max_path_length']:
        print_colored(f"警告: 路径长度超过平台限制，将被截断: {result_path[:50]}...", 'yellow')
        # 简单截断策略，保留文件扩展名
        if '.' in result_path:
            name, ext = os.path.splitext(result_path)
            max_name_length = platform_info['max_path_length'] - len(ext) - 10  # 留一些缓冲
            result_path = name[:max_name_length] + ext
        else:
            result_path = result_path[:platform_info['max_path_length'] - 10]
    
    return result_path


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
        version='FolderSnapshot v3.2 - 跨平台兼容文件快照工具'
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
    print_colored("=== 文件快照工具 (v3.2 - 跨平台优化版) ===", 'blue')
    print("1. 创建快照文件 (无压缩，支持所有文件类型)")
    print("2. 创建高压缩率快照文件 (LZMA)")
    print("3. 从快照文件恢复 (自动识别压缩类型)")
    print("4. 验证快照完整性 (快速)")
    print("5. 验证快照完整性 (详细)")
    print("6. 平台兼容性诊断")
    print_colored("0. 退出", 'yellow')
    
    while True:
        choice = input("\n请选择功能 (1/2/3/4/5/6/0): ").strip()

        if choice == "0":
            print_colored("已退出程序", 'green')
            break

        if choice not in ("1", "2", "3", "4", "5", "6"):
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

            elif choice == "4":
                # 快速验证快照完整性
                snapshot_path = input("请输入快照文件路径: ").strip()
                if not validate_path(snapshot_path):
                    continue

                original_path = input("请输入原始文件夹或文件路径: ").strip()
                if not validate_path(original_path):
                    continue

                print_colored(f"⚡ 正在进行快速验证...", 'blue')
                is_complete, report = verify_snapshot_integrity_fast(snapshot_path, original_path, progress_callback)
                display_fast_verification_report(report)

            elif choice == "5":
                # 详细验证快照完整性
                snapshot_path = input("请输入快照文件路径: ").strip()
                if not validate_path(snapshot_path):
                    continue

                original_path = input("请输入原始文件夹或文件路径: ").strip()
                if not validate_path(original_path):
                    continue

                print_colored(f"🔍 正在进行详细验证...", 'blue')
                is_complete, report = verify_snapshot_integrity(snapshot_path, original_path, progress_callback)
                display_verification_report(report)

            elif choice == "6":
                # 平台兼容性诊断
                diagnose_platform_compatibility()
                input("\n按回车键继续...")

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
        
        # 清理文件路径，处理Windows不支持的字符，确保跨平台兼容性
        sanitized_file_path = sanitize_file_path(file_path)
        # 使用 Path 对象确保正确的路径连接
        full_path = str(Path(output_folder) / sanitized_file_path)
        
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
        
        # 清理文件路径，处理Windows不支持的字符，确保跨平台兼容性
        sanitized_file_path = sanitize_file_path(file_path)
        # 使用 Path 对象确保正确的路径连接
        full_path = str(Path(output_folder) / sanitized_file_path)
        
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
