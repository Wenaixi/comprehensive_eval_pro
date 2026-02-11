import os
import shutil
import datetime
import sys

def archive_assets():
    """
    一键归档资源目录：备份 assets 到 assets_backups 并重建空目录。
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    backups_root = os.path.join(base_dir, "assets_backups")
    
    if not os.path.exists(assets_dir):
        print(f"[!] 错误: 未找到资源目录 {assets_dir}")
        return

    # 1. 准备备份目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join(backups_root, f"archive_{timestamp}")
    
    if not os.path.exists(backups_root):
        os.makedirs(backups_root)
    
    print(f"[*] 正在启动归档流程...")
    print(f"[*] 目标备份路径: {archive_dir}")

    # 2. 执行原子归档 (移动目录)
    try:
        shutil.move(assets_dir, archive_dir)
        print(f"[+] 归档成功！原始资源已安全移至备份目录。")
    except Exception as e:
        print(f"[!] 归档失败: {e}")
        return

    # 3. 重建基础结构
    print(f"[*] 正在重建基础资源架构...")
    task_types = ["劳动", "军训", "主题班会", "国旗下讲话"]
    os.makedirs(assets_dir, exist_ok=True)
    
    for tt in task_types:
        path = os.path.join(assets_dir, tt)
        os.makedirs(path, exist_ok=True)
        # 创建 .gitkeep 保持目录结构
        with open(os.path.join(path, ".gitkeep"), "w") as f:
            pass
        print(f"    - 已重建: assets/{tt}")

    print(f"\n[✨] 换届归档完成！现在你可以开始为新学期投放资源了。")

if __name__ == "__main__":
    # 简单的二次确认
    print("="*50)
    print("           资源换届一键归档工具")
    print("="*50)
    print("警告：此操作将移动所有当前资源到备份文件夹并清空 assets 目录。")
    confirm = input("确定要继续吗？(y/N): ").strip().lower()
    
    if confirm == 'y':
        archive_assets()
    else:
        print("[*] 操作已取消。")
