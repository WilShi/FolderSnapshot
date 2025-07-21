# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import shutil
from pathlib import Path
import random
import string
import pytest
import filecmp
import json
from unittest.mock import MagicMock

# 将脚本所在的目录添加到 sys.path，以便导入 FolderSnapshot
sys.path.insert(0, str(Path(__file__).parent))
import FolderSnapshot

# ==============================================================================
# Helper Functions & Fixtures
# ==============================================================================

def generate_random_text(length):
    """生成指定长度的随机文本，包含多种字符。"""
    chars = string.ascii_letters + string.digits + string.punctuation + ' \n'
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_bytes(length):
    """生成指定长度的随机二进制数据。"""
    return os.urandom(length)

def create_test_structure(base_dir, num_text=2, num_binary=1, depth=2, special_chars=False):
    """创建一个复杂的目录结构用于测试。"""
    created_paths = []
    base_dir = Path(base_dir)

    def _create_recursive(current_dir, current_depth):
        current_dir.mkdir(parents=True, exist_ok=True)
        created_paths.append(current_dir)

        # 根据 special_chars 标志决定文件名
        text_name_template = "text file_{i}.txt" if not special_chars else "text file {i} (文本).txt"
        binary_name_template = "binary_file_{i}.bin" if not special_chars else "binary file {i} (二进制).bin"
        nested_dir_template = "nested_{d}" if not special_chars else "nested dir {d} (嵌套)"
        
        # 创建文本文件
        for i in range(num_text):
            file_path = current_dir / text_name_template.format(i=i)
            content = generate_random_text(random.randint(50, 512))
            file_path.write_text(content, encoding='utf-8')
            created_paths.append(file_path)

        # 创建二进制文件
        for i in range(num_binary):
            file_path = current_dir / binary_name_template.format(i=i)
            content = generate_random_bytes(random.randint(50, 512))
            file_path.write_bytes(content)
            created_paths.append(file_path)
        
        # 创建一个空子目录
        empty_subdir = current_dir / ("empty_dir" if not special_chars else "empty dir (空)")
        empty_subdir.mkdir(exist_ok=True)
        created_paths.append(empty_subdir)

        # 递归创建嵌套目录
        if current_depth < depth:
            nested_dir = current_dir / nested_dir_template.format(d=current_depth)
            _create_recursive(nested_dir, current_depth + 1)

    _create_recursive(base_dir, 0)
    return created_paths

def compare_dirs(dir1, dir2):
    """递归比较两个目录的内容是否完全一致。"""
    dcmp = filecmp.dircmp(dir1, dir2)
    
    if dcmp.left_only or dcmp.right_only or dcmp.diff_files or dcmp.funny_files:
        print("目录比较发现差异:")
        if dcmp.left_only: print(f"  仅存在于 {dir1}: {dcmp.left_only}")
        if dcmp.right_only: print(f"  仅存在于 {dir2}: {dcmp.right_only}")
        if dcmp.diff_files: print(f"  内容不同的文件: {dcmp.diff_files}")
        if dcmp.funny_files: print(f"  无法比较的文件: {dcmp.funny_files}")
        return False
    
    for sub_dcmp in dcmp.subdirs.values():
        if not compare_dirs(sub_dcmp.left, sub_dcmp.right):
            return False
            
    return True

