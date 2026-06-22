import os
import sys
import unittest
from datetime import datetime

# Ensure project root is on sys.path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_benchmarks():
    """Discover and run all benchmark tests under the benchmarks/ directory."""
    os.makedirs("benchmark_results", exist_ok=True)

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(__file__),
        pattern='test_*.py'
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join("benchmark_results", f"benchmark_report_{timestamp}.txt")

    with open(report_file, 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)

    # Summary to stdout for CI capture
    print(f"\nBenchmark execution complete. Report saved to: {report_file}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    return len(result.failures) + len(result.errors)


if __name__ == '__main__':
    exit_code = run_benchmarks()
    sys.exit(exit_code)
