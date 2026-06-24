import unittest

if __name__ == '__main__':
    # 自动发现test_cases目录下所有测试用例
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('test_cases', pattern='test_*.py')

    # 运行测试并生成报告
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_runner.run(test_suite)
