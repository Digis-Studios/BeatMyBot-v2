#!/usr/bin/env python3
"""
Match Series Script for Snake Game Engine
Runs two bots against each other on all 5 maps and saves individual replays.
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime


class MatchSeriesManager:
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root)
        self.maps = [
            
            "maps/framed.json",
            "maps/headphones.json",
            "maps/large.json",
            "maps/sssss.json",
            "maps/x.json"
        ]
        self.replays_dir = self.workspace_root / "replays"
        
    def build_engine(self):
        """Build the game engine"""
        print("Building game engine...")
        
        try:
            # Determine OS and build accordingly
            if sys.platform == "win32":
                output_file = "bin/snakegame.exe"
            else:
                output_file = "bin/snakegame"
            
            result = subprocess.run(
                ["go", "build", "-o", output_file],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"❌ Build failed!")
                print(f"Error: {result.stderr}")
                return False
            
            print(f"✓ Build successful!\n")
            return True
        except FileNotFoundError:
            print("❌ Error: Go compiler not found! Make sure Go is installed.")
            return False
        except subprocess.TimeoutExpired:
            print("❌ Error: Build timed out after 60 seconds!")
            return False
        except Exception as e:
            print(f"❌ Error building engine: {e}")
            return False
    
    def run_match(self, bot1, bot2, map_path):
        """Run a single match between two bots"""
        try:
            # Determine executable name
            if sys.platform == "win32":
                exe = self.workspace_root / "bin" / "snakegame.exe"
            else:
                exe = self.workspace_root / "bin" / "snakegame"
            
            # Run the match
            result = subprocess.run(
                [str(exe), "-bot1", bot1, "-bot2", bot2, "-map", map_path],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120
            )
            
            # Check for errors
            if result.returncode != 0:
                print(f"    ⚠️  Match failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"    Error: {result.stderr.strip()}")
                return "ERROR", "Match execution failed", False
            
            if result.stderr and result.stderr.strip():
                print(f"    ⚠️  Match warnings: {result.stderr.strip()[:200]}")
            
            # Parse the result from stdout
            output = result.stdout
            
            # Determine winner from the output or replay file
            winner, win_reason = self.determine_winner(bot1, bot2)
            
            return winner, win_reason, True
            
        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Match timed out after 120 seconds!")
            return "DRAW", "Match timeout", False
        except Exception as e:
            print(f"    ⚠️  Exception running match: {e}")
            return "DRAW", f"Error: {str(e)}", False
    
    def determine_winner(self, bot1, bot2):
        """Parse replay file to determine winner"""
        replay_path = self.workspace_root / "replays" / "match_replay.json"
        
        try:
            if replay_path.exists():
                with open(replay_path, 'r') as f:
                    replay_data = json.load(f)
                    win_reason = replay_data.get("win_reason", "")
                    
                    if "Bot 1 wins" in win_reason:
                        return bot1, win_reason
                    elif "Bot 2 wins" in win_reason:
                        return bot2, win_reason
                    else:
                        return "DRAW", win_reason
        except Exception as e:
            print(f"      Warning: Could not read replay file: {e}")
        
        return "DRAW", "Unknown result"
    
    def save_replay(self, bot1, bot2, map_name):
        """Save replay with descriptive filename"""
        source = self.workspace_root / "replays" / "match_replay.json"
        
        if not source.exists():
            print(f"    ⚠️  Replay file not found!")
            return False
        
        # Create filename: bot1-vs-bot2-mapname.json
        filename = f"{bot1}-vs-{bot2}-{map_name}.json"
        destination = self.replays_dir / filename
        
        try:
            shutil.copy(source, destination)
            print(f"    💾 Saved: {filename}")
            return True
        except Exception as e:
            print(f"    ⚠️  Failed to save replay: {e}")
            return False
    
    def validate_bots(self, bot1, bot2):
        """Check if bot directories exist"""
        bots_dir = self.workspace_root / "bots"
        bots_done_dir = self.workspace_root / "bots-done"
        
        bot1_path = None
        bot2_path = None
        
        # Check for bot1
        if (bots_dir / bot1).exists():
            bot1_path = bots_dir / bot1
        elif (bots_done_dir / bot1).exists():
            bot1_path = bots_done_dir / bot1
        
        # Check for bot2
        if (bots_dir / bot2).exists():
            bot2_path = bots_dir / bot2
        elif (bots_done_dir / bot2).exists():
            bot2_path = bots_done_dir / bot2
        
        if not bot1_path:
            print(f"❌ Error: Bot '{bot1}' not found in 'bots/' or 'bots-done/' directories")
            return False
        
        if not bot2_path:
            print(f"❌ Error: Bot '{bot2}' not found in 'bots/' or 'bots-done/' directories")
            return False
        
        print(f"✓ Found bot '{bot1}' in {bot1_path.parent.name}/")
        print(f"✓ Found bot '{bot2}' in {bot2_path.parent.name}/")
        return True
    
    def run_series(self, bot1, bot2):
        """Run a best-of-5 series across all maps"""
        print("="*70)
        print(f"  MATCH SERIES: {bot1} vs {bot2}")
        print("="*70)
        print(f"\n📋 Series Configuration:")
        print(f"   Format: Best-of-{len(self.maps)}")
        print(f"   Maps: {', '.join([Path(m).stem for m in self.maps])}")
        
        # Validate bots exist
        print(f"\n🔍 Validating bots...")
        if not self.validate_bots(bot1, bot2):
            print("\n❌ Cannot start series - bot validation failed")
            return
        
        print(f"\n🎮 Starting series...\n")
        
        bot1_wins = 0
        bot2_wins = 0
        draws = 0
        
        for idx, map_path in enumerate(self.maps, 1):
            map_name = Path(map_path).stem
            print(f"{'─'*70}")
            print(f"Map {idx}/{len(self.maps)}: {map_name}")
            print(f"{'─'*70}")
            
            # Keep replaying until we get a winner (not a draw)
            max_retries = 10
            retry_count = 0
            winner = "DRAW"
            
            while winner == "DRAW" and retry_count < max_retries:
                if retry_count > 0:
                    print(f"   🔄 Draw detected - replaying map (attempt {retry_count + 1})...")
                
                winner, win_reason, success = self.run_match(bot1, bot2, map_path)
                
                if not success:
                    print(f"❌ Match failed to run properly")
                    print(f"   Skipping this match...\n")
                    break
                
                retry_count += 1
            
            # If still a draw after retries, count it
            if winner == "DRAW":
                draws += 1
                print(f"🤝 Draw (after {retry_count} attempts)")
                print(f"   Reason: {win_reason}")
            elif winner == bot1:
                bot1_wins += 1
                print(f"✅ Winner: {bot1}")
                print(f"   Reason: {win_reason}")
                if retry_count > 1:
                    print(f"   (Decided after {retry_count} attempts)")
            elif winner == bot2:
                bot2_wins += 1
                print(f"✅ Winner: {bot2}")
                print(f"   Reason: {win_reason}")
                if retry_count > 1:
                    print(f"   (Decided after {retry_count} attempts)")
            
            print(f"   Series Score: {bot1} {bot1_wins}-{bot2_wins} {bot2} ({draws} draws)")
            
            # Save replay with descriptive name
            self.save_replay(bot1, bot2, map_name)
            
            print()
        
        # Print final results
        print("="*70)
        print("  SERIES COMPLETE!")
        print("="*70)
        print(f"\n📊 Final Score:")
        print(f"   {bot1}: {bot1_wins} wins")
        print(f"   {bot2}: {bot2_wins} wins")
        print(f"   Draws: {draws}")
        print()
        
        if bot1_wins > bot2_wins:
            print(f"🏆 SERIES WINNER: {bot1}")
            print(f"   Victory Margin: {bot1_wins}-{bot2_wins}")
        elif bot2_wins > bot1_wins:
            print(f"🏆 SERIES WINNER: {bot2}")
            print(f"   Victory Margin: {bot2_wins}-{bot1_wins}")
        else:
            print(f"🤝 SERIES TIED: {bot1_wins}-{bot2_wins}")
        
        print(f"\n💾 Replays saved in: replays/")
        print(f"   Pattern: {bot1}-vs-{bot2}-<mapname>.json")
        print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/match_series.py <bot1> <bot2>")
        print("\nExample:")
        print("  python scripts/match_series.py GodBot pandas")
        print("  python scripts/match_series.py crimemastergogo sleeping_snakes")
        sys.exit(1)
    
    bot1 = sys.argv[1]
    bot2 = sys.argv[2]
    
    # Get workspace root (parent of scripts directory)
    workspace_root = Path(__file__).parent.parent
    
    manager = MatchSeriesManager(workspace_root)
    
    # Build engine
    if not manager.build_engine():
        print("\n❌ Failed to build engine. Aborting.")
        sys.exit(1)
    
    # Run the series
    manager.run_series(bot1, bot2)


if __name__ == "__main__":
    main()
