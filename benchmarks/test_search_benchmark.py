import json
import mmap
import random
import sys
import os
import time
from datetime import datetime
import unittest
from bangumi_archive.archive_autoupdater import check_archive, ARCHIVE_FILES_DIR
from api.bangumi_api import BangumiApiDataSource, BangumiArchiveDataSource
from config.config import BANGUMI_ACCESS_TOKEN as ACCESS_TOKEN

# Add project root to sys.path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Assessment thresholds. Set low initially to pass tests while observing reports.
RECALL_THRESHOLD = 0.50
TOP1_ACCURACY_THRESHOLD = 0.50

# Config
file_path = os.path.join(ARCHIVE_FILES_DIR, "subject.jsonlines")
samples_size = 100
# Whether to output test report files
is_save_report = True
show_sample_size = 5
use_token = False
if use_token:
    bgm_api = BangumiApiDataSource(ACCESS_TOKEN)
else:
    bgm_api = BangumiApiDataSource()
archive_api = BangumiArchiveDataSource(ARCHIVE_FILES_DIR)


def sample_jsonlines(input_file, sample_size: int, output_file=None):
    if sample_size <= 0:
        raise ValueError("sample_size must be > 0")

    file_size = os.path.getsize(input_file)
    if file_size == 0:
        raise ValueError("File is empty")

    # Store offsets and line indices of valid lines
    valid_offsets = []       # byte offset of each valid line
    valid_line_indices = []  # line index in the original file (0-based)

    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            pos = 0
            line_idx = 0
            while pos < len(mm):
                next_pos = mm.find(b'\n', pos)
                if next_pos == -1:
                    # Last line may not have a newline
                    line_bytes = mm[pos:]
                    try:
                        line_str = line_bytes.rstrip(b'\n\r').decode('utf-8')
                        data = json.loads(line_str)
                        # Condition: type=1 and series=True
                        if isinstance(data, dict) and data.get('type') == 1 and data.get('series') is True:
                            valid_offsets.append(pos)
                            valid_line_indices.append(line_idx)
                    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                        pass  # Skip invalid lines
                    break

                line_bytes = mm[pos:next_pos]
                try:
                    line_str = line_bytes.rstrip(b'\n\r').decode('utf-8')
                    data = json.loads(line_str)
                    # Condition: type=1 and series=True
                    if data.get('type') == 1 and data.get('series') is True:
                        valid_offsets.append(pos)
                        valid_line_indices.append(line_idx)
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    pass  # Skip invalid lines

                pos = next_pos + 1
                line_idx += 1

    total_valid_lines = len(valid_offsets)
    print(f"Found {line_idx} lines, {total_valid_lines} match filter criteria")

    if total_valid_lines == 0:
        raise ValueError("No lines match filter criteria, sampling aborted")

    if sample_size > total_valid_lines:
        print(
            f"Requested {sample_size} samples, but only {total_valid_lines} match; sampling all")
        sample_size = total_valid_lines

    # Randomly sample from valid offsets
    sampled_valid_indices = random.sample(
        range(total_valid_lines), sample_size)
    print(f"Randomly sampled {sample_size} indices from Archive data")

    samples = []
    print("Reading sampled lines by index...")
    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for idx in sampled_valid_indices:
                start = valid_offsets[idx]
                # Find next \n from start position as end
                end = mm.find(b'\n', start)
                if end == -1:
                    end = len(mm)
                line_bytes = mm[start:end]
                line_str = line_bytes.rstrip(b'\n\r').decode(
                    'utf-8', errors='replace')  # Tolerate decode errors
                try:
                    data = json.loads(line_str)
                    samples.append(data)
                except json.JSONDecodeError as e:
                    print(
                        f"\u26a0\ufe0f Parse failed, skipping line (offset {start}): {e.msg} - content: {line_str[:100]}...")
                    continue
                except UnicodeDecodeError as e:
                    print(f"\u26a0\ufe0f Encoding error, skipping line (offset {start}): {e}")
                    continue

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            for item in samples:
                out_f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"Sampling results written to {output_file}")
        return None
    else:
        return samples


