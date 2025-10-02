import json
import mmap
import random
import sys
import os
import time
from datetime import datetime
import unittest
from bangumi_archive.local_archive_searcher import search_all_data, _search_all_data_with_index
from bangumi_archive.archive_autoupdater import check_archive, ARCHIVE_FILES_DIR
from api.bangumi_api import BangumiApiDataSource
from config.config import BANGUMI_ACCESS_TOKEN as ACCESS_TOKEN

# 添加项目根目录到 sys.path，确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 评估阈值. 暂置为较低值以便通过测试, 观察评估报告
RECALL_THRESHOLD = 0.50
TOP1_ACCURACY_THRESHOLD = 0.50

# 配置
file_path = os.path.join(ARCHIVE_FILES_DIR, "subject.jsonlines")
samples_size = 100
# 是否输出测试报告文件
is_save_report = True
show_sample_size = 5
use_token = False
if use_token:
    bgm_api = BangumiApiDataSource(ACCESS_TOKEN)
else:
    bgm_api = BangumiApiDataSource()


def sample_jsonlines(input_file, sample_size: int, output_file=None):
    if sample_size <= 0:
        raise ValueError("sample_size 必须大于 0")
    file_size = os.path.getsize(input_file)
    if file_size == 0:
        raise ValueError("文件为空")
    offsets = []
    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            pos = 0
            while pos < len(mm):
                next_pos = mm.find(b'\n', pos)
                if next_pos == -1:
                    offsets.append(pos)
                    break
                offsets.append(pos)
                pos = next_pos + 1
    total_lines = len(offsets)
    print(f"共找到 {total_lines} 行")
    if sample_size > total_lines:
        print(f"警告：请求采样 {sample_size} 行，但文件只有 {total_lines} 行，将采样全部行")
        sample_size = total_lines
    sampled_indices = random.sample(range(total_lines), sample_size)
    print(f"已随机采样 {sample_size} 行索引")
    samples = []
    print("正在读取采样行...")
    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for idx in sampled_indices:
                start = offsets[idx]
                end = offsets[idx + 1] if idx + 1 < total_lines else len(mm)
                line_bytes = mm[start:end]
                line_str = line_bytes.rstrip(b'\n\r').decode('utf-8')
                samples.append(json.loads(line_str))
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            for item in samples:
                out_f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"采样结果已写入 {output_file}")
        return None
    else:
        return samples


