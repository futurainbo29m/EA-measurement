from dataclasses import dataclass, field
from typing import List, Optional
import customtkinter as ctk
import enum
import math


class Model():

    def __init__(self, parent):
        #ウィジェット変数
        self.var_measurement: ctk.StringVar = ctk.StringVar(parent, "")
        self.var_mode: ctk.StringVar = ctk.StringVar(parent, "")
        self.var_LIamp: ctk.StringVar = ctk.StringVar(parent, "")
        self.var_time_constant: ctk.StringVar = ctk.StringVar(parent, "")
        self.var_time_constant_multiplier: ctk.StringVar = ctk.StringVar(
            parent, "6")
        self.var_measurement_wavelength: List[ctk.StringVar] = [
            ctk.StringVar(parent, value="") for _ in range(0, 5)
        ]
        self.var_measurement_section: List[ctk.StringVar] = [
            ctk.StringVar(parent, value="") for _ in range(0, 4)
        ]
        self.var_filter: List[ctk.StringVar] = [
            ctk.StringVar(parent, value="") for _ in range(0, 4)
        ]
        self.var_diffraction: List[ctk.StringVar] = [
            ctk.StringVar(parent, value="") for _ in range(0, 4)
        ]
        self.var_spectrometer_wavelength: ctk.StringVar = ctk.StringVar(
            parent, "")
        self.var_now_wavelength: ctk.StringVar = ctk.StringVar(parent, "")
        self.var_send_wavelength: ctk.StringVar = ctk.StringVar(parent, "633")
        #変調信号探索モード用のウィジェット変数
        self.var_total_duration: ctk.StringVar = ctk.StringVar(parent, "60")
        self.var_measurement_interval: ctk.StringVar = ctk.StringVar(
            parent, "1")

        # Setting_Parmsインスタンスを生成
        self.setting_parms = Setting_Parms(
            measurement_name="",
            measurement_notes="",
            measurement="",
            mode="",
            LIamp="",
            time_constant="",
            time_constant_multiplier="",
            measurement_wavelength=[""] * 5,
            measurement_section=[""] * 4,
            filter=[""] * 4,
            diffraction=[""] * 4,
        )
        # Data_Containerインスタンスを生成
        self.data_container = Data_Container()

    def update_setting_parms(self):
        """
        SettingParmsのインスタンスの値をウィジェット変数の値で更新
        """
        self.setting_parms.measurement = self.var_measurement.get()
        self.setting_parms.mode = self.var_mode.get()
        self.setting_parms.LIamp = self.var_LIamp.get()
        self.setting_parms.time_constant = self.var_time_constant.get()
        self.setting_parms.time_constant_multiplier = self.var_time_constant_multiplier.get(
        )
        self.setting_parms.measurement_wavelength = [
            var.get() for var in self.var_measurement_wavelength
        ]
        self.setting_parms.measurement_section = [
            var.get() for var in self.var_measurement_section
        ]
        self.setting_parms.filter = [var.get() for var in self.var_filter]
        self.setting_parms.diffraction = [
            var.get() for var in self.var_diffraction
        ]
        self.setting_parms.total_duration = self.var_total_duration.get()
        self.setting_parms.measurement_interval = self.var_measurement_interval.get(
        )

    def print_setting_parms(self):
        """
        SettingParmsの内容を表示（デバッグ用）
        """
        self.update_setting_parms()
        print(self.setting_parms)

    def calculate_measurement_points(self, measurement_wavelength: List[str],
                                     measurement_section: List[str]):
        """
        テキストボックスに入力された測定波長と測定間隔から波長の１次元配列を生成する関数

        _ranges:測定波長のテキストボックスに入力された内容の配列(例:[100,200,400])
        _intervals:測定間隔のテキストボックスに入力された内容の配列(例:[1,3])
        list:測定間隔を区間ごとに変化させながら並べた波長の2次元配列
        """
        #測定横軸配列の作成
        self.data_container.add_measurement_list(measurement_wavelength,
                                                 measurement_section)
        #2次元配列に変換
        _ranges = self.data_container.measurement_wave_length_list
        _intervals = self.data_container.measurement_section_list
        if len(_ranges) == 0:
            print("Error!:ranges is Null")
            return
        else:
            _list = []
            _interval_points = []
            for i in range(len(_ranges) - 1):
                _start = _ranges[i]
                _end = _ranges[i + 1]
                _step_increase = _intervals[i]
                _num_points = math.ceil(
                    (_end - _start) / _step_increase)  #切り上げを行う
                _interval_points.append(_num_points)

            for index, secNum in enumerate(_interval_points):
                _points = []
                for i in range(secNum):
                    _wave = _ranges[index] + i * _intervals[index]
                    _points.append(_wave)
                _list.append(_points)

            if _list:
                _list[-1].append(_ranges[-1])

            self.data_container.MsrData1 = _list  #作成した配列を格納


