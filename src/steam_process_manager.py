import psutil
import time
import os
import signal

DEFAULT_STEAMAPPS_PATH = r"C:\Program Files (x86)\Steam\steamapps"
OUTPUT_FILE = "process_log.txt"


def get_steam_process():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            if 'steam.exe' in process.info['name'].lower():
                return process
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def is_process_in_steamapps(process, steamapps_path):
    try:
        exe_path = process.exe()
        return os.path.commonpath([exe_path.lower(), steamapps_path.lower()]) == steamapps_path.lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def log_process(pid):
    with open(OUTPUT_FILE, 'a') as f:
        f.write(f"New process PID: {pid}\n")

def monitor_steam_process(steamapps_path):
    global known_child_pids
    steam_process = get_steam_process()

    if not steam_process:
        print("Steam is not running.")
        return

    print(f"Steam is running with PID: {steam_process.pid}")

    initial_child_pids = {child.pid for child in steam_process.children(recursive=True)}
    known_child_pids = set()
    waiting_for_game_launch = True

    print("Monitoring for new processes launched by Steam...")

    while True:
        try:
            steam_process = psutil.Process(steam_process.pid)

            current_children = steam_process.children(recursive=True)
            current_child_pids = {child.pid for child in current_children if is_process_in_steamapps(child, steamapps_path)}

            new_processes = current_child_pids - known_child_pids - initial_child_pids
            if new_processes:
                for pid in new_processes:
                    print(f"New process detected: {pid}")
                    log_process(pid)
                known_child_pids.update(new_processes)
                waiting_for_game_launch = False

            closed_processes = known_child_pids - current_child_pids
            if closed_processes:
                print(f"Processes closed: {closed_processes}")
                known_child_pids.difference_update(closed_processes)

            if not known_child_pids and not waiting_for_game_launch:
                print("All new game processes have closed. Exiting...")
                break
                
            if waiting_for_game_launch:
                print("Waiting for a game to launch...")

            time.sleep(1)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print("Steam process has terminated unexpectedly. Exiting...")
            break

################################

def read_pids_from_file(file_path):
    pids = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 4 and parts[0] == 'New' and parts[1] == 'process' and parts[2] == 'PID:':
                    try:
                        pids.append(int(parts[3]))
                    except ValueError:
                        print(f"Skipping invalid PID entry: {line.strip()}")
    else:
        print(f"File {file_path} does not exist.")
    return pids

def terminate_processes(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to process PID: {pid}")
        except ProcessLookupError:
            print(f"Process PID: {pid} not found.")
        except PermissionError:
            print(f"Permission denied to terminate process PID: {pid}.")
        except Exception as e:
            print(f"Failed to terminate process PID: {pid}. Error: {e}")

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    else:
        print(f"File {file_path} does not exist.")

def exit_game():
    pids = read_pids_from_file(OUTPUT_FILE)
    if pids:
        terminate_processes(pids)
        delete_file(OUTPUT_FILE)
    else:
        print("No PIDs to process.")


