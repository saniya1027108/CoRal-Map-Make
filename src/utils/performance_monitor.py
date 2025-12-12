# src/utils/performance_monitor.py
"""
Performance monitoring for parallel LLM extraction.
Tracks timing, throughput, and identifies bottlenecks.
"""
import time
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from threading import Lock
from ..utils.logging_utils import setup_logger

logger = setup_logger("performance")


class PerformanceMonitor:
    """Monitor and track performance metrics for parallel extraction."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Timing data
        self.group_times = {}  # group_label -> duration
        self.chunk_times = defaultdict(list)  # group_label -> [chunk_durations]
        self.slow_calls = []  # List of slow calls
        
        # Throughput tracking
        self.start_time = None
        self.end_time = None
        self.total_calls = 0
        self.completed_calls = 0
        
        # Thread safety
        self.lock = Lock()
        
        # Bottleneck detection
        self.group_start_times = {}
        self.group_end_times = {}
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        logger.info("📊 Performance monitoring started")
    
    def record_call_start(self, group_label: str, chunk_idx: int):
        """Record the start of an LLM call."""
        with self.lock:
            key = f"{group_label}_{chunk_idx}"
            if not hasattr(self, '_call_starts'):
                self._call_starts = {}
            self._call_starts[key] = time.time()
    
    def record_call_end(self, group_label: str, chunk_idx: int, slow_threshold: float = 5.0):
        """Record the end of an LLM call and check if it was slow."""
        with self.lock:
            key = f"{group_label}_{chunk_idx}"
            if not hasattr(self, '_call_starts'):
                return
            
            if key in self._call_starts:
                duration = time.time() - self._call_starts[key]
                self.chunk_times[group_label].append(duration)
                self.completed_calls += 1
                
                # Check if slow
                if duration > slow_threshold:
                    self.slow_calls.append({
                        "group": group_label,
                        "chunk": chunk_idx,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.warning(f"🐌 Slow call detected: {group_label} chunk {chunk_idx} took {duration:.2f}s")
                
                del self._call_starts[key]
    
    def record_group_start(self, group_label: str):
        """Record when a group starts processing."""
        with self.lock:
            self.group_start_times[group_label] = time.time()
    
    def record_group_end(self, group_label: str):
        """Record when a group finishes processing."""
        with self.lock:
            if group_label in self.group_start_times:
                duration = time.time() - self.group_start_times[group_label]
                self.group_times[group_label] = duration
                self.group_end_times[group_label] = time.time()
    
    def finish_monitoring(self):
        """Finish monitoring and calculate final metrics."""
        self.end_time = time.time()
        logger.info("📊 Performance monitoring completed")
    
    def generate_report(self) -> dict:
        """Generate comprehensive performance report."""
        if not self.start_time or not self.end_time:
            logger.warning("Monitoring not properly started/ended")
            return {}
        
        total_duration = self.end_time - self.start_time
        
        report = {
            "summary": {
                "total_duration_seconds": round(total_duration, 2),
                "total_calls": self.completed_calls,
                "calls_per_second": round(self.completed_calls / total_duration, 2),
                "avg_call_duration": round(
                    sum(sum(times) for times in self.chunk_times.values()) / max(self.completed_calls, 1),
                    2
                )
            },
            "groups": {},
            "bottlenecks": [],
            "slow_calls": self.slow_calls
        }
        
        # Group-level statistics
        for group_label, duration in self.group_times.items():
            chunk_durations = self.chunk_times.get(group_label, [])
            if chunk_durations:
                report["groups"][group_label] = {
                    "total_duration": round(duration, 2),
                    "num_calls": len(chunk_durations),
                    "avg_call_duration": round(sum(chunk_durations) / len(chunk_durations), 2),
                    "min_call_duration": round(min(chunk_durations), 2),
                    "max_call_duration": round(max(chunk_durations), 2),
                    "throughput_calls_per_sec": round(len(chunk_durations) / duration, 2)
                }
        
        # Identify bottlenecks (groups that took longest)
        if self.group_times:
            sorted_groups = sorted(
                self.group_times.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            report["bottlenecks"] = [
                {
                    "group": group,
                    "duration": round(duration, 2),
                    "percentage_of_total": round(duration / total_duration * 100, 1)
                }
                for group, duration in sorted_groups[:5]
            ]
        
        return report
    
    def save_report(self, filename: str = "performance_report.json"):
        """Save performance report to file."""
        report = self.generate_report()
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Performance report saved to {output_path}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("⚡ PERFORMANCE SUMMARY")
        print("="*80)
        summary = report["summary"]
        print(f"Total Duration: {summary['total_duration_seconds']:.2f}s")
        print(f"Total Calls: {summary['total_calls']}")
        print(f"Throughput: {summary['calls_per_second']:.2f} calls/sec")
        print(f"Avg Call Duration: {summary['avg_call_duration']:.2f}s")
        
        if report["bottlenecks"]:
            print(f"\n🔴 Top Bottlenecks:")
            for i, bottleneck in enumerate(report["bottlenecks"][:3], 1):
                print(f"   {i}. {bottleneck['group']}: {bottleneck['duration']:.2f}s ({bottleneck['percentage_of_total']:.1f}%)")
        
        if report["slow_calls"]:
            print(f"\n🐌 Slow Calls: {len(report['slow_calls'])}")
            print(f"   (See {output_path} for details)")
        
        print("="*80 + "\n")
        
        return report


def create_performance_visualization(report: dict, output_path: Path):
    """Create a simple text-based visualization of performance."""
    viz_path = output_path.parent / "performance_visualization.txt"
    
    with open(viz_path, "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("PERFORMANCE VISUALIZATION\n")
        f.write("="*80 + "\n\n")
        
        # Summary
        f.write("SUMMARY\n")
        f.write("-"*40 + "\n")
        summary = report["summary"]
        f.write(f"Total Duration: {summary['total_duration_seconds']:.2f}s\n")
        f.write(f"Total Calls: {summary['total_calls']}\n")
        f.write(f"Throughput: {summary['calls_per_second']:.2f} calls/sec\n")
        f.write(f"Avg Call Duration: {summary['avg_call_duration']:.2f}s\n\n")
        
        # Group timeline (ASCII art)
        f.write("GROUP DURATIONS\n")
        f.write("-"*40 + "\n")
        
        if report.get("groups"):
            max_duration = max(g["total_duration"] for g in report["groups"].values())
            
            for group_label, group_data in sorted(
                report["groups"].items(),
                key=lambda x: x[1]["total_duration"],
                reverse=True
            ):
                duration = group_data["total_duration"]
                bar_length = int((duration / max_duration) * 40)
                bar = "█" * bar_length
                
                f.write(f"{group_label:30} {bar} {duration:.2f}s\n")
        
        f.write("\n")
        
        # Bottlenecks
        if report.get("bottlenecks"):
            f.write("BOTTLENECKS\n")
            f.write("-"*40 + "\n")
            for i, bottleneck in enumerate(report["bottlenecks"], 1):
                f.write(f"{i}. {bottleneck['group']}\n")
                f.write(f"   Duration: {bottleneck['duration']:.2f}s\n")
                f.write(f"   % of Total: {bottleneck['percentage_of_total']:.1f}%\n\n")
        
        # Slow calls
        if report.get("slow_calls"):
            f.write(f"SLOW CALLS ({len(report['slow_calls'])})\n")
            f.write("-"*40 + "\n")
            for call in report["slow_calls"][:10]:
                f.write(f"• {call['group']} (chunk {call['chunk']}): {call['duration']:.2f}s\n")
            if len(report["slow_calls"]) > 10:
                f.write(f"  ... and {len(report['slow_calls']) - 10} more\n")
    
    logger.info(f"📊 Performance visualization saved to {viz_path}")