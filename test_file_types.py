#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件类型兼容性的脚本
验证FolderSnapshot工具对各种文件类型的处理能力
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加当前目录到Python路径，以便导入FolderSnapshot模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from FolderSnapshot import (
        gather_files_to_txt,
        gather_files_to_txt_compressed,
        is_binary_file,
        verify_snapshot_integrity,
        display_verification_report,
        print_colored
    )
except ImportError as e:
    print(f"无法导入FolderSnapshot模块: {e}")
    sys.exit(1)


def create_test_files(test_dir):
    """创建各种类型的测试文件"""
    test_files = []

    # 文本文件
    text_files = {
        'test.txt': 'This is a simple text file.\n这是一个简单的文本文件。\n',
        'test.py': '#!/usr/bin/env python3\nprint("Hello, World!")\n',
        'test.js': 'console.log("Hello, World!");\n',
        'test.md': '# Test Markdown\n这是一个测试markdown文件。\n',
        'test.json': '{"name": "test", "value": 123, "unicode": "测试"}\n',
        'test.xml': '<?xml version="1.0" encoding="UTF-8"?>\n<root><item>测试</item></root>\n',
        'test.csv': 'name,value,description\ntest,123,测试项目\n'
    }

    for filename, content in text_files.items():
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        test_files.append((filename, 'text', len(content.encode('utf-8'))))

    # 创建一些"假"二进制文件（小的二进制数据）
    binary_files = {
        'test.ttf': b'\x00\x01\x00\x00\x00\x0F\x00\x80\x00\x03\x00p' + b'FAKE_TTF_DATA' * 10,
        'test.jpg': b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'FAKE_JPEG_DATA' * 20,
        'test.png': b'\x89PNG\r\n\x1A\n\x00\x00\x00\rIHDR' + b'FAKE_PNG_DATA' * 15,
        'test.pdf': b'%PDF-1.4\n%' + b'\xE2\xE3\xCF\xD3' + b'FAKE_PDF_DATA' * 25,
        'test.zip': b'PK\x03\x04\x14\x00\x00\x00\x08\x00' + b'FAKE_ZIP_DATA' * 30,
        'test.exe': b'MZ\x90\x00\x03\x00\x00\x00\x04\x00' + b'FAKE_EXE_DATA' * 35,
        'test.woff': b'wOFF\x00\x01\x00\x00' + b'FAKE_WOFF_DATA' * 12,
        'test.mp3': b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'FAKE_MP3_DATA' * 40
    }

    for filename, content in binary_files.items():
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        test_files.append((filename, 'binary', len(content)))

    # 创建空目录
    empty_dir = os.path.join(test_dir, 'empty_directory')
    os.makedirs(empty_dir, exist_ok=True)
    test_files.append(('empty_directory', 'directory', 0))

    # 创建带有特殊字符的文件名
    special_files = {
        '测试文件.txt': '这是一个包含中文的文件名测试。\n',
        'file with spaces.txt': 'This file has spaces in its name.\n',
        'file-with-dashes.txt': 'This file has dashes in its name.\n'
    }

    for filename, content in special_files.items():
        try:
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            test_files.append((filename, 'text', len(content.encode('utf-8'))))
        except Exception as e:
            print(f"警告: 无法创建文件 {filename}: {e}")

    return test_files


def test_binary_detection():
    """测试二进制文件检测功能"""
    print_colored("\n=== 测试二进制文件检测 ===", 'blue')

    test_cases = [
        ('test.txt', False),
        ('test.py', False),
        ('test.ttf', True),
        ('test.jpg', True),
        ('test.png', True),
        ('test.pdf', True),
        ('test.zip', True),
        ('test.exe', True),
        ('test.woff', True),
        ('test.mp3', True),
        ('test.json', False),
        ('test.md', False)
    ]

    correct_count = 0
    total_count = len(test_cases)

    for filename, expected_binary in test_cases:
        actual_binary = is_binary_file(filename)  # 仅基于扩展名检测

        if actual_binary == expected_binary:
            status = "✅"
            correct_count += 1
        else:
            status = "❌"

        file_type = "二进制" if expected_binary else "文本"
        detected_type = "二进制" if actual_binary else "文本"
        print(f"{status} {filename:20} 期望: {file_type:4} 检测: {detected_type:4}")

    accuracy = (correct_count / total_count) * 100
    print_colored(f"\n检测准确率: {accuracy:.1f}% ({correct_count}/{total_count})",
                 'green' if accuracy >= 90 else 'yellow')


def test_snapshot_creation_and_verification(test_dir):
    """测试快照创建和完整性验证"""
    print_colored("\n=== 测试快照创建和验证 ===", 'blue')

    # 创建无压缩快照
    print("1. 测试无压缩快照...")
    try:
        uncompressed_snapshot = gather_files_to_txt(test_dir)
        print_colored(f"✅ 无压缩快照创建成功: {uncompressed_snapshot}", 'green')

        # 验证完整性
        is_complete, report = verify_snapshot_integrity(str(uncompressed_snapshot), test_dir)
        if is_complete:
            print_colored("✅ 无压缩快照完整性验证通过", 'green')
        else:
            print_colored("❌ 无压缩快照完整性验证失败", 'red')

    except Exception as e:
        print_colored(f"❌ 无压缩快照创建失败: {e}", 'red')

    # 创建压缩快照
    print("\n2. 测试压缩快照...")
    try:
        compressed_snapshot = gather_files_to_txt_compressed(test_dir)
        print_colored(f"✅ 压缩快照创建成功: {compressed_snapshot}", 'green')

        # 验证完整性
        is_complete, report = verify_snapshot_integrity(str(compressed_snapshot), test_dir)
        if is_complete:
            print_colored("✅ 压缩快照完整性验证通过", 'green')
        else:
            print_colored("❌ 压缩快照完整性验证失败", 'red')

    except Exception as e:
        print_colored(f"❌ 压缩快照创建失败: {e}", 'red')


def run_comprehensive_test():
    """运行综合测试"""
    print_colored("🧪 开始文件类型兼容性综合测试", 'cyan')

    # 创建临时测试目录
    with tempfile.TemporaryDirectory(prefix='foldersnapshot_test_') as temp_dir:
        test_dir = os.path.join(temp_dir, 'test_files')
        os.makedirs(test_dir, exist_ok=True)

        print_colored(f"📁 测试目录: {test_dir}", 'blue')

        # 创建测试文件
        print_colored("\n📝 创建测试文件...", 'blue')
        test_files = create_test_files(test_dir)

        total_files = len(test_files)
        text_files = len([f for f in test_files if f[1] == 'text'])
        binary_files = len([f for f in test_files if f[1] == 'binary'])
        directories = len([f for f in test_files if f[1] == 'directory'])
        total_size = sum(f[2] for f in test_files)

        print_colored(f"创建了 {total_files} 个测试项目:", 'green')
        print_colored(f"  - 文本文件: {text_files} 个", 'blue')
        print_colored(f"  - 二进制文件: {binary_files} 个", 'blue')
        print_colored(f"  - 目录: {directories} 个", 'blue')
        print_colored(f"  - 总大小: {total_size} bytes", 'blue')

        # 测试二进制文件检测
        test_binary_detection()

        # 测试快照创建和验证
        test_snapshot_creation_and_verification(test_dir)

    print_colored("\n🎉 综合测试完成！", 'cyan')


if __name__ == "__main__":
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print_colored("\n\n❌ 测试被用户中断", 'yellow')
    except Exception as e:
        print_colored(f"\n\n❌ 测试过程中发生错误: {e}", 'red')
        import traceback
        traceback.print_exc()