class MsrState(enum.Enum):  #ステータスの定義
    default = enum.auto()
    measure = enum.auto()
    stop = enum.auto()
    cancel = enum.auto()
    finish = enum.auto()


class State_Handler:
    """
    GUIの状態（ステータス）を管理するクラス
    """

    def __init__(self):
        self.msrstate = MsrState.default

    def update_state(self, state):
        self.msrstate = state
        print("state:", state)


@dataclass
class Setting_Parms:
    """
    測定条件の入力内容や設定されたパラメータを扱うデータクラス
    """
    measurement_name: str  #測定名
    measurement_notes: str  #測定メモ
    measurement: str  #測定の種類
    mode: str  #測定モード
    LIamp: str  #ロックインアンプ
    time_constant: str  #時定数
    time_constant_multiplier: str  #時定数への掛け算
    measurement_wavelength: List[str] = field(default_factory=list)  #測定波長
    measurement_section: List[str] = field(default_factory=list)  #測定間隔
    filter: List[str] = field(default_factory=list)  #フィルター
    diffraction: List[str] = field(default_factory=list)  #回折格子
    total_duration: str = ""  #[変調信号探索]測定総時間
    measurement_interval: str = ""  #[変調信号探索]測定間隔

    # 日本語ラベル
    def get_label(self, field_name: str) -> str:
        labels = {
            "measurement_name": "測定名",
            "measurement_notes": "測定メモ",
            "measurement": "測定の種類",
            "mode": "測定モード",
            "LIamp": "LIアンプ",
            "time_constant": "時定数",
            "time_constant_multiplier": "定数",
            "measurement_wavelength": "測定波長",
            "measurement_section": "測定間隔",
            "filter": "フィルター",
            "diffraction": "回折格子",
            "total_duration": "測定総時間",
            "measurement_interval": "測定間隔"
        }
        return labels.get(field_name, field_name)


# 1測定点あたりのすべてのデータを格納するデータクラス
@dataclass
class MeasurementPoint:
    time: Optional[float] = None
    wavelength: Optional[float] = None
    dmm_value: Optional[float] = None
    R: Optional[float] = None
    theta: Optional[float] = None
    X: Optional[float] = None
    Y: Optional[float] = None


class Data_Container:
    """
    測定データ（MeasurementPointのリスト）を管理するクラス。
    """

    def __init__(self):
        # 測定データポイントのリスト
        self.points: List[MeasurementPoint] = []
        # 測定波長の計算結果
        self.MsrData1: List[List[float]] = []
        self.measurement_wave_length_list: List[float] = []
        self.measurement_section_list: List[float] = []

    def add_point(self, point: MeasurementPoint):
        """新しい測定データポイントをリストに追加する。"""
        self.points.append(point)

    def get_plot_data(self, x_key: str,
                      y_key: str) -> tuple[List[float], List[float]]:
        """グラフ描画用に特定のキーのデータリストを抽出する。"""
        x_data = [
            getattr(p, x_key) for p in self.points
            if getattr(p, x_key) is not None
        ]
        y_data = [
            getattr(p, y_key) for p in self.points
            if getattr(p, y_key) is not None
        ]
        return x_data, y_data

    def add_measurement_list(self, add_WL: List[str], add_S: List[str]):
        """空の要素を排除して新しいリストに抽出する"""
        self.measurement_wave_length_list = [float(WL) for WL in add_WL if WL]
        self.measurement_section_list = [float(S) for S in add_S if S]

    def reset_list(self):
        """すべてのデータをリセットする。"""
        self.points = []
        self.MsrData1 = []
        self.measurement_wave_length_list = []
        self.measurement_section_list = []
