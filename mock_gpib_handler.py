import random
import time


class Mock_GPIB_Handler:
    """
    GPIB_Handlerを模倣したダミークラス。
    実際のハードウェアなしでデバッグを行うために使用します。
    """

    def __init__(self):
        self.devices = {}
        print("--- MOCK GPIB HANDLER INITIALIZED (DEBUG MODE) ---")

    def add_device(self, alias: str, adress: str):
        """デバイス追加をシミュレートします。"""
        self.devices[alias] = {"address": adress}
        print(f"MOCK: Device '{alias}' added at address '{adress}'.")

    def remove_device(self, alias: str):
        """デバイス削除をシミュレートします。"""
        if alias in self.devices:
            del self.devices[alias]
            print(f"MOCK: Device '{alias}' removed.")
        else:
            print(f"MOCK: Device '{alias}' not found.")

    def clear(self, alias: str):
        """クリア処理をシミュレートします。"""
        print(f"MOCK: Device '{alias}' cleared.")
        pass  #何もしない

    def busy_check(self, alias: str):
        """ビジーチェックをシミュレートし、常に準備完了(False)を返します。"""
        print("MOCK: Busy check -> Not Busy")
        return False

    def write(self, alias: str, command: str):
        """コマンド送信をシミュレートします。"""
        print(f"MOCK: Command '{command}' sent to device '{alias}'.")

    def read(self, alias: str):
        """データ読み取りをシミュレートし、ダミーデータを返します。"""
        response = "MOCK_DATA"
        print(f"MOCK: Response from device '{alias}': {response}")
        return response

    def query(self, alias: str, command: str):
        """
        クエリをシミュレートし、コマンドに応じてダミーの測定値を返します。
        """
        response = 0.0
        if alias == "LI5650":  #ロックインアンプの場合
            STATUS = 0
            DATA1 = random.uniform(0.0, 5.0)
            DATA2 = random.uniform(-180, 180)
            DATA3 = random.uniform(0.0, 0.5)
            DATA4 = random.uniform(0.0, 0.5)

            response = f"{STATUS},{DATA1},{DATA2},{DATA3},{DATA4}"
            print(
                f"MOCK: Query '{command}' to '{alias}' -> Faked response: {response}"
            )
            return response
        if command == ":READ?":  # DMM6500からの電圧読み取りを想定
            response = random.uniform(0.5, 5.0)  # 0.5Vから5.0Vの間のランダムな値を生成
            print(
                f"MOCK: Query '{command}' to '{alias}' -> Faked response: {response}"
            )
        else:
            response = f"MOCK_QUERY_RESPONSE_FOR_{command}"
            print(
                f"MOCK: Query '{command}' to '{alias}' -> Faked response: {response}"
            )

        return float(response)

    def query_bytes(self, alias: str, command: str, bytes: int):
        """
        バイト指定のクエリをシミュレートし、ダミーの波長を返します。
        """
        self.write(alias, command)
        # 現在の送信波長やランダムな値を返すなど、より精巧にすることも可能
        response = float(random.uniform(300.0, 800.0))  # 300nmから800nmのランダムな波長
        print(
            f"MOCK: Query_bytes '{command}' to '{alias}' -> Faked response: {response}"
        )
        return response

    def list_devices(self):
        """登録デバイスのリスト表示をシミュレートします。"""
        if self.devices:
            print("MOCK: Registered devices:")
            for alias, device_info in self.devices.items():
                print(f" - {alias}:{device_info['address']}")
        else:
            print("MOCK: No devices registered.")

    def close_all(self):
        """全デバイス切断をシミュレートします。"""
        self.devices = {}
        print("MOCK: All devices closed.")
