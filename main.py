import sys
import os
import warnings
import threading
import time
import json
import subprocess
import socket
import re
import uuid
import platform
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# Подавляем предупреждения
warnings.filterwarnings("ignore")


# ============================================
# АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПАРАМЕТРОВ
# ============================================

def get_pc_name():
    try:
        return platform.node()
    except:
        return "Unknown"


def get_mac_address():
    try:
        mac = uuid.getnode()
        if mac != 0xFFFFFFFFFFFF:
            mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
            if mac_str != "00:00:00:00:00:00":
                return mac_str
        try:
            result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, encoding='cp866',
                                    errors='ignore')
            for line in result.stdout.splitlines():
                if "Physical Address" in line or "Физический адрес" in line:
                    mac = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                    if mac:
                        return mac.group(0)
        except:
            pass
        return "Не определен"
    except:
        return "Не определен"


def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Не определен"


# ============================================
# ЗАГРУЗКА КОНФИГА
# ============================================

CONFIG_FILE = "config.json"


def load_config():
    default_config = {
        "GITHUB_TOKEN": "",
        "GITHUB_OWNER": "wemble468",
        "GITHUB_REPO": "WinDefenderapi"
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        else:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    except:
        return default_config


CONFIG = load_config()

# ============================================
# ПАРАМЕТРЫ
# ============================================

PC_NAME = get_pc_name()
PC_MAC = get_mac_address()
PC_IP = get_ip_address()

WOL_PORT = 9
WOL_BROADCAST = "255.255.255.255"
TRAY_TOOLTIP = "WinDefenderRemote"
LOCAL_DATA_FILE = "local_data.json"

# ============================================
# ИМПОРТ PYWIN32 ДЛЯ ТРЕЯ
# ============================================

try:
    import pystray
    from PIL import Image, ImageDraw

    PYSTRAY_AVAILABLE = True
except:
    PYSTRAY_AVAILABLE = False
    print("⚠️ Установите pystray: pip install pystray pillow")


# ============================================
# КЛАССЫ
# ============================================

class WakeOnLan:
    @staticmethod
    def send(mac_address, broadcast_ip=WOL_BROADCAST, port=WOL_PORT):
        mac_clean = re.sub(r'[^a-fA-F0-9]', '', mac_address)
        if len(mac_clean) != 12:
            return False, "Неверный формат MAC"
        try:
            mac_bytes = bytes.fromhex(mac_clean)
            magic_packet = b'\xff' * 6 + mac_bytes * 16
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sent = sock.sendto(magic_packet, (broadcast_ip, port))
                return sent == len(magic_packet), "OK"
        except:
            return False, "Ошибка"

    @staticmethod
    def test_wol():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split('.')
            broadcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
            return {"local_ip": local_ip, "broadcast": broadcast}
        except:
            return {"local_ip": "Неизвестно", "broadcast": WOL_BROADCAST}


class DefenderManager:
    @staticmethod
    def run_powershell(command):
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            return result.stdout, result.stderr, result.returncode
        except:
            return "", "", 1

    @staticmethod
    def get_status():
        cmd = """
        $status = Get-MpComputerStatus
        @{
            AntivirusEnabled = $status.AntivirusEnabled
            RealTimeProtectionEnabled = $status.RealTimeProtectionEnabled
            AntivirusSignatureLastUpdated = $status.AntivirusSignatureLastUpdated
            AntivirusSignatureVersion = $status.AntivirusSignatureVersion
            LastQuickScan = $status.LastQuickScan
            LastFullScan = $status.LastFullScan
            ThreatCount = (Get-MpThreatDetection).Count
        } | ConvertTo-Json
        """
        stdout, stderr, code = DefenderManager.run_powershell(cmd)
        if code == 0 and stdout:
            try:
                data = json.loads(stdout)
                return {
                    "enabled": data.get("AntivirusEnabled", False),
                    "realtime": data.get("RealTimeProtectionEnabled", False),
                    "updated": data.get("AntivirusSignatureLastUpdated", "Unknown"),
                    "version": data.get("AntivirusSignatureVersion", "Unknown"),
                    "last_quick_scan": data.get("LastQuickScan", "Never"),
                    "last_full_scan": data.get("LastFullScan", "Never"),
                    "threat_count": data.get("ThreatCount", 0)
                }
            except:
                return {"enabled": False, "updated": "Unknown"}
        return {"enabled": False, "updated": "Unknown"}

    @staticmethod
    def enable():
        cmd = "Set-MpPreference -DisableRealtimeMonitoring $false"
        _, _, code = DefenderManager.run_powershell(cmd)
        return code == 0

    @staticmethod
    def disable():
        cmd = "Set-MpPreference -DisableRealtimeMonitoring $true"
        _, _, code = DefenderManager.run_powershell(cmd)
        return code == 0

    @staticmethod
    def start_quick_scan():
        cmd = "Start-MpScan -ScanType QuickScan"
        _, _, code = DefenderManager.run_powershell(cmd)
        return code == 0

    @staticmethod
    def start_full_scan():
        cmd = "Start-MpScan -ScanType FullScan"
        _, _, code = DefenderManager.run_powershell(cmd)
        return code == 0


class LocalStorage:
    def __init__(self):
        self.data = {"computers": {}, "commands": [], "stats": []}
        self.load()

    def load(self):
        try:
            if os.path.exists(LOCAL_DATA_FILE):
                with open(LOCAL_DATA_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            else:
                self.data = {
                    "computers": {
                        PC_NAME: {
                            "name": PC_NAME,
                            "mac": PC_MAC,
                            "ip": PC_IP,
                            "first_seen": datetime.now().isoformat(),
                            "last_seen": datetime.now().isoformat(),
                            "status": "online",
                            "commands_executed": 0
                        }
                    },
                    "commands": [],
                    "stats": []
                }
                self.save()
        except:
            pass

    def save(self):
        try:
            with open(LOCAL_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except:
            pass

    def get_computers(self):
        return self.data.get("computers", {})

    def register_pc(self, pc_name, mac, ip=""):
        computers = self.get_computers()
        if pc_name not in computers:
            computers[pc_name] = {
                "name": pc_name,
                "mac": mac,
                "ip": ip,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "status": "online",
                "commands_executed": 0
            }
        else:
            computers[pc_name]["last_seen"] = datetime.now().isoformat()
            computers[pc_name]["status"] = "online"
            if ip:
                computers[pc_name]["ip"] = ip
        self.data["computers"] = computers
        self.save()
        return True

    def update_computers(self, computers):
        self.data["computers"] = computers
        self.save()

    def get_commands(self):
        return self.data.get("commands", [])

    def add_command(self, command_type):
        commands = self.get_commands()
        new_command = {
            "id": str(int(datetime.now().timestamp() * 1000)),
            "type": command_type,
            "target": "all",
            "created": datetime.now().isoformat(),
            "status": "pending"
        }
        commands.append(new_command)
        self.data["commands"] = commands
        self.save()
        return True

    def mark_command_done(self, command_id):
        commands = self.get_commands()
        for cmd in commands:
            if cmd.get("id") == command_id:
                cmd["status"] = "completed"
                cmd["executed_at"] = datetime.now().isoformat()
                break
        self.data["commands"] = commands
        self.save()
        return True

    def clear_commands(self):
        self.data["commands"] = []
        self.save()
        return True

    def add_stat(self, stat_data):
        stats = self.data.get("stats", [])
        stats.append(stat_data)
        if len(stats) > 50:
            stats = stats[-50:]
        self.data["stats"] = stats
        self.save()

    def get_stats(self):
        return self.data.get("stats", [])


class SystemTrayApp:
    """Приложение с системным треем на pystray"""

    def __init__(self):
        self.local = None
        self.github = None
        self.running = True

        self.defender = DefenderManager()
        self.init_storage()
        self.init_github()

        # Создаем иконку
        self.icon = self.create_icon()

        # Создаем меню для трея
        self.menu = self.create_menu()
        self.icon.menu = self.menu

        # Запускаем фоновый поток
        self.start_worker()

        # Вывод информации в консоль
        self.print_info()

        # Запускаем иконку
        self.icon.run()

    def create_icon(self):
        """Создает иконку для трея"""
        # Создаем изображение 64x64
        size = 64
        image = Image.new('RGB', (size, size), '#4a2b8a')
        draw = ImageDraw.Draw(image)

        # Круг
        draw.ellipse((4, 4, size - 4, size - 4), fill='#4a2b8a', outline='#6b3fa0', width=2)

        # Текст "WD"
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except:
            font = ImageFont.load_default()

        draw.text((size // 2 - 18, size // 2 - 14), "WD", fill='white', font=font)

        return pystray.Icon("WinDefenderRemote", image, TRAY_TOOLTIP)

    def create_menu(self):
        """Создает меню для трея"""
        return pystray.Menu(
            pystray.MenuItem(f"🛡️ {TRAY_TOOLTIP}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"💻 {PC_NAME} | {PC_IP}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚡ Быстрая проверка", lambda: self.send_command("scan_quick")),
            pystray.MenuItem("🔍 Полная проверка", lambda: self.send_command("scan_full")),
            pystray.MenuItem("📊 Статус Defender", lambda: self.send_command("check_status")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⛔ Отключить Defender", lambda: self.send_command("disable")),
            pystray.MenuItem("✅ Включить Defender", lambda: self.send_command("enable")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📈 Статистика", lambda: self.send_command("stats")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("💤 Wake-on-LAN", self.create_wol_submenu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Выход", self.exit_app)
        )

    def create_wol_submenu(self):
        """Создает подменю для WoL"""
        computers = self.local.get_computers()
        if computers:
            items = []
            for name, data in computers.items():
                ip = data.get("ip", "?")
                items.append(pystray.MenuItem(f"{name} ({ip})", lambda n=name: self.send_wol(n)))
            return pystray.Menu(*items)
        else:
            return pystray.Menu(pystray.MenuItem("Нет компьютеров", lambda: None, enabled=False))

    def send_command(self, cmd):
        """Отправляет команду"""
        if not self.local:
            return

        storage = self.local
        github = self.github

        if cmd == "check_status":
            status = self.defender.get_status()
            msg = (
                f"📊 СТАТУС DEFENDER\n\n"
                f"✅ Включен: {'ДА' if status.get('enabled') else 'НЕТ'}\n"
                f"🛡️ Реальное время: {'ВКЛ' if status.get('realtime') else 'ВЫКЛ'}\n"
                f"🦠 Угроз: {status.get('threat_count', 0)}"
            )
            self.show_message("📊 Статус Defender", msg)
            return

        if cmd == "stats":
            stats = storage.get_stats()
            if not stats:
                self.show_message("📊 Статистика", "Нет записей")
                return
            msg = "📊 ИСТОРИЯ\n\n"
            for stat in stats[-10:]:
                msg += f"🕐 {stat.get('time', '')[:16]}\n"
                msg += f"   📌 {stat.get('type', '')}\n"
                msg += f"   {'✅' if stat.get('success') else '❌'}\n"
                msg += "-" * 25 + "\n"
            self.show_message("📊 Статистика", msg)
            return

        if cmd == "disable":
            # Здесь должен быть диалог подтверждения, но pystray его не поддерживает
            # Просто отключаем без подтверждения
            pass

        storage.add_command(cmd)

        if github and hasattr(github, 'is_connected') and github.is_connected:
            github.add_command(cmd)
            self.show_message("✅ Команда отправлена", f"Команда: {cmd}\n\nСинхронизирована с GitHub")
        else:
            self.show_message("✅ Команда отправлена", f"Команда: {cmd}\n\nТолько локально")

    def send_wol(self, pc_name):
        """Отправляет WoL"""
        if not self.local:
            return

        computers = self.local.get_computers()
        mac = computers.get(pc_name, {}).get("mac")

        if mac:
            network_info = WakeOnLan.test_wol()
            success, _ = WakeOnLan.send(mac, network_info.get('broadcast', WOL_BROADCAST))
            if success:
                self.show_message("💤 WoL отправлен", f"Пакет отправлен на {pc_name}\nMAC: {mac}")
            else:
                self.show_message("❌ Ошибка WoL", f"Не удалось отправить на {pc_name}")
        else:
            self.show_message("❌ Ошибка", f"MAC не найден для {pc_name}")

    def show_message(self, title, text):
        """Показывает уведомление через pystray"""
        self.icon.notify(text, title)

    def print_info(self):
        """Выводит информацию в консоль"""
        print("=" * 60)
        print("  🛡️ WinDefenderRemote")
        print("  Удаленное управление Windows Defender")
        print("=" * 60)
        print(f"  📡 Имя ПК: {PC_NAME}")
        print(f"  📡 IP-адрес: {PC_IP}")
        print(f"  📡 MAC-адрес: {PC_MAC}")
        if self.github and hasattr(self.github, 'is_connected') and self.github.is_connected:
            print(f"  🌐 GitHub: ✅ Подключен")
        else:
            print(f"  🌐 GitHub: ❌ Не подключен")
        print("  🔍 Нажмите на иконку WD в трее")
        print("=" * 60)

    def init_github(self):
        """Инициализация GitHub"""
        try:
            token = CONFIG.get("GITHUB_TOKEN", "").strip()
            owner = CONFIG.get("GITHUB_OWNER", "").strip()
            repo = CONFIG.get("GITHUB_REPO", "").strip()

            if token and owner and repo:
                from github_manager import GitHubManager
                self.github = GitHubManager(token, owner, repo)
                if hasattr(self.github, 'is_connected') and self.github.is_connected:
                    self.sync_computers()
                    print("✅ GitHub: Подключен успешно")
                else:
                    print(f"⚠️ GitHub: {getattr(self.github, 'last_error', 'Ошибка')}")
            else:
                print("⚠️ GitHub: Не настроен (заполните config.json)")
        except Exception as e:
            print(f"⚠️ GitHub: Ошибка инициализации - {e}")

    def sync_computers(self):
        """Синхронизирует список компьютеров с GitHub"""
        try:
            if not self.github or not hasattr(self.github, 'is_connected') or not self.github.is_connected:
                return

            github_computers = self.github.get_computers()
            local_computers = self.local.get_computers()

            merged = {**local_computers, **github_computers}

            merged[PC_NAME] = {
                "name": PC_NAME,
                "mac": PC_MAC,
                "ip": PC_IP,
                "last_seen": datetime.now().isoformat(),
                "status": "online"
            }

            self.local.update_computers(merged)
            self.github.update_computers(merged)

            print(f"✅ GitHub: Синхронизировано {len(merged)} компьютеров")
        except Exception as e:
            print(f"⚠️ GitHub: Ошибка синхронизации - {e}")

    def init_storage(self):
        self.local = LocalStorage()
        self.local.register_pc(PC_NAME, PC_MAC, PC_IP)

    def start_worker(self):
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()

    def worker_loop(self):
        defender = DefenderManager()
        sync_counter = 0

        while self.running:
            try:
                if self.local:
                    commands = self.local.get_commands()
                    pending = [c for c in commands if c.get("status") == "pending"]

                    for cmd in pending:
                        cmd_type = cmd.get("type")
                        cmd_id = cmd.get("id")
                        success = False

                        if cmd_type == "scan_quick":
                            success = defender.start_quick_scan()
                            self.local.add_stat({
                                "time": datetime.now().isoformat(),
                                "type": "Быстрая проверка",
                                "success": success,
                                "details": "Завершена" if success else "Ошибка"
                            })

                        elif cmd_type == "scan_full":
                            success = defender.start_full_scan()
                            self.local.add_stat({
                                "time": datetime.now().isoformat(),
                                "type": "Полная проверка",
                                "success": success,
                                "details": "Завершена" if success else "Ошибка"
                            })

                        elif cmd_type == "check_status":
                            status = defender.get_status()
                            self.local.add_stat({
                                "time": datetime.now().isoformat(),
                                "type": "Статус",
                                "success": True,
                                "details": f"Defender: {'Вкл' if status.get('enabled') else 'Выкл'}"
                            })

                        elif cmd_type == "disable":
                            success = defender.disable()
                            self.local.add_stat({
                                "time": datetime.now().isoformat(),
                                "type": "Отключение",
                                "success": success,
                                "details": "Отключен" if success else "Ошибка"
                            })

                        elif cmd_type == "enable":
                            success = defender.enable()
                            self.local.add_stat({
                                "time": datetime.now().isoformat(),
                                "type": "Включение",
                                "success": success,
                                "details": "Включен" if success else "Ошибка"
                            })

                        elif cmd_type == "stats":
                            success = True

                        self.local.mark_command_done(cmd_id)

                        if success and self.github and hasattr(self.github,
                                                               'is_connected') and self.github.is_connected:
                            self.github.mark_command_done(cmd_id)

                # Синхронизация с GitHub каждые 30 секунд
                sync_counter += 1
                if sync_counter >= 30 and self.github and hasattr(self.github,
                                                                  'is_connected') and self.github.is_connected:
                    sync_counter = 0
                    self.sync_computers()

                # Обновляем меню WoL
                if hasattr(self, 'icon') and self.icon:
                    self.icon.menu = self.create_menu()

            except Exception as e:
                pass
            time.sleep(1)

    def exit_app(self):
        """Выход из программы"""
        self.running = False
        if hasattr(self, 'icon'):
            self.icon.stop()
        sys.exit(0)


def main():
    if not PYSTRAY_AVAILABLE:
        print("❌ Установите pystray: pip install pystray pillow")
        print("И перезапустите программу")
        input("Нажмите Enter для выхода...")
        return

    app = SystemTrayApp()


if __name__ == "__main__":
    main()