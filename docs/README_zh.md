# FolderSnapshot

一个强大的文件快照工具，可以创建整个目录或单个文件的压缩备份，并可以在之后恢复。

## 功能特点

- **高压缩比**：使用 LZMA 算法实现极高压缩比
- **二进制文件支持**：自动检测并正确处理二进制文件
- **跨平台**：支持 Windows、macOS 和 Linux
- **智能路径处理**：清理文件路径以实现跨平台兼容性
- **进度跟踪**：实时进度条显示大文件操作进度
- **错误恢复**：全面的错误处理和恢复机制
- **备份验证**：内置文件完整性检查
- **多种使用模式**：支持交互式和命令行两种使用方式

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/FolderSnapshot.git
cd FolderSnapshot

# 安装依赖（可选，用于增强 Windows 支持）
pip install colorama
```

## 使用方法

### 交互模式

运行以下命令启动交互式界面：

```bash
python FolderSnapshot.py
```

交互模式提供以下功能：
1. 创建快照文件（无压缩，支持所有文件类型）
2. 创建高压缩率快照文件（LZMA）
3. 从快照文件恢复（自动识别压缩类型）

### 命令行模式

#### 创建快照

```bash
# 创建压缩快照
python FolderSnapshot.py --type compress --input /path/to/folder

# 创建未压缩快照
python FolderSnapshot.py --type snapshot --input /path/to/folder

# 指定输出文件
python FolderSnapshot.py --type compress --input /path/to/folder --output backup.txt

# 静默模式（不显示进度条）
python FolderSnapshot.py --type compress --input /path/to/folder --quiet
```

#### 恢复快照

```bash
# 从快照恢复文件
python FolderSnapshot.py --type restore --input snapshot.txt --output /restore/path
```

## 技术细节

### 文件格式

工具支持两种文件格式：

- **未压缩格式**：纯文本格式，易于查看和编辑
- **压缩格式**：使用 LZMA 算法压缩，显著减小文件大小

### 二进制文件处理

工具会自动检测二进制文件并使用 Base64 编码进行存储，确保所有类型的文件都能正确备份和恢复。

### 路径兼容性

为了确保在不同操作系统间的兼容性，工具会自动清理文件路径中的非法字符。

## 许可证

本项目基于 MIT 许可证授权。