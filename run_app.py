import sys
import os
import socket
import streamlit.web.cli as stcli
from app import *
def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def find_free_port(start_port: int = 8501, max_tries: int = 20) -> int:
    """从 start_port 开始，找到可用端口"""
    port = start_port
    for _ in range(max_tries):
        if not is_port_in_use(port):
            return port
        port += 1
    raise RuntimeError(f"没有找到可用端口（尝试范围: {start_port}-{start_port+max_tries}）")

def run_streamlit(script_path, port=8501, cors=False, dev_mode=False):
    # 控制 developmentMode
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false" if not dev_mode else "true"

    args = ["streamlit", "run", script_path]

    if not cors:
        args.append("--server.enableCORS=false")
    if port:
        args.append(f"--server.port={port}")

    sys.argv = args

    print(f"\n  正在启动 Streamlit 应用：{script_path}")
    print(f"  端口: {port} | CORS={cors} | dev_mode={dev_mode}\n")

    try:
        return stcli.main()
    except Exception as e:
        print("❌ 程序运行出错:", e)
        return 1


def main():
    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    script_path = os.path.join(current_dir, "app.py")

    if not os.path.exists(script_path):
        print(f"❌ 没找到目标脚本: {script_path}")
        input("按回车键退出...")
        sys.exit(1)

    # 保持在 run_app.py 所在目录，保证能找到 main 包
    os.chdir(current_dir)
    os.environ["PYTHONPATH"] = current_dir + os.pathsep + os.environ.get("PYTHONPATH", "")

    # ===== 默认配置 =====
    port = find_free_port(8501)  # 自动找可用端口
    dev_mode = False

    # ===== 初次运行 =====
    exit_code = run_streamlit(script_path, port=port, dev_mode=dev_mode)

    # ===== 如果失败，进入调试模式 =====
    while exit_code != 0:
        print("\n⚙️ 调试选项：")
        print("1. 修改端口号")
        print("2. 切换开发模式 (dev_mode)")
        print("3. 自动寻找新端口")
        print("4. 退出程序")

        choice = input("请选择操作 (1/2/3/4): ").strip()
        if choice == "1":
            new_port = input("请输入新的端口号 (默认 8501): ").strip()
            port = int(new_port) if new_port.isdigit() else 8501
        elif choice == "2":
            dev_mode = not dev_mode
            print(f"✅ 已切换开发模式: {dev_mode}")
        elif choice == "3":
            port = find_free_port(port + 1)
            print(f"✅ 已切换到新端口: {port}")
        elif choice == "4":
            break
        else:
            print("无效输入，请重新选择。")
            continue

        exit_code = run_streamlit(script_path, port=port, dev_mode=dev_mode)

    input("\n程序已结束，按回车键退出...")


if __name__ == "__main__":
    main()