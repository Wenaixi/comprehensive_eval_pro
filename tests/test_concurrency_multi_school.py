import os
import sys
import threading
import shutil
import tempfile
import unittest
import random
from pathlib import Path

# 允许从根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.summary_log import append_summary
from comprehensive_eval_pro.config_store import load_json_config, save_json_config

class TestConcurrencyMultiSchool(unittest.TestCase):
    """
    深度并发测试：模拟多学校、多账号、多线程的高并发场景。
    验证：
    1. 目录创建的原子性（多线程同时创建相同或不同目录）。
    2. 日志写入的线程安全性（跨文件与同文件混合）。
    3. 配置存储的原子性（ConfigStore 的 os.replace 机制）。
    """
    
    def setUp(self):
        # 使用 realpath 避免 Windows 短路径问题
        self.test_root = os.path.realpath(tempfile.mkdtemp(prefix="cep_concurrency_"))
        self.log_dir = os.path.join(self.test_root, "runtime", "logs")
        self.config_path = os.path.join(self.test_root, "config.json")
        self.example_config_path = os.path.join(self.test_root, "config.example.json")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 创建示例配置
        with open(self.example_config_path, "w", encoding="utf-8") as f:
            f.write('{"model": "test-model", "accounts": {}}')

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def test_multi_school_log_and_config_stress(self):
        """
        压力测试：5个学校，每个学校10个账号，每个账号并发写入20条记录。
        同时混杂 ConfigStore 的频繁读写。
        """
        num_schools = 5
        accounts_per_school = 10
        writes_per_account = 20
        
        schools = [f"学校_{i}" for i in range(num_schools)]
        grades = ["高一", "高二", "高三"]
        classes = ["1班", "2班", "3班"]
        
        # 准备账号池
        account_pool = []
        for s in schools:
            for a in range(accounts_per_school):
                username = f"user_{s}_{a}"
                user_info = {
                    "studentSchoolInfo": {
                        "schoolName": s,
                        "gradeName": random.choice(grades),
                        "className": random.choice(classes)
                    }
                }
                account_pool.append((username, user_info))

        errors = []
        
        def log_worker(username, user_info):
            try:
                for i in range(writes_per_account):
                    append_summary(
                        username=username,
                        user_info=user_info,
                        task_name=f"并发任务_{i}",
                        ok=True,
                        msg="SUCCESS",
                        log_dir=self.log_dir
                    )
            except Exception as e:
                errors.append(f"Log Error [{username}]: {e}")

        def config_worker():
            try:
                for i in range(50):
                    # 频繁修改配置
                    config = load_json_config(self.config_path)
                    config[f"key_{random.randint(1, 100)}"] = "value"
                    save_json_config(config, self.config_path)
            except Exception as e:
                import traceback
                errors.append(f"Config Error: {e}\n{traceback.format_exc()}")

        threads = []
        # 启动日志线程
        for acc in account_pool:
            t = threading.Thread(target=log_worker, args=acc)
            threads.append(t)
            
        # 启动配置干扰线程
        for _ in range(5):
            t = threading.Thread(target=config_worker)
            threads.append(t)

        # 随机启动
        random.shuffle(threads)
        for t in threads:
            t.start()
            
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(len(errors), 0, f"并发测试中出现异常: {errors}")
        
        # 验证每个账号的日志行数
        for username, user_info in account_pool:
            ssi = user_info["studentSchoolInfo"]
            log_path = os.path.join(
                self.log_dir, 
                ssi["schoolName"], 
                ssi["gradeName"], 
                ssi["className"], 
                f"{username}.log"
            )
            self.assertTrue(os.path.exists(log_path), f"日志缺失: {log_path}")
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), writes_per_account, f"账号 {username} 日志行数不对")

        # 验证配置存储是否可读且有效
        final_config = load_json_config(self.config_path)
        self.assertTrue(len(final_config) > 0)

if __name__ == "__main__":
    unittest.main()