@pytest.fixture
def temp_test_dir():
    """Pytest fixture，创建一个临时目录用于测试。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def source_dir(temp_test_dir):
    """Fixture，创建一个标准的源目录结构。"""
    src_dir = temp_test_dir / "source"
    create_test_structure(src_dir)
    return src_dir

@pytest.fixture
def special_source_dir(temp_test_dir):
    """Fixture，创建一个包含特殊字符文件名的源目录结构。"""
    src_dir = temp_test_dir / "source_special"
    create_test_structure(src_dir, special_chars=True)
    return src_dir

# ==============================================================================
# Core Functionality Tests
# ==============================================================================

def test_snapshot_and_restore_uncompressed_folder(source_dir, temp_test_dir):
    """测试对文件夹进行非压缩快照的创建和恢复。"""
    print(f"\n--- 测试非压缩文件夹快照: {source_dir} ---")
    snapshot_file = FolderSnapshot.gather_files_to_txt(source_dir)
    assert snapshot_file.exists()
    
    restore_dir = temp_test_dir / "restored_uncompressed"
    FolderSnapshot.restore_files_from_txt(snapshot_file, restore_dir)
    
    assert restore_dir.exists()
    assert compare_dirs(source_dir, restore_dir)
    print("非压缩文件夹快照与恢复成功，目录内容匹配。")

def test_snapshot_and_restore_compressed_folder(source_dir, temp_test_dir):
    """测试对文件夹进行压缩快照的创建和恢复。"""
    print(f"\n--- 测试压缩文件夹快照: {source_dir} ---")
    snapshot_file = FolderSnapshot.gather_files_to_txt_compressed(source_dir)
    assert snapshot_file.exists()
    
    restore_dir = temp_test_dir / "restored_compressed"
    FolderSnapshot.restore_files_from_compressed_txt(snapshot_file, restore_dir)
    
    assert restore_dir.exists()
    assert compare_dirs(source_dir, restore_dir)
    print("压缩文件夹快照与恢复成功，目录内容匹配。")

def test_snapshot_and_restore_single_file(temp_test_dir):
    """测试对单个文件（文本和二进制）进行快照和恢复。"""
    print("\n--- 测试单个文件快照 ---")
    
    # 创建测试文件
    text_file = temp_test_dir / "single_text.txt"
    text_content = generate_random_text(200)
    text_file.write_text(text_content, encoding='utf-8')

    binary_file = temp_test_dir / "single_binary.bin"
    binary_content = generate_random_bytes(200)
    binary_file.write_bytes(binary_content)

    for original_file, original_content in [(text_file, text_content.encode('utf-8')), (binary_file, binary_content)]:
        # 测试非压缩
        snapshot_uncompressed = FolderSnapshot.gather_files_to_txt(original_file)
        restore_dir_uncompressed = temp_test_dir / f"restore_single_uncompressed_{original_file.stem}"
        FolderSnapshot.restore_files_from_txt(snapshot_uncompressed, restore_dir_uncompressed)
        restored_file_uncompressed = restore_dir_uncompressed / original_file.name
        assert restored_file_uncompressed.read_bytes() == original_content

        # 测试压缩
        snapshot_compressed = FolderSnapshot.gather_files_to_txt_compressed(original_file)
        restore_dir_compressed = temp_test_dir / f"restore_single_compressed_{original_file.stem}"
        FolderSnapshot.restore_files_from_compressed_txt(snapshot_compressed, restore_dir_compressed)
        restored_file_compressed = restore_dir_compressed / original_file.name
        assert restored_file_compressed.read_bytes() == original_content
        
    print("单个文件快照与恢复成功。")

# ==============================================================================
# Edge Case Tests
# ==============================================================================

def test_empty_source_directory(temp_test_dir):
    """测试处理空目录的情况。"""
    print("\n--- 测试空目录 ---")
    empty_src_dir = temp_test_dir / "empty_source"
    empty_src_dir.mkdir()

    # 非压缩
    snapshot_uncompressed = FolderSnapshot.gather_files_to_txt(empty_src_dir)
    restore_uncompressed = temp_test_dir / "restored_empty_uncompressed"
    FolderSnapshot.restore_files_from_txt(snapshot_uncompressed, restore_uncompressed)
    assert not any(restore_uncompressed.iterdir())

    # 压缩
    snapshot_compressed = FolderSnapshot.gather_files_to_txt_compressed(empty_src_dir)
    restore_compressed = temp_test_dir / "restored_empty_compressed"
    FolderSnapshot.restore_files_from_compressed_txt(snapshot_compressed, restore_compressed)
    assert not any(restore_compressed.iterdir())
    
    print("空目录处理正确。")

def test_special_filenames(special_source_dir, temp_test_dir):
    """测试包含特殊字符的文件名和目录名。"""
    print("\n--- 测试特殊文件名 ---")
    snapshot_file = FolderSnapshot.gather_files_to_txt_compressed(special_source_dir)
    restore_dir = temp_test_dir / "restored_special"
    FolderSnapshot.restore_files_from_compressed_txt(snapshot_file, restore_dir)
    
    assert restore_dir.exists()
    assert compare_dirs(special_source_dir, restore_dir)
    print("特殊文件名处理成功。")

def test_corrupted_snapshot_file(source_dir, temp_test_dir, capsys):
    """测试恢复函数处理损坏的快照文件的能力。"""
    print("\n--- 测试损坏的快照文件 ---")
    snapshot_file = FolderSnapshot.gather_files_to_txt(source_dir)
    
    # 人为损坏文件（截断）
    corrupted_content = snapshot_file.read_bytes()[:200]
    corrupted_snapshot_file = temp_test_dir / "corrupted.txt"
    corrupted_snapshot_file.write_bytes(corrupted_content)
    
    restore_dir = temp_test_dir / "restore_corrupted"
    FolderSnapshot.restore_files_from_txt(corrupted_snapshot_file, restore_dir)
    
    # 检查是否有警告信息输出
    captured = capsys.readouterr()
    assert "警告" in captured.out or "警告" in captured.err
    print("损坏的快照文件已按预期处理并打印警告。")

# ==============================================================================
# Editor and Utility Tests
# ==============================================================================

def test_restore_from_editor_text(source_dir, temp_test_dir, monkeypatch):
    """通过模拟输入来测试从编辑器恢复的功能。"""
    print("\n--- 测试从编辑器恢复 ---")
    
    # 1. 测试非压缩内容
    snapshot_uncompressed_file = FolderSnapshot.gather_files_to_txt(source_dir)
    uncompressed_content = snapshot_uncompressed_file.read_text('utf-8')
    
    # 模拟 get_text_from_editor 和 input
    monkeypatch.setattr(FolderSnapshot, 'get_text_from_editor', lambda: uncompressed_content)
    restore_dir_editor_uncompressed = temp_test_dir / "restored_editor_uncompressed"
    monkeypatch.setattr('builtins.input', lambda _: str(restore_dir_editor_uncompressed))
    
    FolderSnapshot.restore_from_editor_text()
    assert compare_dirs(source_dir, restore_dir_editor_uncompressed)
    print("从编辑器恢复（非压缩）成功。")

    # 2. 测试压缩内容
    snapshot_compressed_file = FolderSnapshot.gather_files_to_txt_compressed(source_dir)
    compressed_content = snapshot_compressed_file.read_text('utf-8')

    # 模拟 get_text_from_editor 和 input
    monkeypatch.setattr(FolderSnapshot, 'get_text_from_editor', lambda: compressed_content)
    restore_dir_editor_compressed = temp_test_dir / "restored_editor_compressed"
    monkeypatch.setattr('builtins.input', lambda _: str(restore_dir_editor_compressed))

    FolderSnapshot.restore_from_editor_text()
    assert compare_dirs(source_dir, restore_dir_editor_compressed)
    print("从编辑器恢复（压缩）成功。")

def test_progress_callback(source_dir, temp_test_dir):
    """测试进度回调函数是否被调用。"""
    print("\n--- 测试进度回调 ---")
    
    # 计算源目录中的文件和目录总数
    total_paths = sum(1 for _ in source_dir.rglob('*'))
    
    mock_callback = MagicMock()
    
    FolderSnapshot.gather_files_to_txt(source_dir, show_progress_callback=mock_callback)
    
    assert mock_callback.call_count == total_paths
    # 验证最后一次调用的参数
    mock_callback.assert_called_with(total_paths, total_paths)
    print("进度回调函数调用正确。")

def test_get_unique_filepath(temp_test_dir):
    """测试 get_unique_filepath 工具函数。"""
    print("\n--- 测试 get_unique_filepath ---")
    base_path = temp_test_dir / "file.txt"
    
    # 第一次调用，文件不存在
    assert FolderSnapshot.get_unique_filepath(base_path) == base_path
    
    # 创建文件后再次调用
    base_path.touch()
    assert FolderSnapshot.get_unique_filepath(base_path) == temp_test_dir / "file_1.txt"
    
    # 创建_1文件后再次调用
    (temp_test_dir / "file_1.txt").touch()
    assert FolderSnapshot.get_unique_filepath(base_path) == temp_test_dir / "file_2.txt"
    print("get_unique_filepath 功能正确。")