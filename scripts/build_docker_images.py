#!/usr/bin/env python3
"""
Docker Image Builder for Snake Game Bots
Builds Docker images for all bots in the bots/ directory.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


class DockerImageBuilder:
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root)
        self.bots_dir = self.workspace_root / "bots"
        self.built_images = []
        self.failed_images = []
        self.skipped_images = []
        
    def check_docker(self):
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ Docker detected: {result.stdout.strip()}")
                
                # Check if daemon is running
                result = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10
                )
                if result.returncode == 0:
                    print("✓ Docker daemon is running\n")
                    return True
                else:
                    print("✗ Docker daemon is not responding")
                    print("  Make sure Docker Desktop is started.\n")
                    return False
            return False
        except FileNotFoundError:
            print("✗ Docker not found! Please install Docker Desktop.")
            return False
        except Exception as e:
            print(f"✗ Error checking Docker: {e}")
            return False
    
    def discover_bots(self):
        """Find all bot directories with config.json and Dockerfile"""
        bots = []
        if not self.bots_dir.exists():
            print(f"Error: Bots directory not found: {self.bots_dir}")
            return []
        
        for bot_dir in self.bots_dir.iterdir():
            if bot_dir.is_dir():
                config_file = bot_dir / "config.json"
                dockerfile = bot_dir / "Dockerfile"
                
                if config_file.exists() and dockerfile.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            docker_image = config.get("docker_image", "")
                            if docker_image:
                                bots.append({
                                    "name": bot_dir.name,
                                    "path": bot_dir,
                                    "docker_image": docker_image,
                                    "config": config
                                })
                    except Exception as e:
                        print(f"Warning: Could not read config for {bot_dir.name}: {e}")
        
        return sorted(bots, key=lambda x: x["name"])
    
    def check_image_exists(self, image_name):
        """Check if a Docker image already exists"""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", image_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def get_image_info(self, image_name):
        """Get information about a Docker image"""
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.CreatedAt}}\t{{.Size}}", image_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            if result.stdout.strip():
                parts = result.stdout.strip().split('\t')
                return {"created": parts[0] if len(parts) > 0 else "Unknown", 
                       "size": parts[1] if len(parts) > 1 else "Unknown"}
            return None
        except Exception:
            return None
    
    def build_image(self, bot_info, force_rebuild=False):
        """Build a Docker image for a bot"""
        bot_name = bot_info["name"]
        image_name = bot_info["docker_image"]
        bot_path = bot_info["path"]
        
        print(f"\n{'='*70}")
        print(f"📦 Building: {bot_name}")
        print(f"{'='*70}")
        print(f"   Image name: {image_name}")
        print(f"   Bot path: {bot_path.relative_to(self.workspace_root)}")
        
        # Check if image exists
        if not force_rebuild and self.check_image_exists(image_name):
            info = self.get_image_info(image_name)
            if info:
                print(f"   ℹ️  Image already exists (Created: {info['created']}, Size: {info['size']})")
                response = input("   Skip build? (Y/n): ").strip().lower()
                if response != 'n':
                    print("   ⏭️  Skipped")
                    self.skipped_images.append(bot_name)
                    return True
        
        print(f"   🔨 Building image...")
        start_time = datetime.now()
        
        try:
            # Build the image
            result = subprocess.run(
                ["docker", "build", "-t", image_name, "."],
                cwd=bot_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5 minute timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                # Get image info
                info = self.get_image_info(image_name)
                size = info['size'] if info else "Unknown"
                print(f"   ✓ Build successful! (Time: {elapsed:.1f}s, Size: {size})")
                self.built_images.append(bot_name)
                return True
            else:
                print(f"   ✗ Build failed!")
                print(f"   Error output:")
                for line in result.stderr.split('\n')[-10:]:  # Show last 10 lines
                    if line.strip():
                        print(f"      {line}")
                self.failed_images.append(bot_name)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"   ✗ Build timed out after 5 minutes!")
            self.failed_images.append(bot_name)
            return False
        except Exception as e:
            print(f"   ✗ Build error: {e}")
            self.failed_images.append(bot_name)
            return False
    
    def build_all(self, force_rebuild=False):
        """Build Docker images for all bots"""
        print("\n" + "="*70)
        print("  🐳 DOCKER IMAGE BUILDER")
        print("="*70)
        print("\nThis script will build Docker images for all bots.\n")
        
        # Check Docker
        print("-"*70)
        print("🔍 CHECKING DOCKER")
        print("-"*70)
        if not self.check_docker():
            print("\n❌ Cannot proceed without Docker. Exiting.")
            return False
        
        # Discover bots
        print("-"*70)
        print("🔍 DISCOVERING BOTS")
        print("-"*70)
        bots = self.discover_bots()
        
        if not bots:
            print("\n❌ No bots found with Dockerfile and config.json!")
            return False
        
        print(f"\n✓ Found {len(bots)} bot(s) with Docker configuration:")
        for i, bot in enumerate(bots, 1):
            exists = "✓" if self.check_image_exists(bot["docker_image"]) else "✗"
            print(f"   {i}. {bot['name']:20} → {bot['docker_image']:20} [{exists}]")
        
        # Ask for confirmation
        print("\n" + "-"*70)
        if force_rebuild:
            print("Force rebuild mode: Will rebuild all images.")
        else:
            print("Normal mode: Will skip existing images unless you choose to rebuild.")
        
        response = input(f"\nProceed with building {len(bots)} image(s)? (y/N): ").strip().lower()
        if response != 'y':
            print("\n👋 Cancelled by user.")
            return False
        
        # Build images
        print("\n" + "="*70)
        print("🔨 BUILD PHASE")
        print("="*70)
        
        total = len(bots)
        for idx, bot in enumerate(bots, 1):
            print(f"\n[{idx}/{total}]", end=" ")
            self.build_image(bot, force_rebuild)
        
        # Summary
        print("\n" + "="*70)
        print("  📊 BUILD SUMMARY")
        print("="*70)
        print(f"\n✓ Successfully built: {len(self.built_images)}")
        if self.built_images:
            for name in self.built_images:
                print(f"   • {name}")
        
        if self.skipped_images:
            print(f"\n⏭️  Skipped (already exists): {len(self.skipped_images)}")
            for name in self.skipped_images:
                print(f"   • {name}")
        
        if self.failed_images:
            print(f"\n✗ Failed: {len(self.failed_images)}")
            for name in self.failed_images:
                print(f"   • {name}")
        
        print("\n" + "="*70)
        
        if self.failed_images:
            print("⚠️  Some images failed to build. Check errors above.")
            return False
        else:
            print("✅ All images ready! You can now run tournaments.")
            return True


def main():
    # Get workspace root
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    
    # Parse arguments
    force_rebuild = "--force" in sys.argv or "-f" in sys.argv
    
    # Create builder and run
    builder = DockerImageBuilder(workspace_root)
    success = builder.build_all(force_rebuild=force_rebuild)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
