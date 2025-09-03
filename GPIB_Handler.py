import pyvisa
from functools import wraps


class GPIB_Handler:

    def __init__(self):
        # PyVISAリソースマネージャを初期化
        self.rm = pyvisa.ResourceManager()
        self.devices = {}

    def add_device(self, alias: str, adress: str):
        """
        GPIBデバイスを追加する
        alias:デバイスのエイリアス名
        adress:GPIBアドレス(例:"GPIB::5::INSTR")
        """
        try:
            _instrument = self.rm.open_resource(adress)
            self.devices[alias] = _instrument
            print(f"Device '{alias}' added at adress '{adress}'.")
        except pyvisa.VisaIOError as e:
            print(f"Failed to add device '{alias}' at adress '{adress}':{e}")

    def remove_device(self, alias: str):
        """
        GPIBデバイスを削除
        alias:削除するデバイスのエイリアス名
        """
        if alias in self.devices:
            self.devices[alias].close()
            del self.devices[alias]
            print(f"Device '{alias}' removed.")
        else:
            print(f"Device '{alias}' not found.")

    def clear(self, alias: str):
        """
        ステータスクリア処理
        pyvisaのclear()が適用可能かどうかで処理を分ける
        """
        if alias == "LI5650":
            self.write(alias, "*CLS")  #LI5650のステータスクリアコマンド
        else:
            self.devices[alias].clear()  #pyvisa搭載のクリアコマンド

    def busy_check(self, alias: str):
        """
        機器のビジーチェックを行う
        """
        _stb = self.devices[alias].read_stb()
        self.clear(alias)
        return _stb

    def _alias_check(func):
        """
        デバイスエイリアスが有効かをチェックし、エラーハンドリングを行うデコレータ
        """

        @wraps(func)
        def wrapper(self, alias: str, *args, **kwargs):
            if alias not in self.devices:
                print(f"Device '{alias}' not found.")
                return None
            try:
                return func(self, alias, *args, *kwargs)
            except pyvisa.VisaIOError as e:
                print(f"Error interacting with device '{alias}':{e}")
                return None

        return wrapper

    @_alias_check
    def write(self, alias: str, command: str):
        """
        デバイスにコマンドを送信
        alias:対象デバイスのエイリアス名
        command:送信するコマンド文字列
        """
        self.devices[alias].write(command)
        print(f"Command '{command}' sent to device '{alias}'.")

    @_alias_check
    def read(self, alias: str):
        """
        デバイスからデータを読み取る
        alias:対象デバイスのエイリア名
        """
        _response = self.devices[alias].read()
        print(f"Response from device '{alias}':{_response}")
        return _response

    @_alias_check
    def query(self, alias: str, command: str):
        """
        デバイスにコマンドを送信して応答を受信
        alias:対象デバイスのエイリアス名
        command:送信するコマンド文字列
        """
        _response = self.devices[alias].query(command)
        print(
            f"Query '{command}' to device '{alias}' received response:{_response}"
        )

        return _response.strip()

    @_alias_check
    def query_bytes(self, alias: str, command: str, bytes: int):
        """
        バイト数を指定してデバイスにコマンドを送信して応答を受信
        alias:対象デバイスのエイリアス名
        command:送信するコマンド文字列
        bytes:指定するバイト数
        """
        self.devices[alias].write(command)
        _response = self.devices[alias].read_bytes(bytes)
        self.clear(alias)
        _response.decode('utf-8')
        _response.strip()
        print(
            f"Query '{command}' to device '{alias}' received response:{float(_response)}"
        )
        return float(_response)

    def list_devices(self):
        """
        現在登録されているデバイスをリスト表示
        """
        if self.devices:
            print("Resistered devices:")
            for alias, device in self.devices.items():
                print(f" - {alias}:{device.resource_name}")
        else:
            print("No devices registered.")

    def close_all(self):
        """
        登録されているすべてのデバイスを閉じる
        """
        for alias in list(self.devices.keys()):
            self.remove_device(alias)
        print("All devices closed.")


if __name__ == "__main__":
    handler = GPIB_Handler()
    print(handler.rm.list_resources())
    handler.add_device("LI5650", 'GPIB0::3::INSTR')
    handler.write("LI5650", "*IDN?")

    handler.close_all()
