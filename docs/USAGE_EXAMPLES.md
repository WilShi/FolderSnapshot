# FolderSnapshot 使用示例

## 🚀 命令行模式 (新增功能)

### 基本用法

```bash
# 查看帮助
python3 FolderSnapshot.py --help

# 查看版本
python3 FolderSnapshot.py --version
```

### 创建快照

```bash
# 创建压缩快照 (推荐，节省空间) - 自动生成带时间戳的文件名
python3 FolderSnapshot.py --type compress --input /path/to/folder

# 创建无压缩快照 (快速，但文件较大)
python3 FolderSnapshot.py --type snapshot --input /path/to/folder

# 指定完整输出文件路径
python3 FolderSnapshot.py --type compress --input /path/to/folder --output /backups/my_backup.txt

# 输出到指定目录 (自动生成文件名)
python3 FolderSnapshot.py --type compress --input /path/to/folder --output /backups/

# 静默模式 (不显示进度条)
python3 FolderSnapshot.py --type compress --input /path/to/folder --quiet
```

### 恢复快照

```bash
# 恢复快照到指定目录
python3 FolderSnapshot.py --type restore --input backup.txt --output /restore/path

# 静默恢复
python3 FolderSnapshot.py --type restore --input backup.txt --output /restore/path --quiet
```

## 📱 交互式模式 (原有功能)

```bash
# 启动交互式界面
python3 FolderSnapshot.py
```

然后按照菜单提示操作：
1. 创建快照文件 (无压缩)
2. 创建高压缩率快照文件 (LZMA)
3. 从快照文件恢复
0. 退出

## 🎯 实际使用场景

### 1. 项目代码备份

```bash
# 备份整个项目
python3 FolderSnapshot.py --type compress --input ~/Projects/MyApp --output ~/Backups/MyApp_$(date +%Y%m%d).txt

# 恢复项目
python3 FolderSnapshot.py --type restore --input ~/Backups/MyApp_20240123.txt --output ~/Projects/MyApp_Restored
```

### 2. 配置文件备份

```bash
# 备份系统配置
python3 FolderSnapshot.py --type compress --input ~/.config --output ~/Backups/config_backup.txt

# 恢复配置
python3 FolderSnapshot.py --type restore --input ~/Backups/config_backup.txt --output ~/.config_restored
```

### 3. 文档归档

```bash
# 压缩文档目录
python3 FolderSnapshot.py --type compress --input ~/Documents/ImportantDocs --output ~/Archives/docs_$(date +%Y%m%d).txt
```

### 4. 批量处理脚本

```bash
#!/bin/bash
# 自动备份脚本

BACKUP_DIR="$HOME/Backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份多个目录
python3 FolderSnapshot.py --type compress --input "$HOME/Projects" --output "$BACKUP_DIR/projects_$DATE.txt" --quiet
python3 FolderSnapshot.py --type compress --input "$HOME/Documents" --output "$BACKUP_DIR/documents_$DATE.txt" --quiet
python3 FolderSnapshot.py --type compress --input "$HOME/.config" --output "$BACKUP_DIR/config_$DATE.txt" --quiet

echo "备份完成: $BACKUP_DIR"
```

## ⚙️ 参数说明

| 参数 | 短参数 | 说明 | 示例 |
|------|--------|------|------|
| `--type` | `-t` | 操作类型 | `compress`, `snapshot`, `restore` |
| `--input` | `-i` | 输入路径 | `/path/to/source` 或 `backup.txt` |
| `--output` | `-o` | 输出路径 | `backup.txt` 或 `/restore/path` |
| `--quiet` | `-q` | 静默模式 | 不显示进度条 |
| `--version` | `-v` | 版本信息 | 显示工具版本 |

## 🔧 高级用法

### 1. 管道和重定向

```bash
# 将输出重定向到日志文件
python3 FolderSnapshot.py --type compress --input /path/to/folder --quiet > backup.log 2>&1

# 结合其他命令
find /path/to/projects -name "*.py" | head -10 > file_list.txt
python3 FolderSnapshot.py --type compress --input file_list.txt --output python_files.txt
```

### 2. 定时任务 (crontab)

```bash
# 编辑定时任务
crontab -e

# 添加每日备份任务 (每天凌晨2点)
0 2 * * * /usr/bin/python3 /path/to/FolderSnapshot.py --type compress --input /home/user/important --output /backups/daily_$(date +\%Y\%m\%d).txt --quiet
```

### 3. 错误处理

```bash
#!/bin/bash
# 带错误处理的备份脚本

if python3 FolderSnapshot.py --type compress --input "$1" --output "$2" --quiet; then
    echo "✅ 备份成功: $2"
else
    echo "❌ 备份失败: $1"
    exit 1
fi
```

## 💡 最佳实践

1. **使用压缩模式**: `--type compress` 通常能节省 30-90% 的空间
2. **指定输出路径**: 使用 `--output` 参数控制备份文件位置
3. **静默模式**: 在脚本中使用 `--quiet` 避免输出干扰
4. **文件命名**: 在输出文件名中包含日期时间戳
5. **定期测试**: 定期测试恢复功能确保备份可用

## 🚨 注意事项

- 确保有足够的磁盘空间存储备份文件
- 大文件备份可能需要较长时间，请耐心等待
- 恢复时会覆盖目标目录中的同名文件
- 建议在重要操作前先测试小规模数据

## 🔄 从旧版本升级

如果你之前使用的是交互式模式，现在可以：

1. **继续使用交互式模式**: 直接运行 `python3 FolderSnapshot.py`
2. **迁移到命令行模式**: 使用新的 `--type` 参数获得更好的自动化支持

两种模式完全兼容，生成的快照文件格式相同！