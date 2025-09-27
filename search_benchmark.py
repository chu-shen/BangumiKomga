import json
import mmap
import random
import sys
import os
from bangumi_archive.local_archive_searcher import search_all_data, _search_all_data_with_index

# 添加项目根目录到 sys.path，确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置
file_path = "archivedata/subject.jsonlines"
samples_size = 200
is_save_report = False


def sample_subjects(input_file, sample_size: int, output_file=None):
    if sample_size <= 0:
        raise ValueError("sample_size 必须大于 0")
    file_size = os.path.getsize(input_file)
    if file_size == 0:
        raise ValueError("文件为空")
    offsets = []
    print("正在扫描文件，构建行偏移索引...")
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
    file_path: str,
    sample_size: int,
    search_func,
    is_save_report: bool = False
):
    """
    动态评估任意搜索函数的召回效果。
    :param file_path: 数据文件路径 (.jsonlines)
    :param sample_size: 采样数量
    :param search_func: 要测试的搜索函数，必须接受 (file_path, query) 两个参数
    :param is_save_report: 是否保存评估结果到 JSON
    """
    print("🔍 开始采样...")
    data_samples = sample_subjects(file_path, sample_size)
    print(f"✅ 采样完成，共 {len(data_samples)} 条记录\n")

    # 构建 query-ground truth 对
    query_gt_pairs = []
    for item in data_samples:
        name_cn = item.get("name_cn", "").strip()
        name = item.get("name", "").strip()
        item_id = item.get("id")
        query = name_cn if name_cn else name
        if not query:
            continue
        query_gt_pairs.append({
            "query": query,
            "ground_truth_id": item_id,
        })
    print(f"📌 成功构建 {len(query_gt_pairs)} 个 query-ground truth 对")
    if query_gt_pairs:
        print(
            f"示例 query: '{query_gt_pairs[0]['query']}' (ID: {query_gt_pairs[0]['ground_truth_id']})\n")

    # 执行搜索评估
    results_per_query = []
    tp_query_count = 0  # query-level recall 计数
    tp_total = 0        # result-level precision 计数
    fp_total = 0
    total_queries = len(query_gt_pairs)

    print(f"🔍 开始对每个 query 执行检索（使用函数: {search_func.__name__}）...")
    for i, pair in enumerate(query_gt_pairs, 1):
        query = pair["query"]
        gt_id = pair["ground_truth_id"]

        search_results = search_func(file_path, query)
        returned_ids = [r.get("id") for r in search_results]

        # Query-level recall
        found_in_results = gt_id in returned_ids
        if found_in_results:
            tp_query_count += 1

        # Result-level precision
        tp_total += sum(1 for rid in returned_ids if rid == gt_id)
        fp_total += sum(1 for rid in returned_ids if rid != gt_id)

        results_per_query.append({
            "query": query,
            "gt_id": gt_id,
            "found": found_in_results,
            "search_results_count": len(returned_ids),
            "search_results_ids": returned_ids
        })

        if i % 100 == 0:
            print(f"  已处理 {i}/{total_queries}，已召回 {tp_query_count} 条")

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

    print("\n" + "="*70)
    print("📊 评估报告")
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
    print("="*70)

    # 错误样例
    failed_queries = [r for r in results_per_query if not r["found"]][:5]
    print(f"\n❌ 前 5 个未召回的查询（FN）:")
    for i, r in enumerate(failed_queries, 1):
        print(f"  {i}. Query: '{r['query']}' (ID: {r['gt_id']})")
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
            "failed_queries": [
                {
                    "query": r["query"],
                    "gt_id": r["gt_id"],
                    "search_results_count": r["search_results_count"],
                    "search_results_ids": r["search_results_ids"]
                }
                for r in failed_queries
            ]
        }
        eval_file = "evaluation_results.json"
        with open(eval_file, 'w', encoding='utf-8') as f:
            json.dump(output_eval, f, ensure_ascii=False, indent=2)
        print(f"\n 评估结果已保存至: {eval_file}")

    return {
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "top1_accuracy": top1_accuracy,
        "search_function": f"{search_func.__module__}.{search_func.__name__}",
        "total_queries": total_queries,
        "tp_count": tp_query_count
    }


if __name__ == "__main__":
    # 测试 search_all_data
    # print("\n测试 search_all_data")
    # evaluate_search_function(
    #     file_path=file_path,
    #     sample_size=samples_size,
    #     search_func=search_all_data,
    #     is_save_report=is_save_report
    # )
    print("\n测试 _search_all_data_with_index")
    evaluate_search_function(
        file_path=file_path,
        sample_size=samples_size,
        search_func=_search_all_data_with_index,
        is_save_report=is_save_report
    )
