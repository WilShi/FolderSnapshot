#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Periodic Backup Script using FolderSnapshot.py
Designed for automated, scheduled backups with maximum compression
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# Import FolderSnapshot
sys.path.insert(0, str(Path(__file__).parent))
import FolderSnapshot

class PeriodicBackup:
    """Handles periodic backup operations with compression"""
    
    def __init__(self, config_file="backup_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load backup configuration from JSON file"""
        default_config = {
            "backup_sources": [],
            "backup_destination": "./backups",
            "max_backups_to_keep": 10,
            "compression_enabled": True,
            "backup_name_format": "backup_{source_name}_{timestamp}",
            "exclude_patterns": [
                "*.tmp", "*.log", "__pycache__", ".git", 
                "node_modules", ".DS_Store", "Thumbs.db"
            ],
            "notification": {
                "enabled": False,
                "email": "",
                "webhook_url": ""
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"⚠️  Error loading config: {e}. Using defaults.")
        else:
            # Create default config file
            self.save_config(default_config)
            print(f"📝 Created default config file: {self.config_file}")
        
        return default_config
    
    def save_config(self, config=None):
        """Save configuration to JSON file"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def add_backup_source(self, source_path, name=None):
        """Add a new backup source"""
        if not os.path.exists(source_path):
            print(f"❌ Source path does not exist: {source_path}")
            return False
        
        source_path = os.path.abspath(source_path)
        
        if name is None:
            name = os.path.basename(source_path) or "root"
        
        # Check if already exists
        for source in self.config["backup_sources"]:
            if source["path"] == source_path:
                print(f"⚠️  Source already exists: {source_path}")
                return False
        
        self.config["backup_sources"].append({
            "name": name,
            "path": source_path,
            "enabled": True,
            "last_backup": None,
            "backup_count": 0
        })
        
        self.save_config()
        print(f"✅ Added backup source: {name} ({source_path})")
        return True
    
    def remove_backup_source(self, name_or_path):
        """Remove a backup source"""
        original_count = len(self.config["backup_sources"])
        
        self.config["backup_sources"] = [
            source for source in self.config["backup_sources"]
            if source["name"] != name_or_path and source["path"] != name_or_path
        ]
        
        if len(self.config["backup_sources"]) < original_count:
            self.save_config()
            print(f"✅ Removed backup source: {name_or_path}")
            return True
        else:
            print(f"❌ Backup source not found: {name_or_path}")
            return False
    
    def list_backup_sources(self):
        """List all configured backup sources"""
        if not self.config["backup_sources"]:
            print("📝 No backup sources configured.")
            return
        
        print("📋 Configured Backup Sources:")
        print("-" * 60)
        for i, source in enumerate(self.config["backup_sources"], 1):
            status = "✅ Enabled" if source["enabled"] else "❌ Disabled"
            last_backup = source.get("last_backup", "Never")
            if last_backup and last_backup != "Never":
                last_backup = datetime.fromisoformat(last_backup).strftime("%Y-%m-%d %H:%M")
            
            print(f"{i}. {source['name']}")
            print(f"   Path: {source['path']}")
            print(f"   Status: {status}")
            print(f"   Last Backup: {last_backup}")
            print(f"   Backup Count: {source.get('backup_count', 0)}")
            print()
    
    def create_backup(self, source_name=None, force=False):
        """Create backup for specified source or all sources"""
        if not os.path.exists(self.config["backup_destination"]):
            os.makedirs(self.config["backup_destination"], exist_ok=True)
        
        sources_to_backup = []
        
        if source_name:
            # Backup specific source
            source = next((s for s in self.config["backup_sources"] 
                          if s["name"] == source_name), None)
            if not source:
                print(f"❌ Backup source not found: {source_name}")
                return False
            sources_to_backup = [source]
        else:
            # Backup all enabled sources
            sources_to_backup = [s for s in self.config["backup_sources"] if s["enabled"]]
        
        if not sources_to_backup:
            print("📝 No sources to backup.")
            return True
        
        success_count = 0
        total_original_size = 0
        total_backup_size = 0
        
        for source in sources_to_backup:
            try:
                print(f"\n🔄 Creating backup for: {source['name']}")
                
                # Check if source still exists
                if not os.path.exists(source["path"]):
                    print(f"⚠️  Source path no longer exists: {source['path']}")
                    continue
                
                # Generate backup filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = self.config["backup_name_format"].format(
                    source_name=source["name"],
                    timestamp=timestamp
                )
                
                # Calculate original size
                original_size = self.calculate_directory_size(source["path"])
                total_original_size += original_size
                
                # Create backup
                start_time = time.time()
                
                if self.config["compression_enabled"]:
                    backup_file = FolderSnapshot.gather_files_to_txt_compressed(
                        source["path"],
                        show_progress_callback=self.progress_callback
                    )
                else:
                    backup_file = FolderSnapshot.gather_files_to_txt(
                        source["path"],
                        show_progress_callback=self.progress_callback
                    )
                
                backup_time = time.time() - start_time
                
                # Move backup to destination with proper name
                final_backup_path = os.path.join(
                    self.config["backup_destination"],
                    f"{backup_name}.txt"
                )
                shutil.move(str(backup_file), final_backup_path)
                
                # Calculate backup size and compression ratio
                backup_size = os.path.getsize(final_backup_path)
                total_backup_size += backup_size
                compression_ratio = (1 - backup_size / original_size) * 100 if original_size > 0 else 0
                
                # Update source info
                source["last_backup"] = datetime.now().isoformat()
                source["backup_count"] = source.get("backup_count", 0) + 1
                
                print(f"✅ Backup completed: {os.path.basename(final_backup_path)}")
                print(f"   Original size: {original_size/1024:.2f} KB")
                print(f"   Backup size: {backup_size/1024:.2f} KB")
                print(f"   Compression: {compression_ratio:.1f}%")
                print(f"   Time taken: {backup_time:.2f} seconds")
                
                success_count += 1
                
            except Exception as e:
                print(f"❌ Backup failed for {source['name']}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save updated config
        self.save_config()
        
        # Clean up old backups
        self.cleanup_old_backups()
        
        # Print summary
        print(f"\n📊 Backup Summary:")
        print(f"   Sources processed: {len(sources_to_backup)}")
        print(f"   Successful backups: {success_count}")
        print(f"   Total original size: {total_original_size/1024:.2f} KB")
        print(f"   Total backup size: {total_backup_size/1024:.2f} KB")
        if total_original_size > 0:
            overall_compression = (1 - total_backup_size / total_original_size) * 100
            print(f"   Overall compression: {overall_compression:.1f}%")
        
        return success_count == len(sources_to_backup)
    
    def restore_backup(self, backup_file, restore_destination):
        """Restore from a backup file"""
        if not os.path.exists(backup_file):
            print(f"❌ Backup file not found: {backup_file}")
            return False
        
        try:
            print(f"🔄 Restoring from: {os.path.basename(backup_file)}")
            print(f"   Destination: {restore_destination}")
            
            FolderSnapshot.restore_files_from_txt(backup_file, restore_destination)
            
            print(f"✅ Restore completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_backups(self):
        """List all available backup files"""
        if not os.path.exists(self.config["backup_destination"]):
            print("📝 No backup directory found.")
            return
        
        backup_files = []
        for file in os.listdir(self.config["backup_destination"]):
            if file.endswith('.txt'):
                file_path = os.path.join(self.config["backup_destination"], file)
                stat = os.stat(file_path)
                backup_files.append({
                    "name": file,
                    "path": file_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
        
        if not backup_files:
            print("📝 No backup files found.")
            return
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x["modified"], reverse=True)
        
        print("📋 Available Backup Files:")
        print("-" * 80)
        for backup in backup_files:
            print(f"📄 {backup['name']}")
            print(f"   Size: {backup['size']/1024:.2f} KB")
            print(f"   Created: {backup['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Path: {backup['path']}")
            print()
    
    def cleanup_old_backups(self):
        """Remove old backup files based on retention policy"""
        max_backups = self.config.get("max_backups_to_keep", 10)
        
        if max_backups <= 0:
            return  # No cleanup if set to 0 or negative
        
        if not os.path.exists(self.config["backup_destination"]):
            return
        
        # Group backups by source name
        backup_groups = {}
        for file in os.listdir(self.config["backup_destination"]):
            if file.endswith('.txt'):
                # Extract source name from filename
                parts = file.replace('.txt', '').split('_')
                if len(parts) >= 3:  # backup_sourcename_timestamp format
                    source_name = '_'.join(parts[1:-1])  # Everything between 'backup' and timestamp
                    if source_name not in backup_groups:
                        backup_groups[source_name] = []
                    
                    file_path = os.path.join(self.config["backup_destination"], file)
                    backup_groups[source_name].append({
                        "name": file,
                        "path": file_path,
                        "modified": os.path.getmtime(file_path)
                    })
        
        # Clean up each group
        total_removed = 0
        for source_name, backups in backup_groups.items():
            if len(backups) > max_backups:
                # Sort by modification time (oldest first)
                backups.sort(key=lambda x: x["modified"])
                
                # Remove oldest backups
                to_remove = backups[:-max_backups]
                for backup in to_remove:
                    try:
                        os.remove(backup["path"])
                        print(f"🗑️  Removed old backup: {backup['name']}")
                        total_removed += 1
                    except Exception as e:
                        print(f"⚠️  Could not remove {backup['name']}: {e}")
        
        if total_removed > 0:
            print(f"🧹 Cleanup completed: {total_removed} old backup(s) removed")
    
    def calculate_directory_size(self, directory):
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            print(f"⚠️  Error calculating size for {directory}: {e}")
        return total_size
    
    def progress_callback(self, current, total):
        """Progress callback for backup operations"""
        if total > 0:
            percent = int(current * 100 / total)
            bar_length = 30
            filled_length = int(bar_length * current // total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f"\r   Progress: [{bar}] {percent}% ({current}/{total})", end='', flush=True)
            if current == total:
                print()  # New line when complete

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Periodic Backup Tool using FolderSnapshot")
    parser.add_argument("--config", default="backup_config.json", help="Configuration file path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add source command
    add_parser = subparsers.add_parser("add", help="Add backup source")
    add_parser.add_argument("path", help="Path to backup")
    add_parser.add_argument("--name", help="Name for the backup source")
    
    # Remove source command
    remove_parser = subparsers.add_parser("remove", help="Remove backup source")
    remove_parser.add_argument("name", help="Name or path of source to remove")
    
    # List sources command
    subparsers.add_parser("list", help="List backup sources")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create backup")
    backup_parser.add_argument("--source", help="Specific source to backup (default: all)")
    backup_parser.add_argument("--force", action="store_true", help="Force backup even if recent")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore from")
    restore_parser.add_argument("destination", help="Where to restore files")
    
    # List backups command
    subparsers.add_parser("backups", help="List available backup files")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Clean up old backup files")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize backup manager
    backup_manager = PeriodicBackup(args.config)
    
    # Execute command
    if args.command == "add":
        backup_manager.add_backup_source(args.path, args.name)
    
    elif args.command == "remove":
        backup_manager.remove_backup_source(args.name)
    
    elif args.command == "list":
        backup_manager.list_backup_sources()
    
    elif args.command == "backup":
        backup_manager.create_backup(args.source, args.force)
    
    elif args.command == "restore":
        backup_manager.restore_backup(args.backup_file, args.destination)
    
    elif args.command == "backups":
        backup_manager.list_backups()
    
    elif args.command == "cleanup":
        backup_manager.cleanup_old_backups()

if __name__ == "__main__":
    main()