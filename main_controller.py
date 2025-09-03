from view import View
from model import Model, MsrState, State_Handler, MeasurementPoint
from save_manager import SaveManager
from logger import Logger
from table_manager import DataTableManager
import customtkinter as ctk
from tkinter import messagebox
from CTkMessagebox import CTkMessagebox
import pyvisa
import threading
from customtkinter import filedialog
from dataclasses import asdict
from typing import List
from functools import wraps
from datetime import datetime, timedelta
import json
import random
import time
import os

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ デバッグモード切り替えフラグ ★★★
# ★★★ True: 装置なしで実行 (Mockを使用)
# ★★★ False: 装置ありで実行 (実機と接続)
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
DEBUG_MODE = True


def measurement_handler(func):
    """
    測定メソッドの前処理と後処理を共通化するためのデコレーター。
    """

    @wraps(func)
    def wrapper(self, headers: tuple, *args, **kwargs):
        # --- ① 測定前の共通準備処理 ---
        #ロガー出力
        measurement_mode = self.model.setting_parms.measurement
        self.logger.add_log(f"{measurement_mode}測定を開始します。", level="STATE")
        #headersを受け渡し単位見出しを反映
        self.table_manager.clear_and_set_header(*headers)
        #保存用ディレクトリ準備
        self.save_manager.create_new_measurement_directory()
        #設定をファイルに保存する
        self.save_manager.save_settings_to_file("settings.json",
                                                self.model.setting_parms)
        #配列のリセット
        self.model.data_container.reset_list()
        #測定横軸配列の作成
        self.model.calculate_measurement_points(
            self.model.setting_parms.measurement_wavelength,
            self.model.setting_parms.measurement_section)

        # --- 予想終了時刻の計算とログ出力 ---
        estimated_duration = 0
        try:
            if measurement_mode in ["ラマン", "電場変調ラマン"]:
                # ポイント数 × 1点あたりの時間で総時間を計算
                num_points = sum(
                    len(sublist)
                    for sublist in self.model.data_container.MsrData1)
                time_constant_ms = float(
                    self.model.setting_parms.time_constant)
                multiplier = float(
                    self.model.setting_parms.time_constant_multiplier)
                wait_per_point = (time_constant_ms * 10E-4) * multiplier
                buffer = 2  # 待機時間以外に、機器の動作時間バッファ(s)を追加
                estimated_duration = num_points * (wait_per_point + buffer)

            elif measurement_mode == "変調信号探索":
                # ユーザーが入力した測定総時間をそのまま使用
                estimated_duration = float(
                    self.model.setting_parms.total_duration)

            if estimated_duration > 0:
                end_time = datetime.now() + timedelta(
                    seconds=estimated_duration)
                self.logger.add_log(
                    f"予想終了時刻: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    level="INFO")

        except Exception as e:
            self.logger.add_log(f"予想終了時刻の計算中にエラーが発生しました: {e}", level="WARN")

        # --- ② 本体となる測定メソッドを実行 ---
        func(self, headers, *args, **kwargs)

        # --- ③ 測定後の共通後処理 ---
        if self.state_handler.msrstate == MsrState.measure:
            # 正常に完了した場合
            self.state_handler.update_state(MsrState.finish)
            self.save_manager.save_matplotlib_figure(
                "measurement_graph.png",
                self.view.graph_frame.plot_manager.fig)
            self.view.graph_frame.canvas.draw()
            self.logger.add_log("測定が正常に完了しました。", level="INFO")

        # 状態をデフォルトに戻し、ボタンの見た目を更新
        self.state_handler.update_state(MsrState.default)
        self.change_button_texture()

    return wrapper


class LockinAmpHandler:
    """ロックインアンプ(LI5650)の操作をカプセル化するクラス。"""

    def __init__(self, gpib_handler, alias="LI5650"):
        self.gpib = gpib_handler
        self.alias = alias

    def setup(self, time_constant: float):
        """ロックインアンプの初期設定を行う。"""
        self.gpib.clear(self.alias)
        self.gpib.write(self.alias, ":CALC1:FORM MLIN")  # R
        self.gpib.write(self.alias, ":CALC2:FORM PHAS")  # θ
        self.gpib.write(self.alias, ":CALC3:FORM REAL")  # X
        self.gpib.write(self.alias, ":CALC4:FORM IMAG")  # Y
        self.gpib.write(self.alias, ":DATA 31")
        self.gpib.write(self.alias, f"FILT:TCON {time_constant}")

    def measure(self) -> dict:
        """測定を実行し、結果を辞書として返す。"""
        raw_values = self.gpib.query(self.alias, ":FETCh?")

        if not raw_values or not isinstance(raw_values, str):
            print("ロックインアンプから有効な値が取得できませんでした。")
            return {"R": 0.0, "theta": 0.0, "X": 0.0, "Y": 0.0}

        # 受信した文字列を解析する
        parts = raw_values.strip().split(',')
        try:
            # STATUS, DATA1(R), DATA2(θ), DATA3(X), DATA4(Y)
            return {
                "R": float(parts[1]),
                "theta": float(parts[2]),
                "X": float(parts[3]),
                "Y": float(parts[4])
            }
        except (IndexError, ValueError) as e:
            print(f"ロックインアンプのデータ解析中にエラー: {e}")
            return {"R": 0.0, "theta": 0.0, "X": 0.0, "Y": 0.0}


class Controller():

    def __init__(self, root):
        self.root = root
        self.view = View(self.root, self)
        self.model = Model(self.root)
        self.save_manager = SaveManager()
        self.state_handler = State_Handler()
        self.table_manager = DataTableManager(
            self.view.text_frame.data_textbox)
        self.logger = Logger(self.view.text_frame.log_textbox)
        #最初のログ
        self.logger.add_log("アプリケーションを起動しました。", level="INFO")

        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        # ★★★ デバッグモードに応じて呼び出すクラスを切り替える ★★★
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        if DEBUG_MODE:
            from mock_gpib_handler import Mock_GPIB_Handler
            self.gpib_handler = Mock_GPIB_Handler()
        else:
            from GPIB_Handler import GPIB_Handler
            self.gpib_handler = GPIB_Handler()

        self.lockin_handler = LockinAmpHandler(self.gpib_handler)

        #GPIB機器のエイリアス
        self.alias_CT25: str = "CT-25"
        self.alias_DM6500: str = "DM6500"
        self.alias_LI5650: str = "LI5650"

        #バインディング
        self.view.mode_frame.measurement_combobox.configure(
            variable=self.model.var_measurement,
            command=self._on_measurement_mode_change)
        self.view.mode_frame.mode_combobox.configure(
            variable=self.model.var_mode)
        self.view.mode_frame.LIamp_combobox.configure(
            variable=self.model.var_LIamp)
        self.view.mode_frame.time_constant_textbox.configure(
            textvariable=self.model.var_time_constant)
        self.view.mode_frame.time_constant_multiplier_textbox.configure(
            textvariable=self.model.var_time_constant_multiplier)
        for i in range(5):
            self.view.params_frame.measurement_wavelengh[i].configure(
                textvariable=self.model.var_measurement_wavelength[i])
        for i in range(4):
            self.view.params_frame.measurement_section[i].configure(
                textvariable=self.model.var_measurement_section[i])
            self.view.params_frame.filter_combobox[i].configure(
                variable=self.model.var_filter[i])
            self.view.params_frame.diffraction_combobox[i].configure(
                variable=self.model.var_diffraction[i])
        self.view.mode_frame.spectrometer_wavelength_label.configure(
            textvariable=self.model.var_spectrometer_wavelength)
        self.view.mode_frame.now_wavelength_label.configure(
            textvariable=self.model.var_now_wavelength)
        self.view.mode_frame.send_wavelength_textbox.configure(
            textvariable=self.model.var_send_wavelength)
        self.view.mode_frame.total_duration_entry.configure(
            textvariable=self.model.var_total_duration)
        self.view.mode_frame.interval_entry.configure(
            textvariable=self.model.var_measurement_interval)

        self._on_measurement_mode_change(self.model.var_measurement.get())

        #コールバック
        ##デバッグ用ボタンたち
        #設定保存ボタン
        self.view.control_button_frame.save_setting_button.configure(
            command=self.save_setting_parms)
        #設定読み込みボタン
        self.view.control_button_frame.load_setting_button.configure(
            command=self.load_setting_parms)
        #波長送りボタン
        self.view.mode_frame.send_wavelength_button.configure(
            command=self.send_wavelength_button_cmd)
        #DMM6500ボタン
        self.view.control_button_frame.check_DMM6500_button.configure(
            command=self.DMM6500_button_cmd)
        #CT25ボタン
        self.view.control_button_frame.check_CT25_button.configure(
            command=self.check_CT25_button_cmd)
        #測定ボタン
        self.view.control_button_frame.measure_button.configure(
            command=self.measure_button_cmd)
        #停止ボタン
        self.view.control_button_frame.stop_button.configure(
            command=self.toggle_pause_cmd)
        #キャンセルボタン
        self.view.control_button_frame.cancel_button.configure(
            command=self.cancel_button_cmd)
        #終了ボタン
        self.view.control_button_frame.finish_button.configure(
            command=self.finish_button_cmd)
        #ボタンのインタラクティブを更新
        self.change_button_texture()

        #GPIB機器の接続
        self.gpib_handler.add_device(self.alias_CT25, "GPIB0::9::INSTR")
        self.gpib_handler.add_device(self.alias_DM6500,
                                     "USB0::0x05E6::0x6500::04425756::INSTR")
        self.gpib_handler.add_device(self.alias_LI5650, "GPIB0::3::INSTR")

        #CT-25の初期設定
        self.default_CT25_set()

    def _on_measurement_mode_change(self, selected_mode: str):
        """測定モードのプルダウンが変更されたときに呼び出される"""
        # ViewのMode_Frameに、UIの更新を指示する
        self.view.mode_frame.update_parameter_visibility(selected_mode)
        self.view.mode_frame.update_labels(selected_mode)
        self.logger.add_log(f"UIを '{selected_mode}' モード用に更新しました。",
                            level="INFO")

    def default_CT25_set(self):
        """
        CT_25の初期設定
        """
        self.gpib_handler.clear(self.alias_CT25)
        self.gpib_handler.write(self.alias_CT25, "MSW,1")  #分光器をCT-25に指定
        self.gpib_handler.write(self.alias_CT25,
                                "GRT,1")  #回折格子の指定(1 -> 1200/mm, 2 -> 600/mm)
        self.gpib_handler.write(
            self.alias_CT25,
            "PRT,100")  #パルスレートの指定(100 -> 1200/mm用, 50 -> 600/mm用)

    def scan_wavelength(self, wavelength):
        """
        目的の波長まで分光器を回す関数
        """
        self.gpib_handler.write(self.alias_CT25, f"SCN,2,{wavelength}")
        while self.gpib_handler.busy_check(self.alias_CT25):
            time.sleep(1)  #ビジー状態のときは待機する

    def check_CT25_button_cmd(self):
        """
        CT-25ボタンのコマンド
        """
        self.sync_wavelength()

    def DMM6500_button_cmd(self):
        """
        DMM6500ボタンコマンド（タイムアウト対応版）
        """
        while True:
            _value = self.gpib_handler.query(self.alias_DM6500, ":READ?")

            if not isinstance(_value, pyvisa.errors.VisaIOError):
                print(_value)
                return _value  # 成功したら値を返して終了
            time.sleep(0.01)

    def measure_button_cmd(self):
        """
        測定ボタンのコマンド。
        バリデーションを実行後、ポップアップで名前とメモを入力させ、測定を開始する。
        """
        # --- ステップ①: バリデーションを先に実行 ---
        self.model.update_setting_parms()
        _errors = self.validate_data(asdict(self.model.setting_parms))
        if _errors:
            self.show_error_messages(_errors)
            self.root.focus_force()
            return  # エラーがあればここで処理を中断

        # --- ステップ②: バリデーション通過後にポップアップを表示 ---
        dialog_result = self.view.open_name_input_dialog()

        # キャンセルされたり、名前が空の場合は測定を開始しない
        if not dialog_result or not dialog_result.get("name"):
            self.logger.add_log("測定名が入力されなかったため、測定をキャンセルしました。", level="WARN")
            self.root.focus_force()
            return

        # --- ステップ③: 取得した名前とメモをモデルに設定 ---
        self.model.setting_parms.measurement_name = dialog_result["name"]
        self.model.setting_parms.measurement_notes = dialog_result["notes"]

        # ステート変更
        self.state_handler.update_state(MsrState.measure)
        self.change_button_texture()

        # 並列スレッドで測定メソッドを起動
        self.thread1 = threading.Thread(target=self.start_measurement_thread)
        self.thread1.start()

    def start_measurement_thread(self):
        """
        測定モードに応じて適切な測定メソッドを呼び出す司令塔
        """
        # Modelから現在選択されている測定モードを取得
        measurement_mode = self.model.setting_parms.measurement
        self.logger.add_log(f"測定モード '{measurement_mode}' が選択されました。",
                            level="STATE")

        # モード名と実行するメソッドを辞書で対応付ける
        measurement_methods = {
            "ラマン": self.measure_raman,
            "電場変調ラマン": self.measure_ef_raman,
            "変調信号探索": self.measure_modulation_search
        }

        #測定モードとテーブルヘッダーの対応辞書
        header_definitions = {
            "ラマン": ("#", "波長 (nm)", "測定値 (V)"),
            "電場変調ラマン": ("#", "波長 (nm)", "X (V)"),
            "変調信号探索": ("#", "経過時間 (s)", "位相 (deg)")
        }

        # 対応するメソッドを取得して実行
        target_method = measurement_methods.get(measurement_mode)
        # 未定義の場合はデフォルトのヘッダーを用意
        headers = header_definitions.get(measurement_mode,
                                         ("#", "Col_1", "Col_2"))

        if target_method:
            target_method(headers=headers)  # メソッドを実行
        else:
            # 万が一、対応するメソッドがない場合の処理
            print(f"エラー: 不明な測定モードです - {measurement_mode}")
            messagebox.showerror("エラー", f"未実装の測定モードです: {measurement_mode}")
            self.change_button_texture()  # ボタンの状態を元に戻す

    def finish_button_cmd(self):
        """
        終了ボタンのコマンド
        """
        # CTkMessageboxを使用して確認ダイアログを表示
        msg = CTkMessagebox(
            title="終了確認",
            message="アプリケーションを終了しますか？",  # このメッセージは自由に変更できます
            icon="question",
            option_1="はい",
            option_2="いいえ")

        response = msg.get()

        if response == "はい":
            # GPIBハンドラをクリーンアップ（デバッグモードでない場合）
            if not DEBUG_MODE:
                self.gpib_handler.close_all()

            # Viewのクローズ処理を呼び出してウィンドウを閉じる
            self.view.on_close()
        else:
            # 「いいえ」が選択された場合、メインウィンドウにフォーカスを戻す
            self.root.focus_force()

    def cancel_button_cmd(self):
        """
        中止ボタンのコマンド。
        測定ループを停止させ、途中データの保存を確認する。
        """
        if self.state_handler.msrstate in [MsrState.measure, MsrState.stop]:
            #【変更】状態を「中止」に更新
            self.state_handler.update_state(MsrState.cancel)
            print("--- 測定中止シグナルを送信しました ---")
            self.root.after(100, self._show_cancel_dialog)

    def toggle_pause_cmd(self):
        """
        「停止/再開」ボタンのコマンド。
        一時停止の状態を切り替える。
        """
        if self.state_handler.msrstate == MsrState.measure:
            #【変更】状態を「一時停止」に更新
            self.state_handler.update_state(MsrState.stop)
            self.view.control_button_frame.stop_button.configure(text="再開")
            self.logger.add_log("測定を一時停止しました。", level="STATE")
            print("--- 測定を一時停止しました ---")
        elif self.state_handler.msrstate == MsrState.stop:
            #【変更】状態を「測定中」に戻す
            self.state_handler.update_state(MsrState.measure)
            self.view.control_button_frame.stop_button.configure(text="停止")
            self.logger.add_log("測定を再開しました。", level="STATE")
            print("--- 測定を再開しました ---")

    def _show_cancel_dialog(self):
        """
        中止後の確認ダイアログを表示し、保存処理を行うヘルパーメソッド。
        """
        # 測定データがなければ、処理を終了
        if not self.model.data_container.points:
            self.logger.add_log("測定データが存在しないため、中止処理を終了します。", level="INFO")
            self.state_handler.update_state(MsrState.default)
            self.change_button_texture()
            return

        # データを保存するか確認するダイアログを表示
        msg = CTkMessagebox(title="中止確認",
                            message="測定を中止しました。\nここまでのデータを保存しますか？",
                            icon="question",
                            option_1="はい",
                            option_2="いいえ")
        response = msg.get()
        self.root.focus_force()

        if response == "はい":
            self.logger.add_log("途中経過のデータを保存しています...", level="INFO")
            self.save_manager.save_data_to_file(
                "output_canceled.txt", self.model.data_container.points)
            self.save_manager.save_matplotlib_figure(
                "graph_canceled.png", self.view.graph_frame.plot_manager.fig)
            self.view.graph_frame.canvas.draw()
            print("データの保存が完了しました。")
        else:
            print("データを保存せずに終了します。")

        # 状態をデフォルトに戻し、ボタンの見た目を更新
        self.state_handler.update_state(MsrState.default)
        self.change_button_texture()

    def interruptible_sleep(self, duration: float) -> bool:
        """
        中断可能なsleep処理。
        指定された時間(duration)、0.1秒ごとに状態をチェックしながら待機する。

        Returns:
            bool: 待機が完了した場合はTrue、途中で中断された場合はFalseを返す。
        """
        end_time = time.time() + duration
        while time.time() < end_time:
            # 既存の状態チェックメソッドを呼び出す
            if not self._check_measurement_status():
                self.logger.add_log("待機が中断されました。", level="WARN")
                return False  # 中断されたらFalseを返す

            # 0.1秒だけ待機する
            time.sleep(0.1)

        return True  # 最後まで待機できたらTrueを返す

    def _check_measurement_status(self) -> bool:
        """
        測定ループ内で現在の状態をチェックするヘルパーメソッド。
        一時停止中の待機と、中止の判定を行う。

        Returns:
            bool: 測定を継続してよい場合はTrue、中断すべき場合はFalseを返す。
        """
        # 一時停止状態(`stop`)なら、測定状態(`measure`)に戻るまで待機する
        while self.state_handler.msrstate == MsrState.stop:
            time.sleep(0.1)
            # GUIが固まらないように更新をかける
            self.root.update()

        # 測定状態(`measure`)でない場合 (中止された場合など)
        if self.state_handler.msrstate not in [
                MsrState.measure, MsrState.stop
        ]:
            self.logger.add_log("測定がユーザーによって中断されました。", level="WARN")
            return False

        # 測定を継続してOK
        return True

    @measurement_handler
    def measure_raman(self, headers: tuple, *args, **kwargs):
        """
        【プレースホルダー】ラマン測定を実行
        """
        #待ち時間を取得
        wait_time_ms = float(self.model.setting_parms.time_constant)
        multiplier = int(self.model.setting_parms.time_constant_multiplier)
        wait_seconds = (wait_time_ms * 10E-4) * multiplier
        #グラフ描画
        _MsrData1 = self.model.data_container.MsrData1
        _flattend_list = [item for sublist in _MsrData1
                          for item in sublist]  #最大最小用に1次元配列に変換

        for i, wavelength_list in enumerate(_MsrData1):
            for j, wavelength in enumerate(wavelength_list):

                # 中断すべきならループを抜ける
                if not self._check_measurement_status():
                    return

                #------ 測定処理_start ------
                #波長送り
                self.scan_wavelength(wavelength)
                #待機時間
                if not self.interruptible_sleep(wait_seconds):
                    return  # 待機が中断されたら、メソッドを終了
                #測定結果を取得
                point = MeasurementPoint(
                    wavelength=wavelength,
                    dmm_value=self.wait_for_measurement_dmm6500())
                self.model.data_container.add_point(point)
                #------ 測定処理_end ------

                #測定データをテーブル出力
                self.table_manager.add_row(point.wavelength, point.dmm_value)
                #測定データをロガー出力
                self.logger.add_log(
                    f"測定: ({point.wavelength:.2f} nm, {point.dmm_value:.4f} V)",
                    level="DATA")

                # 中断すべきならループを抜ける(測定後も確認)
                if not self._check_measurement_status():
                    return

                #グラフの更新
                x, y = self.model.data_container.get_plot_data(
                    'wavelength', 'dmm_value')
                self.view.graph_frame.plot_manager.plot_data(
                    x, y, min(_flattend_list), max(_flattend_list))

                #測定データの保存
                self.save_manager.save_data_to_file(
                    "output.txt", self.model.data_container.points)

    @measurement_handler
    def measure_ef_raman(self, headers: tuple, *args, **kwargs):
        """
        【プレースホルダー】電場変調ラマン測定を実行
        """
        print("--- 電場変調ラマン測定モードが選択されました ---")

        # 時定数と定数の読み込み
        time_constant_ms = float(self.model.setting_parms.time_constant)
        multiplier = float(self.model.setting_parms.time_constant_multiplier)
        wait_seconds = (time_constant_ms * 10E-4) * multiplier
        #ロックインアンプの設定
        self.lockin_handler.setup(time_constant_ms * 10E-4)

        #グラフ描画
        _MsrData1 = self.model.data_container.MsrData1
        _flattend_list = [item for sublist in _MsrData1
                          for item in sublist]  #最大最小用に1次元配列に変換
        for i, wavelength_list in enumerate(_MsrData1):
            for j, wavelength in enumerate(wavelength_list):

                # 中断すべきならループを抜ける
                if not self._check_measurement_status():
                    return

                #------ 測定処理_start ------
                #波長送り
                self.scan_wavelength(wavelength)
                #待機時間
                self.logger.add_log(f"ロックインアンプ待機中... ({wait_seconds:.2f}s)",
                                    level="INFO")
                if not self.interruptible_sleep(wait_seconds):
                    return  # 待機が中断されたら、メソッドを終了
                #ロックインアンプの測定データ取得
                li_data = self.lockin_handler.measure()
                time.sleep(0.1)
                #測定結果取得
                point = MeasurementPoint(
                    wavelength=wavelength,
                    dmm_value=self.wait_for_measurement_dmm6500(),
                    R=li_data["R"],
                    theta=li_data["theta"],
                    X=li_data["X"],
                    Y=li_data["Y"])
                self.model.data_container.add_point(point)
                #------ 測定処理_end ------

                #測定データをテーブル出力
                self.table_manager.add_row(point.wavelength, point.X)
                #測定データをロガー出力
                self.logger.add_log(
                    f"測定: ({point.wavelength:.2f} nm, X:{point.X:.4f} V)",
                    level="DATA")

                # 中断すべきならループを抜ける(測定後も確認)
                if not self._check_measurement_status():
                    return

                #グラフの更新
                x, y = self.model.data_container.get_plot_data(
                    'wavelength', 'X')
                self.view.graph_frame.plot_manager.plot_data(
                    x, y, min(_flattend_list), max(_flattend_list))

                #測定データの保存
                self.save_manager.save_data_to_file(
                    "output.txt", self.model.data_container.points)

    @measurement_handler
    def measure_modulation_search(self, headers: tuple, *args, **kwargs):
        """
        変調信号探索モード。ロックインアンプの位相(θ)の時間変化を測定する。
        """
        # --- このモード専用の準備 ---
        time_constant_ms = float(self.model.setting_parms.time_constant)
        self.lockin_handler.setup(time_constant_ms * 10E-4)

        # 測定の総時間（秒）を定義
        total_duration = float(self.model.setting_parms.total_duration)
        # 測定間隔（秒）
        interval = float(self.model.setting_parms.measurement_interval)

        start_time = time.time()
        self.logger.add_log(f"これから{total_duration}秒間、{interval}秒間隔で測定します。",
                            level="INFO")

        # --- 時間ベースの測定ループ ---
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # 規定時間に達したらループを終了
            if elapsed_time >= total_duration:
                break

            # 状態チェック (一時停止・中止)
            if not self._check_measurement_status():
                return

            # --- 測定処理 ---
            li_data = self.lockin_handler.measure()
            point = MeasurementPoint(
                time=elapsed_time,  # 経過時間を記録
                R=li_data["R"],
                theta=li_data["theta"],
                X=li_data["X"],
                Y=li_data["Y"])
            self.model.data_container.add_point(point)
            # -----------------

            # テーブルとログを更新
            self.table_manager.add_row(point.time, point.theta)
            self.logger.add_log(
                f"測定: (Time: {point.time:.2f} s, θ: {point.theta:.4f} deg)",
                level="DATA")

            # グラフを更新 (X軸: time, Y軸: theta)
            x, y = self.model.data_container.get_plot_data('time', 'theta')
            # X軸の範囲を動的に更新
            self.view.graph_frame.plot_manager.plot_data(
                x, y, 0, total_duration)

            # データをリアルタイムで保存
            self.save_manager.save_data_to_file(
                "output.txt", self.model.data_container.points)

            # 次の測定まで待機
            time.sleep(interval)

    def wait_for_measurement_dmm6500(self, timeout=30):
        """
        Args:
            dmm6500_alias:pyvisa _instのalias名
            timeout:タイムアウト時間（秒）

        Returns:
            float:測定値
        """
        start_time = time.time()

        #レスポンス待機
        while True:
            raw_response = self.gpib_handler.query(self.alias_DM6500, ":READ?")

            if raw_response is not None:
                try:
                    # 文字列から数値への変換を試みる
                    _value = float(raw_response)
                    print(_value)
                    return _value  # 変換に成功したら値を返して終了
                except ValueError:
                    # floatへの変換に失敗した場合 (例: "OK1.23"など)
                    self.logger.add_log(
                        f"DMM6500から不正な値 '{raw_response}' を受信しました。",
                        level="WARN")

            #タイムアウトチェック
            if time.time() - start_time > timeout:
                self.logger.add_log(f"DMM6500からの読み取りがタイムアウトしました ({timeout}秒)",
                                    level="ERROR")
                return -0.1  #ダミーデータ

            time.sleep(0.01)  #10ms間隔でチェック

    def sync_wavelength(self):
        """
        分光器の波長を同期するために子ウィンドウを表示して入力された値を連携する
        """
        self.view.open_child_window()  #子ウィンドウを開く
        _wavelength = self.view.get_child_wavelength()  #入力された波長の値
        self.model.var_spectrometer_wavelength.set(
            _wavelength)  #分光器表示波長ウィジェット変数に代入
        self.gpib_handler.write("CT-25",
                                f"WST,{_wavelength}")  #分光器にwriteコマンドを送信
        self.root.focus_force()  #メインウィンドウにフォーカス
        print(_wavelength)

    def change_button_texture(self):
        """
        現在の状態に基づいてボタンの見た目とコマンドを更新する。
        """
        state = self.state_handler.msrstate
        # 測定中かどうかの判定
        is_measuring = state in [MsrState.measure, MsrState.stop]

        #測定中はプルダウンを無効化
        self.view.mode_frame.measurement_combobox.configure(
            state="disabled" if is_measuring else "normal")
        self.view.mode_frame.mode_combobox.configure(
            state="disabled" if is_measuring else "normal")
        self.view.mode_frame.LIamp_combobox.configure(
            state="disabled" if is_measuring else "normal")

        #波長送りボタン
        self.view.mode_frame.send_wavelength_button.configure(
            state="disabled" if is_measuring else "normal",
            fg_color="#A3A3A3" if is_measuring else "#3B8ED0"  # 通常時の色を指定
        )
        # 測定ボタン
        self.view.control_button_frame.measure_button.configure(
            state="disabled" if is_measuring else "normal",
            fg_color="#A3A3A3" if is_measuring else "#34C491")
        # 終了ボタン
        self.view.control_button_frame.finish_button.configure(
            state="disabled" if is_measuring else "normal",
            fg_color="#A3A3A3" if is_measuring else "#2B2B2B")
        # 停止ボタン
        self.view.control_button_frame.stop_button.configure(
            state="normal" if is_measuring else "disabled",
            fg_color="#FAB942" if is_measuring else "#A3A3A3")
        # 中止ボタン
        self.view.control_button_frame.cancel_button.configure(
            state="normal" if is_measuring else "disabled",
            fg_color="#FF6347" if is_measuring else "#A3A3A3")

    def validate_data(self, data: dict):
        """
        測定条件パラメータのチェックを行う
        Returns:
        - errors: List[dict] (エラー内容)
        """
        # 現在の測定モードを取得
        current_mode = data.get("measurement")

        # もしモードが「変調信号探索」なら、特定のバリデーションをスキップ
        if current_mode == "変調信号探索":
            # 必須項目だけをチェック（ここでは待ち時間のみ）
            if not data.get("time_constant"):
                return [{
                    "type":
                    "missing_params",
                    "missing_key":
                    [self.model.setting_parms.get_label("time_constant")]
                }]
            # 問題なければ、空のエラーリストを返してバリデーションを終了
            return []

        # --- これより下は、他の測定モードの場合のみ実行される ---
        errors = []

        # バリデーションから除外するキーのリストを定義
        keys_to_ignore = ["measurement_name", "measurement_notes"]

        combobox_widgets = {
            "measurement": self.view.mode_frame.measurement_combobox,
            "mode": self.view.mode_frame.mode_combobox,
            "LIamp": self.view.mode_frame.LIamp_combobox,
            "filter": self.view.params_frame.filter_combobox,
            "diffraction": self.view.params_frame.diffraction_combobox
        }

        print(self.model.setting_parms)
        # Noneまたは空文字列を持つパラメータをチェック
        _missing_key = [
            self.model.setting_parms.get_label(key)
            for key, value in data.items()
            # 除外リストに含まれていないキーのみをチェック対象とする
            if key not in keys_to_ignore and (value == "" or (
                isinstance(value, list) and all(item == "" for item in value)))
        ]
        if _missing_key:
            errors.append({
                "type": "missing_params",
                "missing_key": _missing_key
            })

        #comboboxの選択が適切であるかをチェック
        _invalid_key = []
        for key, check_combobox in combobox_widgets.items():
            if isinstance(check_combobox, list):  #check_comboboxがlistの場合
                if any(
                        str(data[key][i]) not in str(check_combobox[0].cget(
                            "values")) for i in range(len(data[key]))):
                    _invalid_key.append(
                        self.model.setting_parms.get_label(key))
            elif data[key] not in check_combobox.cget(
                    "values"):  #check_comboboxが単一の場合
                _invalid_key.append(self.model.setting_parms.get_label(key))
        if _invalid_key:
            errors.append({
                "type": "invalid_dropdown",
                "invalid_key": _invalid_key
            })

        #一番上のテキストボックスから入力されているかをチェック
        _missing_top_key = []
        for key, value in data.items():
            if isinstance(value, list):
                if not value[0]:
                    _missing_top_key.append(
                        self.model.setting_parms.get_label(key))
        if _missing_top_key:
            errors.append({
                "type": "missing_top_input",
                "missing_top_key": _missing_top_key
            })

        # 空でない値が連続しているかのチェック
        _non_continuous_key = []
        for key, value in data.items():
            if isinstance(value, list):
                _non_empty_indices = [
                    i for i, elem in enumerate(value) if elem
                ]
                if _non_empty_indices and (_non_empty_indices[-1] -
                                           _non_empty_indices[0] + 1
                                           != len(_non_empty_indices)):
                    _non_continuous_key.append(
                        self.model.setting_parms.get_label(key))
        if _non_continuous_key:
            errors.append({
                "type": "non_continuous_input",
                "non_continuous_key": _non_continuous_key
            })
        #リストの長さチェック
        _len_measurement = sum(1 for item in data["measurement_wavelength"]
                               if item != "")
        if not (sum(1 for item in data["measurement_section"]
                    if item != "") == _len_measurement - 1
                and sum(1 for item in data["filter"]
                        if item != "") == _len_measurement - 1
                and sum(1 for item in data["diffraction"]
                        if item != "") == _len_measurement - 1):
            errors.append({"type": "faild_list_length"})

        return errors

    def show_error_messages(self, errors: List[dict]):
        """
        エラー内容をUIに表示
        """
        for error in errors:
            if error["type"] == "missing_params":
                error_message = f"パラメータが未入力です:{', '.join(error['missing_key'])}"
            elif error["type"] == "invalid_dropdown":
                error_message = f"プルダウンリストが正しくありません:{', '.join(error['invalid_key'])}"
            elif error["type"] == "missing_top_input":
                error_message = f"一番上のテキストボックスから入力してください:{', '.join(error['missing_top_key'])}"
            elif error["type"] == "non_continuous_input":
                error_message = f"上から連続して入力してください:{', '.join(error['non_continuous_key'])}"
            elif error["type"] == "faild_list_length":
                error_message = f"測定区間に対応付けて各パラメータを設定してください"

            #コンソールに出力
            print(error_message)
            #ロガーに出力
            self.logger.add_log(error_message, level="WARN")

    def save_setting_parms(self):
        """
        条件保存ボタンのコマンド
        setting_parmsインスタンスに格納された各値をjson形式で保存
        """
        #入力パラメータの反映
        self.model.update_setting_parms()

        #バリデーション
        _errors = self.validate_data(asdict(self.model.setting_parms))
        if _errors:
            self.show_error_messages(_errors)
            self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す
            return

        #ファイルダイアログによりパスを取得
        _file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                  filetypes=[("JSON files",
                                                              "*.json")])
        # ファイル保存ダイアログでキャンセルされた場合の処理
        if not _file_path:
            self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す
            return
        #jsonファイルとして保存
        with open(_file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.model.setting_parms), f, ensure_ascii=False)
        self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す

    def validate_json(self, data: dict):
        """
        読み込んだデータの形式を検証する関数
        """
        _required_keys = {
            "measurement": str,
            "mode": str,
            "LIamp": str,
            "time_constant": str,
            "time_constant_multiplier": str,
            "measurement_wavelength": List[str],
            "measurement_section": List[str],
            "filter": List[str],
            "diffraction": List[str]
        }

        for key, expected_type in _required_keys.items():
            if key not in data:
                return False
            # 各値の型が一致しているか
            if expected_type == str:
                if not isinstance(data[key], str):
                    return False
            elif expected_type == List[str]:
                if not isinstance(data[key], list):
                    return False
                # リスト内の要素がすべて文字列であるか
                if not all(isinstance(item, str) for item in data[key]):
                    return False
        return True

    def load_setting_parms(self):
        """
        条件読込ボタンのコマンド
        jsonファイルを読み込んでインスタンス変数に代入して画面にも反映
        """
        #ファイルダイアログによりパスを取得
        _file_path = filedialog.askopenfilename(filetypes=[("JSON files",
                                                            "*.json")])
        if not _file_path:  # キャンセルされた場合
            self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す
            return  # 関数を終了
        with open(_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)  #jsonの中身を代入
            #jsonファイルが適切かどうかを検証する
            if not self.validate_json(data):
                messagebox.showerror("形式エラー", "ファイルの内容を確認してください！")
                self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す
                return
        #読み込み内容を画面に反映
        self.model.var_measurement.set(data["measurement"])
        self.model.var_mode.set(data["mode"])
        self.model.var_LIamp.set(data["LIamp"])
        self.model.var_time_constant.set(data["time_constant"])
        self.model.var_time_constant_multiplier.set(
            data["time_constant_multiplier"])
        for i, var in enumerate(self.model.var_measurement_wavelength):
            self.view.params_frame.measurement_wavelengh[i].insert(0, "")
            var.set(data["measurement_wavelength"][i] if i <
                    len(data["measurement_wavelength"]) else "")
        for i, var in enumerate(self.model.var_measurement_section):
            self.view.params_frame.measurement_section[i].insert(0, "")
            var.set(data["measurement_section"][i] if i <
                    len(data["measurement_section"]) else "")
        for i, var in enumerate(self.model.var_filter):
            var.set(data["filter"][i] if i < len(data["filter"]) else "")
        for i, var in enumerate(self.model.var_diffraction):
            var.set(data["diffraction"][i] if i <
                    len(data["diffraction"]) else "")

        self.root.focus_force()  # ポップアップ終了後にフォーカスを元のウィンドウに戻す

    def send_wavelength_CT25(self):
        """
        send_wavelength用
        CT25で波長送りを行う
        """
        while self.gpib_handler.busy_check(self.alias_CT25):
            time.sleep(1)  #ビジー状態のときは待機する
        _display_wavelength = self.gpib_handler.query_bytes(
            self.alias_CT25, "WAV", 16)
        self.model.var_spectrometer_wavelength.set(_display_wavelength)

    def send_wavelength_button_cmd(self):
        """
        波長送りボタンのコマンド
        """
        _send_wavelength = self.model.var_send_wavelength.get()
        self.gpib_handler.write(self.alias_CT25, f"SCN,2,{_send_wavelength}")
        self.thread_send_wavelength = threading.Thread(
            target=self.send_wavelength_CT25)
        self.thread_send_wavelength.start()


if __name__ == "__main__":
    root = ctk.CTk()
    app = Controller(root)
    app.sync_wavelength()  #最初に波長同期ウィンドウを開く
    app.root.mainloop()  #アプリケーション起動
