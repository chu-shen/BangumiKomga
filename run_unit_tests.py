import os
import sys
import unittest
from datetime import datetime
import xml.etree.ElementTree as ET
from bangumi_archive.archive_autoupdater import check_archive
# coverage 不应纳入 requirements.txt, 仅在GithubAction中使用
import coverage

# 添加源代码路径
sys.path.insert(0, os.path.abspath('src'))


def prepare_archive():
    check_archive()


def write_junit_xml(result, filename):
    testsuite = ET.Element("testsuite", name="MyTests",
                           tests=str(result.testsRun))
    for test, exc in result.failures + result.errors:
        testcase = ET.SubElement(testsuite, "testcase", name=str(test))
        failure = ET.SubElement(testcase, "failure")
        failure.text = exc
    tree = ET.ElementTree(testsuite)
    tree.write(filename, encoding="utf-8", xml_declaration=True)


def run_unit_tests():
    # 初始化覆盖率收集
    cov = coverage.Coverage(
        include=[
            "api/*.py",
            "bangumi_archive/*.py",
            "config/*.py",
            "core/*.py",
            "scripts/*.py",
            "services/*.py",
            "tools/*.py",
            "*.py",
        ],
        omit=[
            "*__pycache__*",
            "*tests*",
            "*test_results*",
            "*archivedata*",
            "*logs*",
            # 排除标准库和第三方库
            "*/lib/*",
        ],
    )
    cov.start()

    # 创建测试报告目录
    report_dir = "test_results"
    os.makedirs(report_dir, exist_ok=True)

    loader = unittest.TestLoader()
    # 自动发现 tests 下的所有 test_ 开头的测试用例
    suite = loader.discover(
        start_dir='tests',
        pattern='test_*.py'
    )

    # 生成带时间戳的报告文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(report_dir, f"test_report_{timestamp}.txt")

    # 使用 TextTestRunner 执行测试并输出到文件
    with open(report_file, 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)

    # 输出 JUnit XML 格式报告
    # xml_report_file = os.path.join(report_dir, f"test_report_{timestamp}.xml")
    # write_junit_xml(result, xml_report_file)
    # print(f"JUnit XML 报告已生成: {xml_report_file}")

    # 停止覆盖率收集
    cov.stop()
    cov.save()

    # 输出覆盖率报告
    coverage_report_file = os.path.join(
        report_dir, f"coverage_report_{timestamp}.txt")
    with open(coverage_report_file, "w") as f:
        cov.report(file=f)

    # 输出简要结果到控制台
    print(f"\n测试执行完成，报告已保存至: {report_file}")
    print(f"测试用例总数: {result.testsRun}")
    print(f"忽略的用例数: {len(result.skipped)}")
    print(f"失败的用例数: {len(result.failures)}")
    print(f"错误的用例数: {len(result.errors)}")
    print(f"\n代码覆盖率：{cov.report():.2f}%")

    # 返回失败用例数量作为退出码
    return len(result.failures) + len(result.errors)


if __name__ == '__main__':
    prepare_archive()
    exit_code = run_unit_tests()
    sys.exit(exit_code)
