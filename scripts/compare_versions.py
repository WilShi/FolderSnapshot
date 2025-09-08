#!/usr/bin/env python3
"""
对比新旧版本压缩效果的测试脚本
"""

import os
import tempfile
import shutil
from FolderSnapshot import gather_files_to_txt_compressed as new_compress
from FolderSnapshot_old_version import gather_files_to_txt_compressed as old_compress

def create_test_data():
    """创建测试数据"""
    test_dir = tempfile.mkdtemp(prefix="version_compare_")
    
    # 创建一些测试文件
    with open(os.path.join(test_dir, "test1.py"), 'w', encoding='utf-8') as f:
        f.write('''
def hello_world():
    print("Hello, World!")
    return True

def process_data(data):
    result = []
    for item in data:
        if validate_item(item):
            result.append(transform_item(item))
    return result

def validate_item(item):
    return isinstance(item, dict) and 'id' in item

def transform_item(item):
    return {
        'id': item['id'],
        'processed': True
    }
''')
    
    with open(os.path.join(test_dir, "test2.js"), 'w', encoding='utf-8') as f:
        f.write('''
function helloWorld() {
    console.log("Hello, World!");
    return true;
}

function processData(data) {
    const result = [];
    for (const item of data) {
        if (validateItem(item)) {
            result.push(transformItem(item));
        }
    }
    return result;
}

function validateItem(item) {
    return typeof item === 'object' && 'id' in item;
}

function transformItem(item) {
    return {
        id: item.id,
        processed: true
    };
}
''')
    
    with open(os.path.join(test_dir, "config.json"), 'w', encoding='utf-8') as f:
        f.write('''{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "testdb"
  },
  "api": {
    "base_url": "https://api.example.com",
    "timeout": 30
  }
}''')
    
    return test_dir

def compare_compression():
    """对比两个版本的压缩效果"""
    print("=== 新旧版本压缩效果对比 ===\n")
    
    test_dir = create_test_data()
    print(f"测试数据目录: {test_dir}")
    
    try:
        # 计算原始大小
        total_size = 0
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                total_size += os.path.getsize(os.path.join(root, file))
        
        print(f"原始数据大小: {total_size/1024:.2f} KB\n")
        
        # 测试旧版本
        print("1. 测试旧版本压缩...")
        old_file = old_compress(test_dir)
        old_size = os.path.getsize(old_file)
        old_ratio = (1 - old_size / total_size) * 100 if total_size > 0 else 0
        print(f"旧版本压缩后: {old_size/1024:.2f} KB (压缩率: {old_ratio:.2f}%)")
        
        # 测试新版本
        print("\n2. 测试新版本压缩...")
        new_file = new_compress(test_dir)
        new_size = os.path.getsize(new_file)
        new_ratio = (1 - new_size / total_size) * 100 if total_size > 0 else 0
        print(f"新版本压缩后: {new_size/1024:.2f} KB (压缩率: {new_ratio:.2f}%)")
        
        # 对比结果
        print(f"\n📊 对比结果:")
        print(f"   旧版本: {old_size/1024:.2f} KB ({old_ratio:.2f}%)")
        print(f"   新版本: {new_size/1024:.2f} KB ({new_ratio:.2f}%)")
        
        if new_size < old_size:
            improvement = (1 - new_size / old_size) * 100
            print(f"   ✅ 新版本更优，改进了 {improvement:.2f}%")
        elif old_size < new_size:
            regression = (new_size / old_size - 1) * 100
            print(f"   ❌ 新版本较差，退步了 {regression:.2f}%")
        else:
            print(f"   ➖ 两版本效果相同")
        
        # 清理文件
        os.unlink(old_file)
        os.unlink(new_file)
        
    finally:
        shutil.rmtree(test_dir)
        print(f"\n✅ 测试完成")

if __name__ == "__main__":
    compare_compression()