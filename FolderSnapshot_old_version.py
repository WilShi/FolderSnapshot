import os
import re
import lzma
import base64
import platform
from pathlib import Path

def get_safe_path(path):
    """获取安全的跨平台路径"""
    path = str(Path(path))
    # 在Windows系统上保持Windows路径格式
    if platform.system() == 'Windows':
        return path
    # 非Windows系统统一使用正斜杠
    return path.replace('\\', '/')

def gather_files_to_txt(input_path, show_progress_callback=None):
    """将文件夹或单个文件内容合并到一个txt文件中"""
    input_path = get_safe_path(input_path)
    
    if os.path.isfile(input_path):
        with open(input_path, 'r', encoding='utf-8') as f:
            file_list = [line.strip() for line in f if line.strip()]
        
        base_name = os.path.basename(input_path)
        output_file = get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_from_list_{base_name}.txt"))
        
        files_to_process = []
        for file_path in file_list:
            if os.path.isfile(file_path):
                relative_path = os.path.basename(file_path)
                files_to_process.append((relative_path, file_path))
    else:
        folder_name = os.path.basename(os.path.normpath(input_path))
        output_file = get_safe_path(os.path.join(os.path.dirname(input_path), f"combined_files_{folder_name}.txt"))
        base_path = os.path.normpath(input_path)
        files_to_process = []
        
        for root, dirs, files in os.walk(input_path):
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace('\\', '/')
                files_to_process.append((relative_path, file_path))
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write("=== SNAPSHOT_FORMAT: UNCOMPRESSED ===\n\n")
        total_files = len(files_to_process)
        for i, (relative_path, file_path) in enumerate(files_to_process):
            try:
                out_f.write(f"=== 文件: {relative_path} ===\n")
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    content = in_f.read()
                    out_f.write(content + "\n")
                out_f.write("\n" + "="*50 + "\n\n")
            except Exception as e:
                out_f.write(f"!!! 读取文件 {relative_path} 时出错: {str(e)} !!!\n\n")
            
            if show_progress_callback:
                show_progress_callback(i + 1, total_files)

    return output_file

def gather_files_to_txt_compressed(input_path, show_progress_callback=None):
    """将文件夹或文件内容在内存中合并并压缩，然后写入一个txt文件"""
    input_path = get_safe_path(input_path)
    
    if os.path.isfile(input_path):
        base_name = os.path.basename(input_path)
        initial_output_file = get_safe_path(os.path.join(os.path.dirname(input_path), f"compressed_{base_name}.txt"))
        files_to_process = [(os.path.basename(input_path), input_path)]
    else:
        folder_name = os.path.basename(os.path.normpath(input_path))
        initial_output_file = get_safe_path(os.path.join(os.path.dirname(input_path), f"compressed_files_{folder_name}.txt"))
        base_path = os.path.normpath(input_path)
        files_to_process = []
        
        for root, dirs, files in os.walk(input_path):
            for file in files:
                file_path = get_safe_path(os.path.join(root, file))
                relative_path = os.path.relpath(file_path, start=base_path).replace('\\', '/')
                files_to_process.append((relative_path, file_path))

    output_file = get_unique_filepath(initial_output_file)

    content_parts = []
    total_files = len(files_to_process)
    original_size = 0
    
    for i, (relative_path, file_path) in enumerate(files_to_process):
        try:
            content_parts.append(f"=== 文件: {relative_path} ===\n")
            original_size += os.path.getsize(file_path)
            with open(file_path, 'r', encoding='utf-8') as in_f:
                content_parts.append(in_f.read() + "\n")
            content_parts.append("\n" + "="*50 + "\n\n")
        except Exception as e:
            content_parts.append(f"!!! 读取文件 {relative_path} 时出错: {str(e)} !!!\n\n")
        
        if show_progress_callback:
            show_progress_callback(i + 1, total_files)

    full_content = "".join(content_parts)
    compressed_content = compress_text(full_content)
    compressed_content = "=== SNAPSHOT_FORMAT: COMPRESSED ===\n\n" + compressed_content
    
    compressed_size = len(compressed_content.encode('utf-8'))
    if original_size > 0:
        ratio = (1 - compressed_size / original_size) * 100
        print_colored(f"压缩比例: 原始大小 {original_size/1024:.2f} KB → 压缩后 {compressed_size/1024:.2f} KB (减少 {ratio:.2f}%)", 'blue')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(compressed_content)
        
    return output_file

