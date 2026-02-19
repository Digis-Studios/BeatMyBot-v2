#!/usr/bin/env python3
"""
Round Robin Tournament Script for Snake Game Engine
Runs all bots against each other on random maps and generates seeded rankings.
"""

import os
import sys
import subprocess
import json
import random
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class TournamentManager:
    def __init__(self, workspace_root, maps_per_match=1):
        self.workspace_root = Path(workspace_root)
        self.bots_dir = self.workspace_root / "bots"
        self.maps_dir = self.workspace_root / "maps"
        self.replays_dir = self.workspace_root / "replays" / "roundrobin"
        self.results = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "points": 0})
        self.match_history = []
        self.total_matches = 0
        self.completed_matches = 0
        self.start_time = None
        self.maps_per_match = maps_per_match
        
        # Create replays directory if it doesn't exist
        self.replays_dir.mkdir(parents=True, exist_ok=True)
        
    def discover_bots(self):
        """Find all bot directories with config.json"""
        bots = []
        if not self.bots_dir.exists():
            print(f"Error: Bots directory not found: {self.bots_dir}")
            return []
        
        for bot_dir in self.bots_dir.iterdir():
            if bot_dir.is_dir() and (bot_dir / "config.json").exists():
                bots.append(bot_dir.name)
        
        return sorted(bots)
    
    def discover_maps(self):
        """Find all map JSON files"""
        maps = []
        if not self.maps_dir.exists():
            print(f"Error: Maps directory not found: {self.maps_dir}")
            return []
        
        # Get maps from main maps directory
        for map_file in self.maps_dir.glob("*.json"):
            maps.append(str(map_file.relative_to(self.workspace_root)))
        
        # Get maps from tourneymaps subdirectory
        tourney_maps_dir = self.maps_dir / "tourneymaps"
        if tourney_maps_dir.exists():
            for map_file in tourney_maps_dir.glob("*.json"):
                maps.append(str(map_file.relative_to(self.workspace_root)))
        
        return sorted(maps)
    
    def check_docker(self):
        """Check if Docker is running and accessible"""
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
                version = result.stdout.strip()
                print(f"   Docker version: {version}")
                
                # Try to list containers to verify Docker daemon is running
                print("   Testing Docker daemon...")
                result = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10
                )
                if result.returncode == 0:
                    print("   ✓ Docker daemon is running")
                    return True
                else:
                    print("   ✗ Docker daemon is not responding")
                    print("   Make sure Docker Desktop is started on Windows.")
                    return False
            return False
        except FileNotFoundError:
            print("   ✗ Docker executable not found")
            print("   Install Docker Desktop from docker.com")
            return False
        except subprocess.TimeoutExpired:
            print("   ✗ Docker check timed out")
            print("   Docker may not be responding properly")
            return False
        except Exception as e:
            print(f"   ✗ Docker check failed: {e}")
            return False
    
    def build_engine(self):
        """Build the game engine"""
        
        try:
            # Determine OS and build accordingly
            if sys.platform == "win32":
                output_file = "bin/snakegame.exe"
                print("Building game engine for Windows...")
            else:
                output_file = "bin/snakegame"
                print("Building game engine for Unix/Linux...")
            
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
            
            print(f"✓ Build successful! Executable: {output_file}")
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
    
    def run_multi_map_match(self, bot1, bot2, all_maps):
        """Run a best-of-N match across multiple maps"""
        num_maps = self.maps_per_match
        
        # Select unique maps for this match
        if len(all_maps) < num_maps:
            print(f"    ⚠️  Warning: Not enough maps ({len(all_maps)}) for best-of-{num_maps}. Using all available.")
            selected_maps = list(all_maps)
        else:
            selected_maps = random.sample(all_maps, num_maps)
        
        map_results = []
        bot1_wins = 0
        bot2_wins = 0
        draws = 0
        
        if num_maps > 1:
            print(f"\n  🎮 Best-of-{num_maps} Match: {bot1} vs {bot2}")
        
        for map_idx, map_path in enumerate(selected_maps, 1):
            if num_maps > 1:
                print(f"\n  📍 Map {map_idx}/{num_maps}: {Path(map_path).name}")
            else:
                print(f"\n  Running: {bot1} vs {bot2} on {Path(map_path).name}")
            
            # Keep replaying until we get a winner (not a draw)
            max_retries = 10
            retry_count = 0
            winner = "DRAW"
            
            while winner == "DRAW" and retry_count < max_retries:
                if retry_count > 0:
                    if num_maps > 1:
                        print(f"    🔄 Draw detected - replaying map (attempt {retry_count + 1})...")
                    else:
                        print(f"  🔄 Draw detected - replaying match (attempt {retry_count + 1})...")
                
                winner, win_reason = self._run_single_match(bot1, bot2, map_path, is_multi_map=(num_maps > 1))
                retry_count += 1
            
            map_results.append({
                "map": Path(map_path).name,
                "winner": winner,
                "win_reason": win_reason
            })
            
            # Save replay with meaningful name
            map_name = Path(map_path).stem
            self.save_replay(bot1, bot2, map_name)
            
            if winner == bot1:
                bot1_wins += 1
                if num_maps > 1:
                    print(f"    ✓ Map result: {bot1} wins")
                    print(f"      Reason: {win_reason}")
                    if retry_count > 1:
                        print(f"      (Decided after {retry_count} attempts)")
                    print(f"      Series: {bot1} {bot1_wins}-{bot2_wins} {bot2}")
            elif winner == bot2:
                bot2_wins += 1
                if num_maps > 1:
                    print(f"    ✓ Map result: {bot2} wins")
                    print(f"      Reason: {win_reason}")
                    if retry_count > 1:
                        print(f"      (Decided after {retry_count} attempts)")
                    print(f"      Series: {bot1} {bot1_wins}-{bot2_wins} {bot2}")
            else:
                draws += 1
                if num_maps > 1:
                    print(f"    ≈ Map result: Draw (after {retry_count} attempts)")
                    print(f"      Reason: {win_reason}")
                    print(f"      Series: {bot1} {bot1_wins}-{bot2_wins} {bot2}, {draws} draws")
                else:
                    print(f"    ≈ Result: Draw (after {retry_count} attempts)")
                    print(f"      Reason: {win_reason}")
            
            # Early exit if winner is decided (majority reached)
            maps_to_win = (num_maps // 2) + 1
            if bot1_wins >= maps_to_win:
                if num_maps > 1 and map_idx < num_maps:
                    print(f"\n  🏁 {bot1} wins the series {bot1_wins}-{bot2_wins} (early victory)")
                return bot1, map_results
            elif bot2_wins >= maps_to_win:
                if num_maps > 1 and map_idx < num_maps:
                    print(f"\n  🏁 {bot2} wins the series {bot2_wins}-{bot1_wins} (early victory)")
                return bot2, map_results
        
        # Determine overall winner
        if bot1_wins > bot2_wins:
            if num_maps > 1:
                print(f"\n  🏁 {bot1} wins the series {bot1_wins}-{bot2_wins}")
            return bot1, map_results
        elif bot2_wins > bot1_wins:
            if num_maps > 1:
                print(f"\n  🏁 {bot2} wins the series {bot2_wins}-{bot1_wins}")
            return bot2, map_results
        else:
            if num_maps > 1:
                print(f"\n  🏁 Series ends in draw {bot1_wins}-{bot2_wins}")
            return "DRAW", map_results
    
    def _run_single_match(self, bot1, bot2, map_path, is_multi_map=False):
        """Run a single match between two bots (internal method)"""
        
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
            
            # Check for errors in stderr
            if result.stderr:
                stderr_lower = result.stderr.lower()
                if "docker" in stderr_lower and ("timeout" in stderr_lower or "not running" in stderr_lower or "cannot connect" in stderr_lower):
                    print(f"    WARNING: Docker issue detected!")
                    print(f"    Error: {result.stderr[:200]}")
                    # Return as draw with reason
                    return "DRAW", "Docker error"
            
            # Check return code
            if result.returncode != 0:
                print(f"    WARNING: Match ended with error code {result.returncode}")
                if result.stderr:
                    print(f"    Error output: {result.stderr[:200]}")
            
            # Parse the result from stdout
            output = result.stdout
            
            # Determine winner from the output or replay file
            winner, win_reason = self.determine_winner(bot1, bot2, output)
            
            # Record the result
            # For single-map mode or when not part of multi-map, print individual results
            if not is_multi_map:
                if winner == bot1:
                    print(f"    ✓ Result: {bot1} WINS!")
                    print(f"      Reason: {win_reason}")
                elif winner == bot2:
                    print(f"    ✓ Result: {bot2} WINS!")
                    print(f"      Reason: {win_reason}")
                else:
                    print(f"    ≈ Result: DRAW")
                    print(f"      Reason: {win_reason}")
            
            return winner, win_reason
            
        except subprocess.TimeoutExpired:
            print(f"    ERROR: Match timed out after 120 seconds!")
            print(f"    This usually means a bot is hanging or Docker is not responding.")
            # Timeout counts as a draw
            return "DRAW", "Match timeout"
        except Exception as e:
            print(f"    ERROR: Exception running match: {e}")
            # Error counts as a draw
            return "DRAW", f"Error: {str(e)}"
    
    def save_replay(self, bot1, bot2, map_name, match_num=None):
        """Save replay with descriptive filename"""
        source = self.workspace_root / "replays" / "match_replay.json"
        
        if not source.exists():
            return False
        
        # Create filename: bot1-vs-bot2-mapname.json (optionally with match number)
        if match_num is not None:
            filename = f"match{match_num:03d}_{bot1}-vs-{bot2}-{map_name}.json"
        else:
            filename = f"{bot1}-vs-{bot2}-{map_name}.json"
        destination = self.replays_dir / filename
        
        try:
            shutil.copy(source, destination)
            return True
        except Exception as e:
            print(f"      Warning: Failed to save replay: {e}")
            return False
    
    def determine_winner(self, bot1, bot2, output):
        """Parse match output to determine winner and extract details"""
        # Try to read from the replay file
        replay_path = self.workspace_root / "replays" / "match_replay.json"
        win_reason = ""
        
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
        
        # Fallback: parse stdout
        if "Bot 1 wins" in output:
            return bot1, "Bot 1 wins"
        elif "Bot 2 wins" in output:
            return bot2, "Bot 2 wins"
        else:
            return "DRAW", "Draw or unknown result"
    
    def run_round_robin(self, bots, maps, use_random_map=True):
        """Run a full round robin tournament"""
        print("\n" + "="*70)
        print("  SNAKE GAME ENGINE - ROUND ROBIN TOURNAMENT")
        print("="*70)
        print(f"\n📋 Tournament Configuration:")
        print(f"   Participants: {len(bots)} bots")
        print(f"   Available Maps: {len(maps)}")
        print(f"   Total Matches: {len(bots) * (len(bots) - 1) // 2}")
        print(f"   Maps per Match: {self.maps_per_match} (Best-of-{self.maps_per_match})")
        print(f"   Map Selection: Random (no repeats within a match)")
        print(f"   Scoring: Win = 3 pts | Draw = 1 pt | Loss = 0 pts")
        
        if len(bots) < 2:
            print("\nError: Need at least 2 bots for a tournament!")
            return
        
        if len(maps) == 0:
            print("\nError: No maps found!")
            return
        
        # Generate match pairings
        matches = []
        for i in range(len(bots)):
            for j in range(i + 1, len(bots)):
                matches.append((bots[i], bots[j]))
        
        self.total_matches = len(matches)
        self.start_time = datetime.now()
        
        print(f"\n🎮 Starting tournament with {len(matches)} matches...")
        print(f"   Estimated time: ~{len(matches) * 2} minutes (2 min/match avg)\n")
        
        # Run all matches
        for idx, (bot1, bot2) in enumerate(matches, 1):
            self.completed_matches = idx - 1
            elapsed = (datetime.now() - self.start_time).total_seconds()
            avg_time = elapsed / idx if idx > 1 else 0
            remaining = int(avg_time * (len(matches) - idx + 1))
            
            print(f"\n{'='*70}")
            print(f"Match {idx}/{len(matches)} | Progress: {idx/len(matches)*100:.1f}% | Est. remaining: {remaining//60}m {remaining%60}s")
            print(f"{'='*70}")
            
            # Run match across multiple maps
            winner, map_results = self.run_multi_map_match(bot1, bot2, maps)
            
            # Record the match result
            match_record = {
                "bot1": bot1,
                "bot2": bot2,
                "winner": winner,
                "map_results": map_results,
                "timestamp": datetime.now().isoformat()
            }
            self.match_history.append(match_record)
            
            # Update overall statistics
            if winner == bot1:
                self.results[bot1]["wins"] += 1
                self.results[bot1]["points"] += 3
                self.results[bot2]["losses"] += 1
                print(f"\n  ✓ Match Result: {bot1} WINS! (+3 pts)")
            elif winner == bot2:
                self.results[bot2]["wins"] += 1
                self.results[bot2]["points"] += 3
                self.results[bot1]["losses"] += 1
                print(f"\n  ✓ Match Result: {bot2} WINS! (+3 pts)")
            else:  # Draw
                self.results[bot1]["draws"] += 1
                self.results[bot1]["points"] += 1
                self.results[bot2]["draws"] += 1
                self.results[bot2]["points"] += 1
                print(f"\n  ≈ Match Result: DRAW (+1 pt each)")
            
            # Show current standings
            print(f"      {bot1}: {self.results[bot1]['wins']}W-{self.results[bot1]['draws']}D-{self.results[bot1]['losses']}L ({self.results[bot1]['points']} pts)")
            print(f"      {bot2}: {self.results[bot2]['wins']}W-{self.results[bot2]['draws']}D-{self.results[bot2]['losses']}L ({self.results[bot2]['points']} pts)")
        
        self.completed_matches = len(matches)
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*70)
        print("  🏆 TOURNAMENT COMPLETE!")
        print("="*70)
        print(f"   Total matches: {len(matches)}")
        print(f"   Total time: {int(total_time//60)}m {int(total_time%60)}s")
        print(f"   Avg time per match: {total_time/len(matches):.1f}s")
    
    def generate_rankings(self):
        """Generate final rankings based on points"""
        rankings = []
        for bot, stats in self.results.items():
            rankings.append({
                "rank": 0,  # Will be filled in
                "bot": bot,
                "points": stats["points"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "matches": stats["wins"] + stats["draws"] + stats["losses"]
            })
        
        # Sort by points (descending), then by wins, then alphabetically
        rankings.sort(key=lambda x: (-x["points"], -x["wins"], x["bot"]))
        
        # Assign ranks
        for idx, entry in enumerate(rankings, 1):
            entry["rank"] = idx
        
        return rankings
    
    def print_results(self, rankings):
        """Print tournament results table"""
        print("\n" + "="*85)
        print("  📊 FINAL STANDINGS & SEEDING")
        print("="*85)
        
        # Header
        print(f"\n{'Rank':<6} {'Bot Name':<25} {'Points':<8} {'W':<5} {'D':<5} {'L':<5} {'Matches':<8} {'Win %':<8}")
        print("-"*85)
        
        # Rankings
        for entry in rankings:
            total = entry['matches']
            win_pct = (entry['wins'] / total * 100) if total > 0 else 0
            
            # Add medal emojis for top 3
            rank_display = entry['rank']
            if entry['rank'] == 1:
                rank_display = "🥇 1"
            elif entry['rank'] == 2:
                rank_display = "🥈 2"
            elif entry['rank'] == 3:
                rank_display = "🥉 3"
            
            print(f"{str(rank_display):<6} {entry['bot']:<25} {entry['points']:<8} "
                  f"{entry['wins']:<5} {entry['draws']:<5} {entry['losses']:<5} "
                  f"{entry['matches']:<8} {win_pct:>5.1f}%")
        
        print("="*85)
        print("\n📈 Tournament Statistics:")
        print(f"   Scoring System: Win = 3 points | Draw = 1 point | Loss = 0 points")
        
        # Additional stats
        total_wins = sum(r['wins'] for r in rankings)
        total_draws = sum(r['draws'] for r in rankings) // 2  # Divide by 2 since each draw is counted twice
        total_matches = self.completed_matches
        
        print(f"   Total Matches Played: {total_matches}")
        print(f"   Decisive Results: {total_wins} ({total_wins/total_matches*100:.1f}%)")
        print(f"   Draws: {total_draws} ({total_draws/total_matches*100:.1f}%)")
        
        # Top performer
        if rankings:
            top = rankings[0]
            print(f"\n🏆 Tournament Champion: {top['bot']}")
            print(f"   Record: {top['wins']}-{top['draws']}-{top['losses']} | {top['points']} points | {(top['wins']/top['matches']*100):.1f}% win rate")
    
    def save_results(self, rankings):
        """Save tournament results to file"""
        output_dir = self.workspace_root / "tournament_results"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"round_robin_{timestamp}.json"
        
        tournament_data = {
            "tournament_type": "round_robin",
            "timestamp": datetime.now().isoformat(),
            "participants": len(rankings),
            "total_matches": len(self.match_history),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "rankings": rankings,
            "match_history": self.match_history
        }
        
        with open(output_file, 'w') as f:
            json.dump(tournament_data, f, indent=2)
        
        print("\n" + "="*85)
        print("  💾 RESULTS SAVED")
        print("="*85)
        print(f"\n📄 Detailed Results (JSON):")
        print(f"   {output_file.relative_to(self.workspace_root)}")
        print(f"   Contains: Full match history, timestamps, and detailed statistics")
        
        # Also save a simple seeding file
        seeding_file = output_dir / "latest_seeding.txt"
        with open(seeding_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("SNAKE GAME - TOURNAMENT SEEDING (Latest Round Robin)\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Total Participants: {len(rankings)}\n")
            f.write(f"Total Matches: {len(self.match_history)}\n")
            f.write(f"Scoring: Win = 3 pts | Draw = 1 pt | Loss = 0 pts\n\n")
            f.write("FINAL SEEDING:\n")
            f.write("-" * 70 + "\n\n")
            for entry in rankings:
                total = entry['matches']
                win_pct = (entry['wins'] / total * 100) if total > 0 else 0
                f.write(f"Seed #{entry['rank']}: {entry['bot']}\n")
                f.write(f"   Score: {entry['points']} points\n")
                f.write(f"   Record: {entry['wins']} Wins - {entry['draws']} Draws - {entry['losses']} Losses\n")
                f.write(f"   Win Rate: {win_pct:.1f}%\n\n")
        
        print(f"\n📋 Seeding Summary (TXT):")
        print(f"   {seeding_file.relative_to(self.workspace_root)}")
        print(f"   Contains: Easy-to-read seeding order for bracket tournaments")
        print("\n" + "="*85)


def main():
    # Get workspace root (parent of scripts directory)
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    
    # Parse command line arguments
    maps_per_match = 1
    if len(sys.argv) > 1:
        try:
            maps_per_match = int(sys.argv[1])
            if maps_per_match not in [1, 3, 5]:
                print("Error: Maps per match must be 1, 3, or 5")
                print("Usage: python round_robin.py [maps_per_match]")
                print("Example: python round_robin.py 3  # Best-of-3")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid argument. Maps per match must be a number (1, 3, or 5)")
            print("Usage: python round_robin.py [maps_per_match]")
            sys.exit(1)
    
    print("="*85)
    print("  🐍 SNAKE GAME ENGINE - ROUND ROBIN TOURNAMENT MANAGER")
    print("="*85)
    print("\nThis script will run a complete round-robin tournament where every bot")
    print("plays against every other bot.")
    if maps_per_match > 1:
        print(f"Each match is Best-of-{maps_per_match} across different maps.")
    
    # Create tournament manager
    tm = TournamentManager(workspace_root, maps_per_match=maps_per_match)
    
    # Discover bots and maps
    print("\n" + "-"*85)
    print("🔍 DISCOVERY PHASE")
    print("-"*85)
    
    print("\n📁 Scanning for bots in bots/ directory...")
    bots = tm.discover_bots()
    if bots:
        print(f"✓ Found {len(bots)} bot(s):")
        for i, bot in enumerate(bots, 1):
            print(f"   {i}. {bot}")
    else:
        print("✗ No bots found!")
    
    print("\n🗺️  Scanning for maps...")
    maps = tm.discover_maps()
    if maps:
        print(f"✓ Found {len(maps)} map(s):")
        for m in maps[:5]:  # Show first 5
            print(f"   • {m}")
        if len(maps) > 5:
            print(f"   ... and {len(maps) - 5} more")
    else:
        print("✗ No maps found!")
    
    if len(bots) < 2:
        print("\n❌ Error: Need at least 2 bots to run a tournament!")
        sys.exit(1)
    
    if len(maps) == 0:
        print("\n❌ Error: No maps found!")
        sys.exit(1)
    
    # Check Docker availability
    print("\n" + "-"*85)
    print("🐳 DOCKER VERIFICATION")
    print("-"*85)
    print("\nChecking if Docker is installed and running...")
    docker_available = tm.check_docker()
    if not docker_available:
        print("\n⚠️  WARNING: Docker may not be available or running!")
        print("   Many bots require Docker to run. Matches may fail without it.")
        print("   On Windows, make sure Docker Desktop is started.")
        response = input("\n❓ Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("\n👋 Exiting. Start Docker and try again.")
            sys.exit(0)
        print("\n⚡ Continuing without Docker verification...")
    else:
        print("✓ Docker is ready!")
    
    # Build the engine
    print("\n" + "-"*85)
    print("🔨 BUILD PHASE")
    print("-"*85)
    if not tm.build_engine():
        print("\n❌ Failed to build engine. Exiting.")
        sys.exit(1)
    
    # Run the tournament
    tm.run_round_robin(bots, maps, use_random_map=True)
    
    # Generate and display rankings
    rankings = tm.generate_rankings()
    tm.print_results(rankings)
    
    # Save results
    tm.save_results(rankings)
    
    print("\n" + "="*85)
    print("  ✅ TOURNAMENT COMPLETE - ALL RESULTS SAVED")
    print("="*85)
    print("\n📌 Next Steps:")
    print("   • Review detailed results in tournament_results/")
    print("   • Use seeding for bracket tournaments")
    print("   • Watch replays in replays/ directory (last match only)")
    print("   • Analyze bot performance and iterate on strategies")
    print("\n" + "="*85)


if __name__ == "__main__":
    main()
