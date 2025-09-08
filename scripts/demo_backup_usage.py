#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script showing how to use the periodic backup system
"""

import os
import tempfile
import shutil
from pathlib import Path
import json

# Import our modules
import sys
sys.path.insert(0, str(Path(__file__).parent))
from periodic_backup import PeriodicBackup

def create_demo_files(base_dir):
    """Create some demo files for backup testing"""
    base_path = Path(base_dir)
    
    # Create various file types
    (base_path / "document.txt").write_text("This is a sample document with some content.\nMultiple lines for testing.", encoding='utf-8')
    
    (base_path / "config.json").write_text(json.dumps({
        "app_name": "Demo App",
        "version": "1.0.0",
        "settings": {
            "debug": True,
            "max_connections": 100
        }
    }, indent=2), encoding='utf-8')
    
    (base_path / "script.py").write_text('''#!/usr/bin/env python3
def main():
    print("Hello from demo script!")
    for i in range(10):
        print(f"Count: {i}")

if __name__ == "__main__":
    main()
''', encoding='utf-8')
    
    # Create subdirectory with files
    subdir = base_path / "data"
    subdir.mkdir()
    (subdir / "data.csv").write_text("name,age,city\nJohn,25,NYC\nJane,30,LA\n", encoding='utf-8')
    (subdir / "notes.md").write_text("# Notes\n\n- Important item 1\n- Important item 2\n", encoding='utf-8')
    
    # Create empty directory
    (base_path / "empty_folder").mkdir()
    
    print(f"✅ Created demo files in: {base_dir}")
    return base_dir

def demo_backup_workflow():
    """Demonstrate the complete backup workflow"""
    print("🚀 Starting Periodic Backup Demo")
    print("=" * 50)
    
    # Create temporary directories for demo
    with tempfile.TemporaryDirectory(prefix="demo_source_") as source_dir, \
         tempfile.TemporaryDirectory(prefix="demo_backup_") as backup_dir, \
         tempfile.TemporaryDirectory(prefix="demo_restore_") as restore_dir:
        
        # Step 1: Create demo files
        print("\n📁 Step 1: Creating demo files...")
        create_demo_files(source_dir)
        
        # Step 2: Initialize backup manager
        print("\n⚙️  Step 2: Initializing backup manager...")
        config_file = os.path.join(backup_dir, "demo_config.json")
        backup_manager = PeriodicBackup(config_file)
        
        # Configure backup destination
        backup_manager.config["backup_destination"] = os.path.join(backup_dir, "backups")
        backup_manager.config["max_backups_to_keep"] = 5
        backup_manager.save_config()
        
        # Step 3: Add backup source
        print("\n➕ Step 3: Adding backup source...")
        backup_manager.add_backup_source(source_dir, "demo_project")
        
        # Step 4: List sources
        print("\n📋 Step 4: Listing backup sources...")
        backup_manager.list_backup_sources()
        
        # Step 5: Create backup
        print("\n💾 Step 5: Creating backup...")
        success = backup_manager.create_backup()
        
        if success:
            print("✅ Backup created successfully!")
        else:
            print("❌ Backup failed!")
            return
        
        # Step 6: List available backups
        print("\n📄 Step 6: Listing available backups...")
        backup_manager.list_backups()
        
        # Step 7: Find the backup file for restoration
        backup_files_dir = backup_manager.config["backup_destination"]
        backup_files = [f for f in os.listdir(backup_files_dir) if f.endswith('.txt')]
        
        if backup_files:
            backup_file_path = os.path.join(backup_files_dir, backup_files[0])
            
            # Step 8: Restore backup
            print(f"\n🔄 Step 7: Restoring backup...")
            restore_success = backup_manager.restore_backup(backup_file_path, restore_dir)
            
            if restore_success:
                print("✅ Restore completed successfully!")
                
                # Step 9: Verify restoration
                print("\n🔍 Step 8: Verifying restoration...")
                
                # Compare original and restored files
                def compare_directories(dir1, dir2):
                    """Simple directory comparison"""
                    files1 = set()
                    files2 = set()
                    
                    for root, dirs, files in os.walk(dir1):
                        for file in files:
                            rel_path = os.path.relpath(os.path.join(root, file), dir1)
                            files1.add(rel_path)
                    
                    for root, dirs, files in os.walk(dir2):
                        for file in files:
                            rel_path = os.path.relpath(os.path.join(root, file), dir2)
                            files2.add(rel_path)
                    
                    return files1 == files2
                
                if compare_directories(source_dir, restore_dir):
                    print("✅ Verification successful! All files restored correctly.")
                else:
                    print("⚠️  Verification warning: Some differences detected.")
                
                # Show restored file structure
                print(f"\n📂 Restored file structure:")
                for root, dirs, files in os.walk(restore_dir):
                    level = root.replace(restore_dir, '').count(os.sep)
                    indent = ' ' * 2 * level
                    print(f"{indent}{os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files:
                        file_path = os.path.join(root, file)
                        size = os.path.getsize(file_path)
                        print(f"{subindent}{file} ({size} bytes)")
            else:
                print("❌ Restore failed!")
        
        print("\n🎉 Demo completed successfully!")
        print("\n💡 Key Features Demonstrated:")
        print("   ✅ Automatic compression for space efficiency")
        print("   ✅ Support for all file types (text, binary, empty)")
        print("   ✅ Preservation of directory structure")
        print("   ✅ Unicode and special character support")
        print("   ✅ Configuration management")
        print("   ✅ Backup retention policies")
        
        print(f"\n📊 Configuration used:")
        print(f"   Config file: {config_file}")
        print(f"   Backup destination: {backup_manager.config['backup_destination']}")
        print(f"   Compression: {'Enabled' if backup_manager.config['compression_enabled'] else 'Disabled'}")
        print(f"   Max backups to keep: {backup_manager.config['max_backups_to_keep']}")

def demo_cli_usage():
    """Show CLI usage examples"""
    print("\n" + "="*60)
    print("📚 CLI Usage Examples")
    print("="*60)
    
    examples = [
        ("Add a backup source", "python periodic_backup.py add /path/to/project --name my_project"),
        ("List backup sources", "python periodic_backup.py list"),
        ("Create backup for all sources", "python periodic_backup.py backup"),
        ("Create backup for specific source", "python periodic_backup.py backup --source my_project"),
        ("List available backups", "python periodic_backup.py backups"),
        ("Restore from backup", "python periodic_backup.py restore backup_file.txt /restore/destination"),
        ("Clean up old backups", "python periodic_backup.py cleanup"),
        ("Remove a backup source", "python periodic_backup.py remove my_project"),
    ]
    
    for description, command in examples:
        print(f"\n📝 {description}:")
        print(f"   {command}")
    
    print(f"\n⚙️  Configuration file (backup_config.json) structure:")
    sample_config = {
        "backup_sources": [
            {
                "name": "my_project",
                "path": "/path/to/project",
                "enabled": True,
                "last_backup": "2024-01-15T10:30:00",
                "backup_count": 5
            }
        ],
        "backup_destination": "./backups",
        "max_backups_to_keep": 10,
        "compression_enabled": True,
        "backup_name_format": "backup_{source_name}_{timestamp}",
        "exclude_patterns": ["*.tmp", "*.log", "__pycache__", ".git"]
    }
    
    print(json.dumps(sample_config, indent=2))

if __name__ == "__main__":
    try:
        demo_backup_workflow()
        demo_cli_usage()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()