def restore_files_from_txt(txt_path, output_folder):
    """从合并的文本文件恢复原始文件"""
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    
    if first_line == "=== SNAPSHOT_FORMAT: COMPRESSED ===":
        restore_files_from_compressed_txt(txt_path, output_folder)
        return
    elif first_line == "=== SNAPSHOT_FORMAT: UNCOMPRESSED ===":
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read().split('\n', 1)[1]
        
        os.makedirs(output_folder, exist_ok=True)
        file_blocks = re.split(r'=== 文件: (.+?) ===\n', content)[1:]
        
        total_files = len(file_blocks) // 2
        if total_files == 0:
            print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
            return
    else:
        print_colored("错误: 无法识别的文件格式!", 'red')
        return

    show_progress(0, total_files, "恢复进度:")
    for i in range(0, len(file_blocks), 2):
        file_path = file_blocks[i].strip().replace('\\', '/')
        file_content = file_blocks[i+1].split('\n' + "="*50)[0]
        
        full_path = os.path.abspath(os.path.join(output_folder, file_path))
        full_path = os.path.normpath(full_path).replace('\\', '/')
        
        parent_dir = os.path.dirname(full_path)
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except OSError as e:
                print_colored(f"创建目录失败: {parent_dir} - {str(e)}", 'red')
                continue
        
        try:
            with open(full_path, 'wb') as f:
                f.write(file_content.encode('utf-8'))
        except Exception as e:
            print_colored(f"写入文件失败: {full_path} - {str(e)}", 'red')
        
        show_progress(i // 2 + 1, total_files, "恢复进度:")
    
    print()
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')

def restore_files_from_compressed_txt(txt_path, output_folder):
    """从压缩的文本文件恢复原始文件"""
    if not os.path.isfile(txt_path):
        print_colored("错误: 输入的路径不是有效的文本文件!", 'red')
        return

    print("正在读取并解压缩文件...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line != "=== SNAPSHOT_FORMAT: COMPRESSED ===":
            print_colored("错误: 文件格式不正确!", 'red')
            return
        f.readline()
        compressed_content = f.read()
    
    try:
        compressed = base64.b85decode(compressed_content.encode('utf-8'))
        decompressed_content = lzma.decompress(compressed).decode('utf-8')
        
        compressed_size = len(compressed_content.encode('utf-8'))
        original_size = len(decompressed_content.encode('utf-8'))
        if compressed_size > 0:
            ratio = (original_size / compressed_size) * 100
            print_colored(f"解压比例: 压缩文件 {compressed_size/1024:.2f} KB → 解压后 {original_size/1024:.2f} KB (原始大小的 {ratio:.2f}%)", 'blue')
            
    except Exception as e:
        print_colored(f"解压缩失败: {str(e)}", 'red')
        return
    
    os.makedirs(output_folder, exist_ok=True)
    file_blocks = re.split(r'=== 文件: (.+?) ===\n', decompressed_content)[1:]
    
    total_files = len(file_blocks) // 2
    if total_files == 0:
        print_colored("警告: 未在文件中找到任何有效的文件块。", 'yellow')
        return

    show_progress(0, total_files, "恢复进度:")
    for i in range(0, len(file_blocks), 2):
        file_path = file_blocks[i].strip().replace('\\', '/')
        file_content = file_blocks[i+1].split('\n' + "="*50)[0]
        
        full_path = os.path.abspath(os.path.join(output_folder, file_path))
        full_path = os.path.normpath(full_path).replace('\\', '/')
        
        parent_dir = os.path.dirname(full_path)
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except OSError as e:
                print_colored(f"创建目录失败: {parent_dir} - {str(e)}", 'red')
                continue
        
        try:
            with open(full_path, 'wb') as f:
                f.write(file_content.encode('utf-8'))
        except Exception as e:
            print_colored(f"写入文件失败: {full_path} - {str(e)}", 'red')
        
        show_progress(i // 2 + 1, total_files, "恢复进度:")
    
    print()
    print_colored(f"文件已从 {txt_path} 恢复到 {output_folder}", 'green')

def compress_text(text):
    """压缩文本内容"""
    compressed = lzma.compress(text.encode('utf-8'))
    return base64.b85encode(compressed).decode('utf-8')

def get_unique_filepath(filepath):
    """如果文件路径已存在，则在扩展名前附加'_<数字>'以创建唯一路径"""
    if not os.path.exists(filepath):
        return filepath
    
    directory, filename = os.path.split(filepath)
    name, extension = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_name = f"{name}_{counter}{extension}"
        new_filepath = os.path.join(directory, new_name)
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

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
            print(text)
    else:
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'end': '\033[0m'
        }
        print(f"{colors.get(color, '')}{text}{colors['end']}")

def validate_path(path):
    """验证路径是否存在"""
    if not os.path.exists(path):
        print_colored(f"错误: 路径 '{path}' 不存在", 'red')
        return False
    return True

def show_progress(current, total, prefix=""):
    """显示进度条"""
    percent = int(current * 100 / total) if total > 0 else 0
    bar_length = 50
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r{prefix} [{bar}] {percent}%", end='')
    if current == total:
        print()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        try:
            import colorama
        except ImportError:
            print("检测到Windows系统，建议安装colorama以获得更好的彩色输出支持")
            print("可以通过运行: pip install colorama 来安装")
    
    print_colored("=== 文件快照工具 (v2.0 优化版) ===", 'blue')
    print("1. 合并文件夹/文件内容到文本文件")
    print("2. 合并并压缩文件夹/文件内容 (更高压缩率)")
    print("3. 从快照文件恢复原始文件")
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
                restore_files_from_txt(txt_path, output_folder)

        except Exception as e:
            print_colored(f"\n发生严重错误: {str(e)}", 'red')
            continue

