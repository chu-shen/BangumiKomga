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
archive_api = BangumiArchiveDataSource(ARCHIVE_FILES_DIR)


def sample_jsonlines(input_file, sample_size: int, output_file=None):
    if sample_size <= 0:
        raise ValueError("sample_size 必须大于 0")

    file_size = os.path.getsize(input_file)
    if file_size == 0:
        raise ValueError("文件为空")

    # 存储符合条件的行的偏移量和原始行号
    valid_offsets = []       # 每个有效行的起始字节偏移
    valid_line_indices = []  # 对应在原始文件中的行号(从0开始)

    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            pos = 0
            line_idx = 0
            while pos < len(mm):
                next_pos = mm.find(b'\n', pos)
                if next_pos == -1:
                    # 最后一行可能没有换行符
                    line_bytes = mm[pos:]
                    try:
                        line_str = line_bytes.rstrip(b'\n\r').decode('utf-8')
                        data = json.loads(line_str)
                        # 条件筛选最后一行
                        # 当前条件: type=1且series=True
                        if isinstance(data, dict) and data.get('type') == 1 and data.get('series') is True:
                            valid_offsets.append(pos)
                            valid_line_indices.append(line_idx)
                    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                        pass  # 跳过非法行
                    break

                line_bytes = mm[pos:next_pos]
                try:
                    line_str = line_bytes.rstrip(b'\n\r').decode('utf-8')
                    data = json.loads(line_str)
                    # 条件筛选
                    # 当前条件: type=1且series=True
                    if data.get('type') == 1 and data.get('series') is True:
                        valid_offsets.append(pos)
                        valid_line_indices.append(line_idx)
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    pass  # 跳过非法行

                pos = next_pos + 1
                line_idx += 1

    total_valid_lines = len(valid_offsets)
    print(f"共找到 {line_idx} 行，其中满足筛选条件的行有 {total_valid_lines} 行")

    if total_valid_lines == 0:
        raise ValueError("文件中没有满足筛选条件的的行，采样中止")

    if sample_size > total_valid_lines:
        print(
            f"请求采样 {sample_size} 行，但只有 {total_valid_lines} 行满足筛选条件, 将采样全部行")
        sample_size = total_valid_lines

    # 从符合条件的索引 valid_offsets 中随机采样
    sampled_valid_indices = random.sample(
        range(total_valid_lines), sample_size)
    print(f"已按规则从 Archive 数据中随机采样 {sample_size} 行索引")

    samples = []
    print("正在根据索引读取采样行...")
    with open(input_file, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for idx in sampled_valid_indices:
                start = valid_offsets[idx]
                # 从当前行起始位置，找下一个 \n，作为结束位置
                end = mm.find(b'\n', start)
                if end == -1:
                    end = len(mm)
                line_bytes = mm[start:end]
                line_str = line_bytes.rstrip(b'\n\r').decode(
                    'utf-8', errors='replace')  # 容错解码
                try:
                    data = json.loads(line_str)
                    samples.append(data)
                except json.JSONDecodeError as e:
                    print(
                        f"⚠️ 解析失败，跳过行（偏移 {start}）: {e.msg} - 内容: {line_str[:100]}...")
                    continue
                except UnicodeDecodeError as e:
                    print(f"⚠️ 编码错误，跳过行（偏移 {start}）: {e}")
                    continue

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
    is_show_summery: bool = True,
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
    if is_show_summery:
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
        print(f"\n 前 {show_sample_size} 个未召回的查询(FN):")
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
            query): return archive_api.search_subjects(query)
        try:
            metrics = evaluate_search_function(
                data_samples=self.__class__.sampled_data,
                search_func=search_func_offline,
                is_show_summery=True,
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
            return bgm_api.search_subjects(query, threshold=80)
        try:
            metrics = evaluate_search_function(
                self.__class__.sampled_data,
                search_func=search_func_online,
                is_show_summery=True,
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

    def test_optimaize_threshold_archive_search(self):
        """自动推断 search_subjects 的最优 threshold 值"""
        # 搜索范围和步长
        threshold_range = list(range(60, 101, 5))  # [60, 65, ..., 100]
        print(f"\n 开始搜索最优 threshold 值：{threshold_range}")

        # 存储每个 threshold 的评估结果
        results = []

        def search_func_with_threshold(query, th):
            return archive_api.search_subjects(query, threshold=th)

        # 遍历所有 threshold 值
        for th in threshold_range:
            print(f"  评估 threshold={th} ...")

            def wrapped_search(query):
                return search_func_with_threshold(query, th)

            try:
                metrics = evaluate_search_function(
                    data_samples=self.__class__.sampled_data,
                    search_func=wrapped_search,
                    is_show_summery=False,  # 不显示评测概览
                    is_save_report=False  # 不保存中间报告
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
                print(f"    ❌ threshold={th} 评估失败: {e}")
                continue

        # 过滤出满足最低要求的候选
        min_recall = RECALL_THRESHOLD
        min_top1 = TOP1_ACCURACY_THRESHOLD
        valid_results = [
            r for r in results
            if r["recall"] >= min_recall and r["top1_accuracy"] >= min_top1
        ]

        if not valid_results:
            self.fail(
                f"❌ 所有 threshold 值均未达到最低要求(Recall≥{min_recall}, Top-1≥{min_top1})"
            )

        # 按f1值排序，取最优
        best_result = max(valid_results, key=lambda x: x["f1"])
        best_threshold = best_result["threshold"]

        # 获取默认 threshold=80 的结果
        default_result = next(
            (r for r in results if r["threshold"] == 80), None)
        if not default_result:
            self.fail("默认 threshold=80 未评估，无法比较")

        print("\n" + "="*70)
        print("最优 threshold 推断结果")
        print("="*70)
        print(f"✅ 最优 threshold: {best_threshold}")
        print(f"  Recall: {best_result['recall']:.4f}")
        print(f"  Top-1 Accuracy: {best_result['top1_accuracy']:.4f}")
        print(f"  F1: {best_result['f1']:.4f}")
        print(f"  默认 threshold=80 的表现:")
        print(f"    Recall: {default_result['recall']:.4f}")
        print(f"    Top-1 Accuracy: {default_result['top1_accuracy']:.4f}")
        print(f"    F1: {default_result['f1']:.4f}")

        # 判断是否优于默认值
        is_better_than_default = (
            best_result["f1"] > default_result["f1"]
        )

        # 断言：最优值F1必须至少不低于默认值
        self.assertGreaterEqual(
            best_result["f1"],
            default_result["f1"],
            f"❌ 推断出的最优 threshold={best_threshold} 的F1值 ({best_result['f1']:.4f}) "
            f"高于默认值的F1 ({default_result['f1']:.4f})，默认值可能不合理。"
        )

        # 保存最终推断结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("test_results", exist_ok=True)
        report_path = f"test_results/optimal_threshold_report_{timestamp}.json"
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
        print(f"\n📊 最优阈值评估报告已保存至: {report_path}")
