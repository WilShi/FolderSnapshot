# FolderSnapshot

一个强大的文件快照工具，可以创建整个目录或单个文件的压缩备份，并可以在之后恢复。

## 功能特点

- **高压缩比**：使用 LZMA 算法实现极高压缩比，平均压缩率超过80%
- **二进制文件支持**：自动检测并正确处理二进制文件
- **跨平台**：支持 Windows、macOS 和 Linux
- **智能路径处理**：清理文件路径以实现跨平台兼容性
- **进度跟踪**：实时进度条显示大文件操作进度
- **错误恢复**：全面的错误处理和恢复机制
- **备份验证**：内置文件完整性检查
- **多种使用模式**：支持交互式和命令行两种使用方式
- **自动文件类型检测**：智能识别文本和二进制文件
- **空目录处理**：支持备份和恢复空目录
- **Unicode支持**：完美支持中文等Unicode字符
- **多编码支持**：自动识别UTF-8、UTF-16、Latin1等编码

## 🚀 新增功能 (v3.2)

- **Windows优化**：针对Windows平台的原生API优化，性能提升20-30%
- **高级压缩算法**：智能选择LZMA、BZ2、ZLIB中最优算法
- **交互式路径自定义**：支持自定义输出路径和文件名
- **快速验证模式**：提供快速完整性检查功能
- **周期性备份工具**：新增自动化备份脚本支持

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
4. 验证快照完整性（快速）
5. 验证快照完整性（详细）
6. 平台兼容性诊断

### 命令行模式

#### 创建快照

```bash
# 创建压缩快照 (推荐，节省空间)
python FolderSnapshot.py --type compress --input /path/to/folder

# 创建无压缩快照 (快速，但文件较大)
python FolderSnapshot.py --type snapshot --input /path/to/folder

# 指定输出文件
python FolderSnapshot.py --type compress --input /path/to/folder --output backup.txt

# 指定输出目录 (自动生成文件名)
python FolderSnapshot.py --type compress --input /path/to/folder --output /backups/

# 静默模式（不显示进度条）
python FolderSnapshot.py --type compress --input /path/to/folder --quiet
```

#### 恢复快照

```bash
# 从快照恢复文件
python FolderSnapshot.py --type restore --input snapshot.txt --output /restore/path

# 静默恢复
python FolderSnapshot.py --type restore --input snapshot.txt --output /restore/path --quiet
```

#### 查看帮助和版本

```bash
# 查看帮助
python FolderSnapshot.py --help

# 查看版本
python FolderSnapshot.py --version
```

## 周期性备份工具

项目包含自动化备份脚本，支持定期备份任务：

```bash
# 添加备份源
python scripts/periodic_backup.py add /path/to/project --name my_project

# 创建备份
python scripts/periodic_backup.py backup

# 列出备份
python scripts/periodic_backup.py backups

# 恢复备份
python scripts/periodic_backup.py restore backup_file.txt /restore/destination
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

### 压缩算法

- **LZMA**：最高压缩率，适合文本文件
- **BZ2**：平衡压缩率和速度
- **ZLIB**：快速压缩，适合小文件
- **智能选择**：自动选择最佳算法

## 性能表现

- **最佳压缩率**：84.63% (大型Java项目)
- **处理速度**：8.5MB数据压缩时间约30秒
- **小文件优化**：<2KB文件使用快速压缩模式
- **大文件优化**：≥2KB文件使用多算法优化模式
- **Windows优化**：使用原生API提升20-30%性能

## 📋 支持的文件类型

- **文本文件**：.txt, .py, .java, .js, .html, .css, .json, .xml等
- **配置文件**：.ini, .cfg, .conf, .properties等
- **二进制文件**：.exe, .dll, .jpg, .png, .pdf, .zip等 (自动base64编码)
- **文档文件**：.doc, .docx, .pdf, .md等
- **空目录**：完全支持空目录的备份和恢复

## 最佳实践

1. **使用压缩模式**：`--type compress` 通常能节省 30-90% 的空间
2. **指定输出路径**：使用 `--output` 参数控制备份文件位置
3. **静默模式**：在脚本中使用 `--quiet` 避免输出干扰
4. **文件命名**：在输出文件名中包含日期时间戳
5. **定期测试**：定期测试恢复功能确保备份可用

## 许可证

本项目基于 MIT 许可证授权。