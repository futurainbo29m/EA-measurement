import os
from datetime import datetime
from model import MeasurementPoint
from typing import List
from dataclasses import asdict
import json


class SaveManager:
    """
    測定データの保存に関する全ての処理を担当するクラス。
    ディレクトリの作成、テキストデータやグラフ画像の保存を一元管理する。
    """

    def __init__(self, base_directory="./outputdata"):
        """
        Args:
            base_directory (str): 全ての測定データを保存する大元のフォルダパス
        """
        self.base_directory = base_directory
        # 現在の測定に対応する保存フォルダのパスを保持する
        self.current_save_path = None

    def save_settings_to_file(self, filename: str, settings_data):
        """
        現在の測定フォルダに、設定データ（Setting_Parmsなど）をJSONファイルとして保存する。
        """
        path = self.get_current_save_path()
        if not path:
            return

        file_path = os.path.join(path, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # dataclassを辞書に変換して保存
                json.dump(asdict(settings_data),
                          f,
                          ensure_ascii=False,
                          indent=4)
            print(f"測定設定を保存しました: {file_path}")
        except Exception as e:
            print(f"設定ファイルの保存中にエラーが発生しました: {e}")

    def create_new_measurement_directory(self):
        """
        タイムスタンプに基づいた新しい測定フォルダを作成し、パスを保持する。
        例: ./outputdata/2025-08-07_14-30-00/
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_save_path = os.path.join(self.base_directory, timestamp)
        os.makedirs(self.current_save_path, exist_ok=True)
        print(f"保存用ディレクトリを作成しました: {self.current_save_path}")

    def get_current_save_path(self):
        """
        現在使用している保存フォルダのフルパスを返す。
        """
        if not self.current_save_path:
            print("エラー: 保存用ディレクトリがまだ作成されていません。")
            return None
        return self.current_save_path

    def save_data_to_file(self, filename: str,
                          data_points: List[MeasurementPoint]):
        """
        現在の測定フォルダに、MeasurementPointのリストをテキストファイルとして保存する。
        ヘッダーとデータ列は、データポイントの内容に応じて動的に決定される。

        Args:
            filename (str): 保存するファイル名 (例: "output.txt")
            data_points (List[MeasurementPoint]): 保存するデータポイントのリスト
        """
        path = self.get_current_save_path()
        if not path or not data_points:
            return

        file_path = os.path.join(path, filename)

        # 最初のデータポイントを基に、保存する列（Noneでない値を持つ列）を決定
        first_point_dict = data_points[0].__dict__
        headers = [
            key for key, value in first_point_dict.items() if value is not None
        ]

        try:
            with open(file_path, 'w') as file:
                # ヘッダー行を書き込む
                file.write("\t".join(headers) + "\n")

                # データ行を書き込む
                for point in data_points:
                    values = []
                    for header in headers:
                        value = getattr(point, header, "")
                        values.append(str(value) if value is not None else "")
                    file.write("\t".join(values) + "\n")

            print(f"テキストデータを保存しました: {file_path}")
        except Exception as e:
            print(f"テキストデータの保存中にエラーが発生しました: {e}")

    def save_matplotlib_figure(self, filename: str, fig):
        """
        現在の測定フォルダにmatplotlibのグラフを画像として保存する。

        Args:
            filename (str): 保存する画像ファイル名 (例: "graph.png")
            fig: 保存するmatplotlibのFigureオブジェクト
        """
        path = self.get_current_save_path()
        if not path:
            return

        file_path = os.path.join(path, filename)
        try:
            fig.savefig(file_path)
            print(f"グラフ画像を保存しました: {file_path}")
        except Exception as e:
            print(f"グラフ画像の保存中にエラーが発生しました: {e}")
