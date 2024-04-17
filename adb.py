import asyncio
import time

# 日志等级定义。根据日志等级打印不同重要性的信息，等级越低，信息越重要。
log_level = 4  # 1-5，可调整此值来控制日志输出

def log(message, level):
    # 日志输出函数，只有当设定的日志等级与消息等级匹配时才输出。
    if level == log_level or (level == 4 and log_level == 4):
        print(message)

# 设备的IP地址和端口
device_ip = "192.168.1.146:5555"
# 重新连接尝试的时间间隔（秒）
reconnect_interval = 0.1
# 检查应用程序的时间间隔（秒）
package_check_interval = 0.1
# 目标应用的关键词
target_package_keyword = "com.mitv.tvhome"
# 启动新应用的ADB命令
adb_command = "adb shell am start -n com.dangbei.tvlauncher/com.dangbei.launcher.ui.main.MainActivity -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -f 0x10000000"
# 禁用目标应用的ADB命令
disable_command = "adb shell pm disable-user --user 0 com.mitv.tvhome"
# 启用目标应用的ADB命令
enable_command = "adb shell pm enable com.mitv.tvhome"

async def run_adb_command(command):
    # 异步执行ADB命令并获取输出
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        return stdout
    else:
        # 处理命令执行失败的情况
        error_message = stderr.decode('utf-8', errors='ignore').strip()
        log(f"Command failed with error: {error_message}", 4)  # 4级日志用于错误信息
        return None

def parse_current_package(output):
    # 解析ADB命令返回的输出，找到当前焦点的应用程序包名
    for line in output.decode('utf-8', errors='ignore').splitlines():
        if "mCurrentFocus" in line:
            parts = line.split()
            for part in parts:
                if '/' in part:
                    return part.split('/')[0]
    return ""

async def main():
    connected = False
    last_reconnect_attempt = time.time() - reconnect_interval

    while True:
        current_time = time.time()
        # 检查设备连接状态，并在需要时尝试重新连接
        if not connected or (current_time - last_reconnect_attempt >= reconnect_interval):
            try:
                log("Connecting to device...", 2)
                output = await run_adb_command(f"adb connect {device_ip}")
                if output:
                    output = output.decode('utf-8', errors='ignore').strip()
                    log(output, 2)
                connected = "connected" in output if output else False
                last_reconnect_attempt = current_time
            except Exception as e:
                log(str(e), 4)  # 显示异常信息
                connected = False

        if connected:
            try:
                output = await run_adb_command("adb shell dumpsys window")
                if output:
                    current_package = parse_current_package(output)
                    if target_package_keyword in current_package:
                        log(f"Target package '{current_package}' detected, disabling the app and launching new app...", 3)
                        # 并行执行禁用和启动命令
                        disable_task = run_adb_command(disable_command)
                        launch_task = run_adb_command(adb_command)
                        await asyncio.gather(disable_task, launch_task)
                        log(f"Enabling {target_package_keyword} again...", 3)
                        await run_adb_command(enable_command)
                    else:
                        log(f"Active package '{current_package}' is not the target.", 3)
            except Exception as e:
                log(str(e), 4)  # 显示异常信息

        await asyncio.sleep(package_check_interval)

if __name__ == "__main__":
    asyncio.run(main())