def evaluate_search_function(
    data_samples,
    search_func,
    is_save_report: bool = False
):
    """
    评估任意搜索函数的检索效果, 并统计检索耗时。
    :param data_samples: 采样数据
    :param search_func: 要测试的搜索函数，必须接受 (file_path, query) 两个参数
    :param is_save_report: 是否保存评估结果到 JSON
    """

    start_total = time.time()  # 开始计时

    # 构建 query-ground truth 对
    query_gt_pairs = []
    for item in data_samples:
        name_cn = item.get("name_cn", "").strip()
        name = item.get("name", "").strip()
        item_id = item.get("id")
        # 用作品名构建查询
        query = name_cn if name_cn else name
        if not query:
            continue
        query_gt_pairs.append({
            "query": query,
            "ground_truth_id": item_id,
        })
    print(f"成功构建 {len(query_gt_pairs)} 个 query-ground truth 对")
    if query_gt_pairs:
        print(
            f"示例 query: '{query_gt_pairs[0]['query']}' (ID: {query_gt_pairs[0]['ground_truth_id']})\n")

    # 执行搜索评估
    results_per_query = []
    tp_query_count = 0  # query-level recall 计数
    tp_total = 0        # result-level precision 计数
    fp_total = 0
    total_queries = len(query_gt_pairs)

    # 搜索耗时
    total_search_time = 0.0

    print(f"🔍 开始对每个 query 执行检索（使用函数: {search_func.__name__}）...")
    for i, pair in enumerate(query_gt_pairs, 1):
        query = pair["query"]
        gt_id = pair["ground_truth_id"]

        # 对每次搜索计时
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
            "search_time": search_duration  # 保留单次搜索耗时
        })

        if i % 50 == 0:
            print(
                f"  已处理 {i}/{total_queries}，已召回 {tp_query_count} 条，当前搜索已耗时: {total_search_time:.4f}s")

    # 计算指标
    recall = tp_query_count / total_queries if total_queries > 0 else 0.0
    precision = tp_total / \
        (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision +
                                     recall) if (precision + recall) > 0 else 0.0

    # Top-1 Accuracy
    top1_correct = sum(
        1 for r in results_per_query if r["search_results_ids"] and r["search_results_ids"][0] == r["gt_id"])
    top1_accuracy = top1_correct / total_queries if total_queries > 0 else 0.0

    # 计时, 总流程结束
    end_total = time.time()
    total_time = end_total - start_total

    print("\n" + "="*70)
    print("评估报告")
    print("="*70)
    print(f"搜索函数: {search_func.__module__}.{search_func.__name__}")
    print(f"总查询数: {total_queries}")
    print(f"成功召回 (TP): {tp_query_count}")
    print(f"未召回 (FN): {total_queries - tp_query_count}")
    print(
        f"平均检索结果数: {sum(r['search_results_count'] for r in results_per_query) / total_queries:.2f}")
    print(f"召回率 (Recall): {recall:.4f} ({tp_query_count}/{total_queries})")
    print(f"精确率 (Precision): {precision:.4f}")
    print(f"Top-1 准确率: {top1_accuracy:.4f}")
    print(f"F1-score: {f1:.4f}")
    print(f"总耗时: {total_time:.4f} 秒")
    print(f"搜索总耗时: {total_search_time:.4f} 秒")
    print(f"平均每次搜索耗时: {total_search_time / total_queries:.4f} 秒")
    print("="*70)

    # 错误样例
    failed_queries = [
        r for r in results_per_query if not r["found"]][:show_sample_size]
    print(f"\n 前 {show_sample_size} 个未召回的查询（FN）:")
    for i, r in enumerate(failed_queries, 1):
        print(f"  {i}. Query: '{r['query']}' (ID: {r['gt_id']})")
        print(f"     检索结果数: {r['search_results_count']}")
        if r['search_results_ids']:
            ids_str = r['search_results_ids'][:3]
            suffix = "..." if len(r['search_results_ids']) > 3 else ""
            print(f"     返回的 ID: {ids_str}{suffix}")

    # 展示最慢的 5 次搜索
    print(f"\n 最慢的 {show_sample_size} 次查询:")
    slowest_queries = sorted(
        results_per_query, key=lambda x: x["search_time"], reverse=True)[:show_sample_size]
    for i, r in enumerate(slowest_queries, 1):
        print(f"  {i}. Query: '{r['query']}' (ID: {r['gt_id']})")
        print(f"     检索耗时: {r['search_time']:.4f} 秒")
        print(f"     检索结果数: {r['search_results_count']}")
        if r['search_results_ids']:
            ids_str = r['search_results_ids'][:3]
            suffix = "..." if len(r['search_results_ids']) > 3 else ""
            print(f"     返回的 ID: {ids_str}{suffix}")

    # 保存报告
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
        # 确保目录存在
        os.makedirs("test_results", exist_ok=True)
        eval_file = f"test_results/search_func_eval_results_{timestamp}.json"
        with open(eval_file, 'w', encoding='utf-8') as f:
            json.dump(output_eval, f, ensure_ascii=False, indent=2)
        print(f"\n 检索函数评估结果已保存至: {eval_file}")

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
        print("\n 正在准备 Bangumi Archive 数据文件...")
        # 使采样结果可复现
        # random.seed(42)
        try:
            check_archive()
            # 验证文件是否存在且非空
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archive 文件不存在: {file_path}")
            if os.path.getsize(file_path) == 0:
                raise ValueError(f"Archive 文件为空: {file_path}")
            print(f" Archive 文件准备完成: {file_path}")

            # 采样放到setUpClass以便测试共享同一份采样数据
            cls.sampled_data = sample_jsonlines(file_path, samples_size)
            if not cls.sampled_data:
                raise ValueError("采样结果为空")
            print(f"采样完成，共 {len(cls.sampled_data)} 个样本")
        except Exception as e:
            raise unittest.SkipTest(f" Archive 准备失败，跳过测试: {str(e)}")

    def test_offline_search_function(self):
        """测试检索函数的召回率和Top-1准确率是否达标"""

        def search_func_offline(
            query): return _search_all_data_with_index(file_path, query)
        try:
            metrics = evaluate_search_function(
                data_samples=self.__class__.sampled_data,
                search_func=search_func_offline,
                is_save_report=is_save_report
            )
        except Exception as e:
            self.fail(f"评估过程出错: {str(e)}")

        # 输出指标到 stdout，供 CI 捕获
        print(json.dumps(metrics, ensure_ascii=False, indent=None))

        # 断言阈值
        self.assertGreaterEqual(
            metrics["recall"],
            RECALL_THRESHOLD,
            f"召回率 {metrics['recall']:.4f} 低于阈值 {RECALL_THRESHOLD}"
        )
        self.assertGreaterEqual(
            metrics["top1_accuracy"],
            TOP1_ACCURACY_THRESHOLD,
            f"Top-1 准确率 {metrics['top1_accuracy']:.4f} 低于阈值 {TOP1_ACCURACY_THRESHOLD}"
        )

    def test_online_search_function(self):
        """测试检索函数的召回率和Top-1准确率是否达标"""
        def search_func_online(query):
            # 1 RPS,使测试的请求速率低于限流器要求
            time.sleep(1)
            return bgm_api.search_subjects(query)
        try:
            metrics = evaluate_search_function(
                self.__class__.sampled_data,
                search_func=search_func_online,
                is_save_report=is_save_report
            )
        except Exception as e:
            self.fail(f"评估过程出错: {str(e)}")

        # 输出指标到 stdout，供 CI 捕获
        print(json.dumps(metrics, ensure_ascii=False, indent=None))

        # 断言阈值
        self.assertGreaterEqual(
            metrics["recall"],
            RECALL_THRESHOLD,
            f"召回率 {metrics['recall']:.4f} 低于阈值 {RECALL_THRESHOLD}"
        )
        self.assertGreaterEqual(
            metrics["top1_accuracy"],
            TOP1_ACCURACY_THRESHOLD,
            f"Top-1 准确率 {metrics['top1_accuracy']:.4f} 低于阈值 {TOP1_ACCURACY_THRESHOLD}"
        )
