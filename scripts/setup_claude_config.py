import json
import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any
import argparse


class ClaudeConfigManager:
    def __init__(self):
        self.config_dir = Path(os.environ['APPDATA']) / 'Claude'
        self.config_path = self.config_dir / 'claude_desktop_config.json'
        self.backup_path = self.config_dir / 'claude_desktop_config.json.backup'
        self.project_root = Path(__file__).parent.parent.resolve()
        
    def validate_environment(self) -> tuple[bool, list[str]]:
        errors = []
        
        if not self.config_dir.exists():
            errors.append(f"Claude Desktop directory not found: {self.config_dir}")
            errors.append("Is Claude Desktop installed?")
        
        pyproject = self.project_root / 'pyproject.toml'
        if not pyproject.exists():
            errors.append(f"pyproject.toml not found in {self.project_root}")
            errors.append("Run this script from project root: python scripts/setup_claude_config.py")
        
        mcp_server = self.project_root / 'src' / 'kraken' / 'mcp_server.py'
        if not mcp_server.exists():
            errors.append(f"MCP server not found: {mcp_server}")
            errors.append("Expected: src/kraken/mcp_server.py")
        
        uv_check = os.system('uv --version >nul 2>&1')
        if uv_check != 0:
            errors.append("uv not found in PATH")
            errors.append("Install: https://docs.astral.sh/uv/getting-started/installation/")
        
        try:
            sys.path.insert(0, str(self.project_root / 'src'))
            import kraken.mcp_server
        except ImportError as e:
            errors.append(f"Cannot import kraken.mcp_server: {e}")
            errors.append("Run: uv sync")
        finally:
            sys.path.pop(0)
        
        return (len(errors) == 0, errors)
    
    def generate_config(self) -> Dict[str, Any]:
        project_path = str(self.project_root).replace('\\', '/')
        
        config = {
            "mcpServers": {
                "kraken": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        project_path,
                        "run",
                        "python",
                        "-m",
                        "kraken.mcp_server"
                    ]
                }
            }
        }
        
        return config
    
    def backup_existing(self) -> bool:
        if not self.config_path.exists():
            print("No existing config to backup")
            return True
        
        try:
            shutil.copy2(self.config_path, self.backup_path)
            print(f"✓ Backed up existing config to: {self.backup_path}")
            return True
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return False
    
    def write_config(self, config: Dict[str, Any]) -> bool:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            json_str = json.dumps(config, indent=2, ensure_ascii=False)
            self.config_path.write_text(json_str, encoding='utf-8')
            print(f"✓ Config written to: {self.config_path}")
            return True
        except Exception as e:
            print(f"✗ Write failed: {e}")
            return False
    
    def validate_config(self) -> tuple[bool, list[str]]:
        errors = []
        
        if not self.config_path.exists():
            errors.append("Config file not found after write")
            return (False, errors)
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return (False, errors)
        
        if 'mcpServers' not in loaded_config:
            errors.append("Missing 'mcpServers' key")
        
        if 'kraken' not in loaded_config.get('mcpServers', {}):
            errors.append("Missing 'kraken' server config")
        
        kraken_config = loaded_config.get('mcpServers', {}).get('kraken', {})
        
        if 'command' not in kraken_config:
            errors.append("Missing 'command' in kraken config")
        
        if 'args' not in kraken_config:
            errors.append("Missing 'args' in kraken config")
        
        args = kraken_config.get('args', [])
        if '--directory' in args:
            dir_index = args.index('--directory')
            if dir_index + 1 < len(args):
                project_path = args[dir_index + 1]
                path_obj = Path(project_path.replace('/', os.sep))
                if not path_obj.exists():
                    errors.append(f"Project path in config doesn't exist: {project_path}")
        
        if len(errors) == 0:
            print("✓ Config validation passed")
        
        return (len(errors) == 0, errors)
    
    def restore_backup(self) -> bool:
        if not self.backup_path.exists():
            print("✗ No backup found")
            return False
        
        try:
            shutil.copy2(self.backup_path, self.config_path)
            print(f"✓ Restored config from: {self.backup_path}")
            return True
        except Exception as e:
            print(f"✗ Restore failed: {e}")
            return False
    
    def setup(self) -> bool:
        print("=" * 60)
        print("Claude Desktop MCP Configuration Setup")
        print("=" * 60)
        print()
        
        print("[1/5] Validating environment...")
        valid, errors = self.validate_environment()
        if not valid:
            print("✗ Environment validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        print("✓ Environment OK")
        print()
        
        print("[2/5] Backing up existing config...")
        if not self.backup_existing():
            print("⚠ Warning: Backup failed, continuing anyway")
        print()
        
        print("[3/5] Generating configuration...")
        config = self.generate_config()
        print(f"✓ Config generated:")
        print(json.dumps(config, indent=2))
        print()
        
        print("[4/5] Writing configuration...")
        if not self.write_config(config):
            print("✗ Setup failed: Could not write config")
            return False
        print()
        
        print("[5/5] Validating written config...")
        valid, errors = self.validate_config()
        if not valid:
            print("✗ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        print()
        
        print("=" * 60)
        print("✓ Setup complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart Claude Desktop completely (quit + reopen)")
        print("2. Wait 10 seconds for initialization")
        print("3. In Claude, type: 'What time is it?'")
        print("4. Check logs: %APPDATA%\\Claude\\logs\\mcp-server-kraken*.log")
        print()
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Manage Claude Desktop MCP configuration for Kraken'
    )
    parser.add_argument(
        '--restore',
        action='store_true',
        help='Restore config from backup'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test existing config without changes'
    )
    
    args = parser.parse_args()
    manager = ClaudeConfigManager()
    
    if args.restore:
        success = manager.restore_backup()
        sys.exit(0 if success else 1)
    
    if args.test:
        valid, errors = manager.validate_config()
        if not valid:
            print("✗ Config validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        print("✓ Config is valid")
        sys.exit(0)
    
    success = manager.setup()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()