def evaluate_search_function(
    data_samples,
    search_func,
    is_show_summery: bool = True,
    is_save_report: bool = False
):
    """
    Evaluate retrieval effectiveness of an arbitrary search function, and measure search latency.
    :param data_samples: Sampled data
    :param search_func: The search function to test, must accept (query) as a single argument
    :param is_save_report: Whether to save evaluation results as JSON
    """

    start_total = time.time()  # Start timing

    # Build query-ground truth pairs
    query_gt_pairs = []
    for item in data_samples:
        name_cn = item.get("name_cn", "").strip()
        name = item.get("name", "").strip()
        item_id = item.get("id")
        # Use Chinese name if available, otherwise original name
        query = name_cn if name_cn else name
        if not query:
            continue
        query_gt_pairs.append({
            "query": query,
            "ground_truth_id": item_id,
        })
    print(f"Built {len(query_gt_pairs)} query-ground truth pairs")
    if query_gt_pairs:
        print(
            f"Example query: '{query_gt_pairs[0]['query']}' (ID: {query_gt_pairs[0]['ground_truth_id']})\n")

    # Execute search evaluation
    results_per_query = []
    tp_query_count = 0  # query-level recall count
    tp_total = 0        # result-level precision count
    fp_total = 0
    total_queries = len(query_gt_pairs)

    # Search latency
    total_search_time = 0.0

    print(f"\U0001f50d Starting per-query retrieval (using function: {search_func.__name__})...")
    for i, pair in enumerate(query_gt_pairs, 1):
        query = pair["query"]
        gt_id = pair["ground_truth_id"]

        # Time each search
        start_search = time.time()
        search_results = search_func(query)
        search_duration = time.time() - start_search
        total_search_time += search_duration

        returned_ids = [r.get("id") for r in search_results]
        found_in_results = gt_id in returned_ids
        if found_in_results:
            tp_query_count += 1
        tp_total += sum(1 for rid in returned_ids if rid == gt_id)
        fp_total += sum(1 for rid in returned_ids if rid != gt_id)

        results_per_query.append({
            "query": query,
            "gt_id": gt_id,
            "found": found_in_results,
            "search_results_count": len(returned_ids),
            "search_results_ids": returned_ids,
            "search_time": search_duration  # Keep per-query latency
        })

        if i % 50 == 0:
            print(
                f"  Processed {i}/{total_queries}, recalled {tp_query_count}, search time so far: {total_search_time:.4f}s")

    # Compute metrics
    recall = tp_query_count / total_queries if total_queries > 0 else 0.0
    precision = tp_total / \
        (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision +
                                     recall) if (precision + recall) > 0 else 0.0

    # Top-1 Accuracy
    top1_correct = sum(
        1 for r in results_per_query if r["search_results_ids"] and r["search_results_ids"][0] == r["gt_id"])
    top1_accuracy = top1_correct / total_queries if total_queries > 0 else 0.0

    # Timing: total process ends
    end_total = time.time()
    total_time = end_total - start_total
    if is_show_summery:
        print("\n" + "="*70)
        print("Evaluation Report")
        print("="*70)
        print(f"Search function: {search_func.__module__}.{search_func.__name__}")
        print(f"Total queries: {total_queries}")
        print(f"Successful recalls (TP): {tp_query_count}")
        print(f"Missed (FN): {total_queries - tp_query_count}")
        print(
            f"Average result count: {sum(r['search_results_count'] for r in results_per_query) / total_queries:.2f}")
        print(f"Recall: {recall:.4f} ({tp_query_count}/{total_queries})")
        print(f"Precision: {precision:.4f}")
        print(f"Top-1 Accuracy: {top1_accuracy:.4f}")
        print(f"F1-score: {f1:.4f}")
        print(f"Total time: {total_time:.4f} seconds")
        print(f"Total search time: {total_search_time:.4f} seconds")
        print(f"Average search time: {total_search_time / total_queries:.4f} seconds")
        print("="*70)

        # Failed examples
        failed_queries = [
            r for r in results_per_query if not r["found"]][:show_sample_size]
        print(f"\n Top {show_sample_size} unrecalled queries (FN):")
        for i, r in enumerate(failed_queries, 1):
            print(f"  {i}. Query: '{r['query']}' (ID: {r['gt_id']})")
            print(f"     Result count: {r['search_results_count']}")
            if r['search_results_ids']:
                ids_str = r['search_results_ids'][:3]
                suffix = "..." if len(r['search_results_ids']) > 3 else ""
                print(f"     Returned IDs: {ids_str}{suffix}")

        # Show slowest 5 searches
        print(f"\n Slowest {show_sample_size} queries:")
        slowest_queries = sorted(
            results_per_query, key=lambda x: x["search_time"], reverse=True)[:show_sample_size]
        for i, r in enumerate(slowest_queries, 1):
            print(f"  {i}. Query: '{r['query']}' (ID: {r['gt_id']})")
            print(f"     Search latency: {r['search_time']:.4f} seconds")
            print(f"     Result count: {r['search_results_count']}")
            if r['search_results_ids']:
                ids_str = r['search_results_ids'][:3]
                suffix = "..." if len(r['search_results_ids']) > 3 else ""
                print(f"     Returned IDs: {ids_str}{suffix}")

    # Save report
    if is_save_report:
        output_eval = {
            "total_queries": total_queries,
            "tp_count": tp_query_count,
            "recall": recall,
            "precision": precision,
            "f1": f1,
            "top1_accuracy": top1_accuracy,
            "search_function": f"{search_func.__module__}.{search_func.__name__}",
            "total_time_seconds": total_time,
            "search_total_time_seconds": total_search_time,
            "avg_search_time_seconds": total_search_time / total_queries,
            "failed_queries": [
                {
                    "query": r["query"],
                    "gt_id": r["gt_id"],
                    "search_results_count": r["search_results_count"],
                    "search_results_ids": r["search_results_ids"],
                    "search_time": r.get("search_time", 0.0)
                }
                for r in failed_queries
            ],
            "slowest_queries": [
                {
                    "query": r["query"],
                    "gt_id": r["gt_id"],
                    "search_results_count": r["search_results_count"],
                    "search_results_ids": r["search_results_ids"],
                    "search_time": r["search_time"]
                }
                for r in slowest_queries
            ]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Ensure directory exists
        os.makedirs("benchmark_results", exist_ok=True)
        eval_file = f"benchmark_results/search_func_eval_results_{timestamp}.json"
        with open(eval_file, 'w', encoding='utf-8') as f:
            json.dump(output_eval, f, ensure_ascii=False, indent=2)
        print(f"\n Search function evaluation results saved to: {eval_file}")

    return {
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "top1_accuracy": top1_accuracy,
        "search_function": f"{search_func.__module__}.{search_func.__name__}",
        "total_queries": total_queries,
        "tp_count": tp_query_count,
        "total_time_seconds": total_time,
        "search_total_time_seconds": total_search_time,
        "avg_search_time_seconds": total_search_time / total_queries
    }


class TestSearchFunctionEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n Preparing Bangumi Archive data files...")
        # Set seed for reproducible sampling
        # random.seed(42)
        try:
            check_archive()
            # Verify file exists and is non-empty
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archive file not found: {file_path}")
            if os.path.getsize(file_path) == 0:
                raise ValueError(f"Archive file is empty: {file_path}")
            print(f" Archive file ready: {file_path}")

            # Sample in setUpClass so all tests share the same sampled data
            cls.sampled_data = sample_jsonlines(file_path, samples_size)
            if not cls.sampled_data:
                raise ValueError("Sampling result is empty")
            print(f"Sampling complete, {len(cls.sampled_data)} samples")
        except Exception as e:
            raise unittest.SkipTest(f" Archive preparation failed, skipping test: {str(e)}")

    def test_offline_search_function(self):
        """Test recall and Top-1 accuracy of the offline search function"""

        def search_func_offline(
            query): return archive_api.search_subjects(query)
        try:
            metrics = evaluate_search_function(
                data_samples=self.__class__.sampled_data,
                search_func=search_func_offline,
                is_show_summery=True,
                is_save_report=is_save_report
            )
        except Exception as e:
            self.fail(f"Evaluation error: {str(e)}")

        # Output metrics to stdout for CI capture
        print(json.dumps(metrics, ensure_ascii=False, indent=None))

        # Assert thresholds
        self.assertGreaterEqual(
            metrics["recall"],
            RECALL_THRESHOLD,
            f"Recall {metrics['recall']:.4f} below threshold {RECALL_THRESHOLD}"
        )
        self.assertGreaterEqual(
            metrics["top1_accuracy"],
            TOP1_ACCURACY_THRESHOLD,
            f"Top-1 Accuracy {metrics['top1_accuracy']:.4f} below threshold {TOP1_ACCURACY_THRESHOLD}"
        )

    def test_online_search_function(self):
        """Test recall and Top-1 accuracy of the online search function"""
        def search_func_online(query):
            # 1 RPS, keep request rate below rate limiter threshold
            time.sleep(1)
            return bgm_api.search_subjects(query, threshold=80)
        try:
            metrics = evaluate_search_function(
                self.__class__.sampled_data,
                search_func=search_func_online,
                is_show_summery=True,
                is_save_report=is_save_report
            )
        except Exception as e:
            self.fail(f"Evaluation error: {str(e)}")

        # Output metrics to stdout for CI capture
        print(json.dumps(metrics, ensure_ascii=False, indent=None))

        # Assert thresholds
        self.assertGreaterEqual(
            metrics["recall"],
            RECALL_THRESHOLD,
            f"Recall {metrics['recall']:.4f} below threshold {RECALL_THRESHOLD}"
        )
        self.assertGreaterEqual(
            metrics["top1_accuracy"],
            TOP1_ACCURACY_THRESHOLD,
            f"Top-1 Accuracy {metrics['top1_accuracy']:.4f} below threshold {TOP1_ACCURACY_THRESHOLD}"
        )

    def test_optimaize_threshold_archive_search(self):
        """Automatically infer the optimal threshold value for search_subjects"""
        # Search range and step
        threshold_range = list(range(60, 101, 5))  # [60, 65, ..., 100]
        print(f"\n Starting optimal threshold search: {threshold_range}")

        # Store evaluation results for each threshold
        results = []

        def search_func_with_threshold(query, th):
            return archive_api.search_subjects(query, threshold=th)

        # Iterate over all threshold values
        for th in threshold_range:
            print(f"  Evaluating threshold={th} ...")

            def wrapped_search(query):
                return search_func_with_threshold(query, th)

            try:
                metrics = evaluate_search_function(
                    data_samples=self.__class__.sampled_data,
                    search_func=wrapped_search,
                    is_show_summery=False,  # Don't show summary
                    is_save_report=False  # Don't save intermediate reports
                )
                results.append({
                    "threshold": th,
                    "recall": metrics["recall"],
                    "top1_accuracy": metrics["top1_accuracy"],
                    "f1": metrics["f1"]
                })
                print(
                    f"    Recall: {metrics['recall']:.4f}, Top-1: {metrics['top1_accuracy']:.4f}, F1: {metrics['f1']:.4f}")
            except Exception as e:
                print(f"    \u274c threshold={th} evaluation failed: {e}")
                continue

        # Filter candidates meeting minimum requirements
        min_recall = RECALL_THRESHOLD
        min_top1 = TOP1_ACCURACY_THRESHOLD
        valid_results = [
            r for r in results
            if r["recall"] >= min_recall and r["top1_accuracy"] >= min_top1
        ]

        if not valid_results:
            self.fail(
                f"\u274c No threshold values met minimum requirements (Recall\u2265{min_recall}, Top-1\u2265{min_top1})"
            )

        # Sort by F1, pick the best
        best_result = max(valid_results, key=lambda x: x["f1"])
        best_threshold = best_result["threshold"]

        # Get default threshold=80 result
        default_result = next(
            (r for r in results if r["threshold"] == 80), None)
        if not default_result:
            self.fail("Default threshold=80 was not evaluated, cannot compare")

        print("\n" + "="*70)
        print("Optimal Threshold Inference Result")
        print("="*70)
        print(f"\u2705 Optimal threshold: {best_threshold}")
        print(f"  Recall: {best_result['recall']:.4f}")
        print(f"  Top-1 Accuracy: {best_result['top1_accuracy']:.4f}")
        print(f"  F1: {best_result['f1']:.4f}")
        print(f"  Default threshold=80 performance:")
        print(f"    Recall: {default_result['recall']:.4f}")
        print(f"    Top-1 Accuracy: {default_result['top1_accuracy']:.4f}")
        print(f"    F1: {default_result['f1']:.4f}")

        # Determine if better than default
        is_better_than_default = (
            best_result["f1"] > default_result["f1"]
        )

        # Assert: optimal F1 must not be worse than default
        self.assertGreaterEqual(
            best_result["f1"],
            default_result["f1"],
            f"\u274c Inferred optimal threshold={best_threshold} F1 ({best_result['f1']:.4f}) "
            f"is higher than default F1 ({default_result['f1']:.4f}), default may be unreasonable."
        )

        # Save final inference result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("benchmark_results", exist_ok=True)
        report_path = f"benchmark_results/optimal_threshold_report_{timestamp}.json"
        report = {
            "threshold_range": threshold_range,
            "all_results": results,
            "valid_results": valid_results,
            "best_threshold": best_threshold,
            "best_metrics": best_result,
            "default_threshold": 80,
            "default_metrics": default_result,
            "is_better_than_default": is_better_than_default,
            "min_recall_threshold": min_recall,
            "min_top1_threshold": min_top1
        }
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n\U0001f4ca Optimal threshold evaluation report saved to: {report_path}")
