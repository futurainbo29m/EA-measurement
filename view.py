import customtkinter
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from plot_manager import PlotManager

FONT_TYPE = "meiryo"


class NameAndNotesDialog(customtkinter.CTkToplevel):
    """測定名とメモを入力するためのカスタムダイアログ"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("測定情報の入力")
        self.geometry("400x300")
        self.grid_columnconfigure(0, weight=1)

        self.result = None  # 結果を保持する変数

        # --- ウィジェットの作成 ---
        self.name_label = customtkinter.CTkLabel(self, text="測定名:")
        self.name_label.grid(row=0,
                             column=0,
                             padx=20,
                             pady=(10, 0),
                             sticky="w")
        self.name_entry = customtkinter.CTkEntry(
            self, placeholder_text="例: サンプルA 初回測定")
        self.name_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.notes_label = customtkinter.CTkLabel(self,
                                                  text="測定メモ (測定条件、サンプル状態など):")
        self.notes_label.grid(row=2,
                              column=0,
                              padx=20,
                              pady=(10, 0),
                              sticky="w")
        self.notes_textbox = customtkinter.CTkTextbox(self, height=100)
        self.notes_textbox.grid(row=3,
                                column=0,
                                padx=20,
                                pady=5,
                                sticky="nsew")
        self.grid_rowconfigure(3, weight=1)  # テキストボックスが伸縮するように

        # --- ボタンフレーム ---
        self.button_frame = customtkinter.CTkFrame(self,
                                                   fg_color="transparent")
        self.button_frame.grid(row=4, column=0, padx=20, pady=10, sticky="")

        self.ok_button = customtkinter.CTkButton(self.button_frame,
                                                 text="OK",
                                                 command=self.on_ok)
        self.ok_button.pack(side="left", padx=(0, 10))

        self.cancel_button = customtkinter.CTkButton(self.button_frame,
                                                     text="キャンセル",
                                                     command=self.on_cancel)
        self.cancel_button.pack(side="left")

    def on_ok(self):
        # 入力された値を辞書として保持
        self.result = {
            "name": self.name_entry.get(),
            "notes": self.notes_textbox.get("1.0", "end-1c")  # テキストボックスの全内容を取得
        }
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

    def get_input(self):
        """ダイアログを表示し、閉じるまで待機して結果を返す"""
        self.grab_set()  # モーダルにする
        self.wait_window()
        return self.result


class View():

    def __init__(self, master, controller):
        self.controller = controller
        self.master = master

        #メンバー変数の設定
        self.fonts = (FONT_TYPE, 12)
        self.csv_filepath = None
        self.master.protocol("WM_DELETE_WINDOW",
                             self.on_close)  # クローズイベントをキャプチャ

        #子ウィンドウで入力された波長を保持する
        self.child_wavelength: float = None

        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        # CustomTkinter のフォームデザイン設定
        customtkinter.set_appearance_mode(
            "light")  # Modes: system (default), light, dark
        customtkinter.set_default_color_theme(
            "blue")  # Themes: blue (default), dark-blue, green

        # フォームサイズ設定
        self.master.geometry("1200x700")
        self.master.title("測定アプリケーション")
        self.master.minsize(920, 750)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        #フレーム設定
        outline_margin = 5
        widget_space = 5
        frame_margin = 5

        ##上部フレーム
        self.frame_1 = customtkinter.CTkFrame(self.master)
        self.frame_1.grid(row=0,
                          column=0,
                          padx=outline_margin,
                          pady=(outline_margin, widget_space),
                          sticky="nswe")
        self.frame_1.grid_columnconfigure(0, weight=6)
        self.frame_1.grid_columnconfigure(0, weight=1)
        self.frame_1.grid_rowconfigure(0, weight=1)

        ###グラフフレーム
        self.graph_frame = Graph_Frame(self.frame_1, header_name="グラフ")
        self.graph_frame.grid(row=0,
                              column=0,
                              padx=(outline_margin, 0),
                              pady=outline_margin,
                              sticky="nsew")

        ###測定モードフレーム
        self.mode_frame = Mode_Frame(self.frame_1, header_name="測定モード")
        self.mode_frame.grid(row=0,
                             column=1,
                             padx=(widget_space, frame_margin),
                             pady=outline_margin,
                             sticky="nsew")

        ##下部フレーム
        self.frame_2 = customtkinter.CTkFrame(self.master)
        self.frame_2.grid(row=1,
                          column=0,
                          padx=outline_margin,
                          pady=(0, outline_margin),
                          sticky="nswe")
        self.frame_2.grid_columnconfigure(0, weight=1)

        ###テキスト関連フレーム
        self.text_frame = Text_Frame(self.frame_2, header_name="テキスト領域")
        self.text_frame.grid(row=0,
                             column=0,
                             padx=outline_margin,
                             pady=outline_margin,
                             sticky="we")
        self.text_frame.grid_columnconfigure(0, weight=1)

        ###パラメータフレーム
        self.params_frame = Params_Frame(self.frame_2, header_name="測定パラメータ")
        self.params_frame.grid(row=0,
                               column=1,
                               padx=(0, outline_margin),
                               pady=outline_margin,
                               sticky="ns")

        ###制御ボタンフレーム
        self.control_button_frame = Control_Button_Frame(self.frame_2,
                                                         header_name="制御ボタン")
        self.control_button_frame.grid(row=0,
                                       column=2,
                                       padx=(0, outline_margin),
                                       pady=outline_margin,
                                       sticky="ns")

    def on_close(self):
        """
        終了時のウィジェットを適切にクローズするための処理
        """
        self.graph_frame.plot_manager.close_plt()  #グラフ領域を終了
        self.master.destroy()  # メインウィンドウを終了
        self.master.quit()

    def open_child_window(self):
        """
        波長同期する子ウィンドウを開く関数
        """

        def input_wavelength():
            """
            子ウィンドウで入力された波長をメインウィンドウに反映し、子ウィンドウを閉じる
            """
            _input_value = self.child_entry.get()
            try:
                self.child_wavelength = float(_input_value)
                self.child_window.destroy()
            except ValueError:
                messagebox.showerror("入力エラー", "有効な数値を入力してください！")

        #子ウィンドウを作成
        self.child_window = customtkinter.CTkToplevel(self.master)
        self.child_window.geometry("400x170")
        self.child_window.title("波長同期ウィンドウ")
        #テキストラベル
        self.child_label = customtkinter.CTkLabel(
            self.child_window, text="分光器に表示されている波長を入力してください", font=self.fonts)
        self.child_label.pack(pady=(20, 10))  # 上下の余白を設定
        # 中央に配置する入力エリア（フレーム内に入力ボックスと"nm"ラベルを配置）
        self.input_frame = customtkinter.CTkFrame(self.child_window,
                                                  fg_color='transparent')
        self.input_frame.pack(pady=(10, 10))  # 上下の余白を設定
        #入力ボックス
        self.child_entry = customtkinter.CTkEntry(
            self.input_frame,
            placeholder_text="波長を入力",
            justify="center",  # 入力を中央寄せ
            width=200  # 入力ボックスの幅
        )
        self.child_entry.pack(side="left", padx=(10, 5))  # 右に少し余白を設定
        # "nm" テキストラベル
        self.child_nm_label = customtkinter.CTkLabel(self.input_frame,
                                                     text="nm",
                                                     font=self.fonts)
        self.child_nm_label.pack(side="left")  # 入力ボックスの右に配置
        # ボタン
        self.child_button = customtkinter.CTkButton(self.child_window,
                                                    text="波長を同期",
                                                    command=input_wavelength)
        self.child_button.pack(pady=(10, 20))  # 上下の余白を設定

        # 子ウィンドウをモーダルにする
        self.child_window.grab_set()
        self.master.wait_window(self.child_window)

    def get_child_wavelength(self):
        return self.child_wavelength

    def open_name_input_dialog(self):
        """
        測定名とメモを入力するためのカスタムダイアログを開く。
        """
        dialog = NameAndNotesDialog(self.master)
        return dialog.get_input()


#グラフのフレーム
class Graph_Frame(customtkinter.CTkFrame):

    def __init__(self, *args, header_name, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (FONT_TYPE, 12)
        self.header_name = header_name
        #グラフ機能のインポート
        self.plot_manager = PlotManager()
        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        #グラフの表示（起動時）
        self.canvas = FigureCanvasTkAgg(self.plot_manager.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0,
                                         column=0,
                                         padx=10,
                                         pady=10,
                                         sticky="nsew")
        self.plot_manager.set_plot_style()
        #ツールバーの表示
        self.toolbar = NavigationToolbar2Tk(self.canvas,
                                            self,
                                            pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, pady=(0, 10))


#測定モードのフレーム
class Mode_Frame(customtkinter.CTkFrame):

    def __init__(self, *args, header_name, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (FONT_TYPE, 12)
        self.header_name = header_name
        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        _label_pady = 0
        _box_pady = 0
        #測定の種類プルダウン
        ##プルダウンの前にラベルを表示する
        self.measurement_label = customtkinter.CTkLabel(self,
                                                        text="測定の種類",
                                                        font=self.fonts)
        self.measurement_label.grid(row=0,
                                    column=0,
                                    padx=10,
                                    pady=(6, _label_pady),
                                    sticky="w")
        ##プルダウンを表示する
        self.measurement_combobox = customtkinter.CTkComboBox(
            self,
            values=["ラマン", "電場変調ラマン", "変調信号探索"],
            width=170,
            font=self.fonts)
        self.measurement_combobox.grid(row=1,
                                       column=0,
                                       padx=10,
                                       pady=_box_pady,
                                       columnspan=2)
        self.measurement_combobox.set("")

        #測定モードプルダウン
        ##プルダウンの前にラベルを表示する
        self.mode_label = customtkinter.CTkLabel(self,
                                                 text="測定モード",
                                                 font=self.fonts)
        self.mode_label.grid(row=2,
                             column=0,
                             padx=10,
                             pady=_label_pady,
                             sticky="w")
        ##プルダウンを表示する
        self.mode_combobox = customtkinter.CTkComboBox(
            self, values=["X", "Y", "R", "θ", "V"], width=170, font=self.fonts)
        self.mode_combobox.grid(row=3,
                                column=0,
                                padx=2,
                                pady=_box_pady,
                                columnspan=2)
        self.mode_combobox.set("")

        #LIアンププルダウン
        ##プルダウンの前にラベルを表示する
        self.LIamp_label_before = customtkinter.CTkLabel(self,
                                                         text="LIアンプ",
                                                         font=self.fonts)
        self.LIamp_label_before.grid(row=4,
                                     column=0,
                                     padx=10,
                                     pady=_label_pady,
                                     sticky="w")
        ##プルダウンを表示する
        self.LIamp_combobox = customtkinter.CTkComboBox(self,
                                                        values=["LI5650"],
                                                        width=170,
                                                        font=self.fonts)
        self.LIamp_combobox.grid(row=5, column=0, pady=_box_pady, columnspan=2)
        self.LIamp_combobox.set("")

        # --- 時定数入力フレーム ---
        ## ラベル
        self.time_constant_label = customtkinter.CTkLabel(self,
                                                          text="時定数",
                                                          font=self.fonts)
        self.time_constant_label.grid(row=6,
                                      column=0,
                                      padx=10,
                                      pady=_label_pady,
                                      sticky="w")

        ## 入力ウィジェットをまとめるフレーム
        self.time_constant_frame = customtkinter.CTkFrame(
            self, fg_color="transparent")
        self.time_constant_frame.grid(row=7,
                                      column=0,
                                      columnspan=2,
                                      padx=10,
                                      sticky="ew")

        ## 時定数(ms)の入力ボックス
        self.time_constant_textbox = customtkinter.CTkEntry(
            master=self.time_constant_frame,
            placeholder_text="1000",
            width=80,  # 幅を調整
            font=self.fonts,
            justify="right")
        self.time_constant_textbox.grid(row=0,
                                        column=0,
                                        padx=(10, 0),
                                        pady=_box_pady,
                                        sticky="e")
        self.time_constant_textbox.insert(0, 1000)

        ## "ms  ×" のラベル
        self.time_constant_unit_label = customtkinter.CTkLabel(
            self.time_constant_frame, text="ms  ×", font=self.fonts)
        self.time_constant_unit_label.grid(row=0,
                                           column=1,
                                           padx=4,
                                           pady=_label_pady)

        ## 定数（乗数）の入力ボックス
        self.time_constant_multiplier_textbox = customtkinter.CTkEntry(
            master=self.time_constant_frame,
            width=40,  # 幅を調整
            font=self.fonts,
            justify="right")
        self.time_constant_multiplier_textbox.grid(row=0,
                                                   column=2,
                                                   padx=(0, 10),
                                                   pady=_box_pady,
                                                   sticky="w")
        self.time_constant_multiplier_textbox.insert(0, 6)

        #------- 波長表示フレーム -------
        self.grid_rowconfigure(19, weight=1)  #フレームを下部に寄せる
        self.view_wavelength_frame = customtkinter.CTkFrame(self)
        self.view_wavelength_frame.grid(row=20,
                                        column=0,
                                        padx=8,
                                        pady=(8, 8),
                                        columnspan=2,
                                        sticky="we")
        ##分光器表示波長
        ###ラベルを表示
        self.spectrometer_wavelength_label_before = customtkinter.CTkLabel(
            self.view_wavelength_frame, text="分光器表示波長", font=self.fonts)
        self.spectrometer_wavelength_label_before.grid(row=0,
                                                       column=0,
                                                       padx=10,
                                                       pady=(2, 0),
                                                       sticky="w")
        ###波長の値を表示
        self.spectrometer_wavelength_label = customtkinter.CTkLabel(
            self.view_wavelength_frame,
            text="400",
            font=self.fonts,
            width=120,
            height=25,
            bg_color="transparent",
            fg_color="#9FA09D",
            corner_radius=6)
        self.spectrometer_wavelength_label.grid(row=1,
                                                column=0,
                                                padx=(20, 0),
                                                pady=(0, 2),
                                                sticky="e")
        ###nmを表示
        self.spectrometer_wavelength_label_after = customtkinter.CTkLabel(
            self.view_wavelength_frame, text="nm", font=self.fonts)
        self.spectrometer_wavelength_label_after.grid(row=1,
                                                      column=1,
                                                      padx=(5, 15),
                                                      pady=(0, 2),
                                                      sticky="w")

        ##測定波長
        ###ラベルを表示
        self.now_wavelength_label_before = customtkinter.CTkLabel(
            self.view_wavelength_frame, text="測定波長", font=self.fonts)
        self.now_wavelength_label_before.grid(row=2,
                                              column=0,
                                              padx=10,
                                              pady=(0, 0),
                                              sticky="w")
        ###波長の値を表示
        self.now_wavelength_label = customtkinter.CTkLabel(
            self.view_wavelength_frame,
            text="400",
            font=self.fonts,
            width=120,
            height=25,
            bg_color="transparent",
            fg_color="#9FA09D",
            corner_radius=6)
        self.now_wavelength_label.grid(row=3,
                                       column=0,
                                       padx=(20, 0),
                                       pady=(0, _box_pady),
                                       sticky="e")
        ###nmを表示
        self.now_wavelength_label_after = customtkinter.CTkLabel(
            self.view_wavelength_frame, text="nm", font=self.fonts)
        self.now_wavelength_label_after.grid(row=3,
                                             column=1,
                                             padx=(5, 15),
                                             pady=(0, _box_pady),
                                             sticky="w")

        #波長送り
        ##波長送りラベル
        self.send_wavelength_label = customtkinter.CTkLabel(
            self.view_wavelength_frame, text="波長送り", font=self.fonts)
        self.send_wavelength_label.grid(row=4,
                                        column=0,
                                        padx=10,
                                        pady=_label_pady,
                                        sticky="w")
        ##波長送りフレーム
        self.send_wavelength_frame = customtkinter.CTkFrame(
            self.view_wavelength_frame, fg_color="transparent")
        self.send_wavelength_frame.grid(row=5,
                                        column=0,
                                        padx=5,
                                        pady=(_box_pady, 8),
                                        columnspan=2,
                                        sticky="we")
        self.send_wavelength_frame.columnconfigure(1, weight="1")
        ##波長入力テキストボックス
        self.send_wavelength_textbox = customtkinter.CTkEntry(
            self.send_wavelength_frame,
            placeholder_text="400",
            width=90,
            font=self.fonts,
            justify=customtkinter.RIGHT)  #justifyは位置を指定
        self.send_wavelength_textbox.grid(row=0,
                                          column=0,
                                          padx=(10, 0),
                                          pady=0,
                                          sticky="w")
        self.send_wavelength_textbox.insert(0, 400)
        ##テキストボックスの後ろにラベルを表示する
        self.now_wavelength_label_after = customtkinter.CTkLabel(
            self.send_wavelength_frame, text="nm", font=self.fonts)
        self.now_wavelength_label_after.grid(row=0,
                                             column=1,
                                             padx=5,
                                             pady=_label_pady,
                                             sticky="w")
        ##波長送りボタン
        self.send_wavelength_button = customtkinter.CTkButton(
            self.send_wavelength_frame,
            text="send",
            font=self.fonts,
            width=30,
            height=26,
            anchor="center")
        self.send_wavelength_button.grid(row=0,
                                         column=2,
                                         padx=(2, 6),
                                         pady=2,
                                         sticky="e")

        #------------ 変調信号探索モード用フレーム ------------
        self.search_mode_frame = customtkinter.CTkFrame(self,
                                                        fg_color="transparent")

        # --- ラベル ---
        label = customtkinter.CTkLabel(self.search_mode_frame,
                                       text="測定時間 / 間隔",
                                       font=self.fonts)
        label.grid(row=0, column=0, padx=10, pady=_label_pady, sticky="w")

        # --- 入力ウィジェットをまとめる内部フレーム ---
        input_frame = customtkinter.CTkFrame(self.search_mode_frame,
                                             fg_color="transparent")
        input_frame.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")

        # 測定総時間の入力ボックス
        self.total_duration_entry = customtkinter.CTkEntry(
            master=input_frame,
            width=80,  # 幅を調整
            font=self.fonts,
            justify="right")
        self.total_duration_entry.grid(row=0,
                                       column=0,
                                       padx=(10, 0),
                                       pady=0,
                                       sticky="e")

        # "s /" のラベル
        unit_label_1 = customtkinter.CTkLabel(input_frame,
                                              text="s /",
                                              font=self.fonts)
        unit_label_1.grid(row=0, column=1, padx=4, pady=0)

        # 測定間隔の入力ボックス
        self.interval_entry = customtkinter.CTkEntry(
            master=input_frame,
            width=40,  # 幅を調整
            font=self.fonts,
            justify="right")
        self.interval_entry.grid(row=0, column=2, padx=0, pady=0, sticky="w")

        # 間隔の後ろの "s" 単位ラベル
        unit_label_2 = customtkinter.CTkLabel(input_frame,
                                              text="s",
                                              font=self.fonts)
        unit_label_2.grid(row=0, column=3, padx=(4, 5), pady=0, sticky="w")

    def update_labels(self, mode: str):
        """選択された測定モードに応じて、ラベルのテキストを変更する"""
        if mode == "ラマン":
            self.time_constant_label.configure(text="待ち時間")
        else:
            # 他_のモードでは"時定数"に戻す
            self.time_constant_label.configure(text="時定数")

    def update_parameter_visibility(self, mode: str):
        """選択された測定モードに応じて、パラメータ入力欄の表示/非表示を切り替える"""
        if mode == "変調信号探索":
            # 専用フレームをグリッドに配置して表示
            self.search_mode_frame.grid(row=15,
                                        column=0,
                                        columnspan=2,
                                        padx=0,
                                        pady=0,
                                        sticky="we")
        else:
            # 他のモードでは専用フレームをグリッドから外して非表示
            self.search_mode_frame.grid_forget()


#テキスト関連フレーム
class Text_Frame(customtkinter.CTkFrame):

    def __init__(self, *args, header_name, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (FONT_TYPE, 12)
        self.header_name = header_name
        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        _box_height = 150
        # --- タブビューの作成 ---
        self.tab_view = customtkinter.CTkTabview(self,
                                                 height=_box_height,
                                                 fg_color="transparent")
        self.tab_view.grid(row=0, column=0, padx=2, pady=(0, 3), sticky="we")
        # 「ログ」タブの作成
        self.tab_view.add(" ログ ")
        self.log_textbox = customtkinter.CTkTextbox(
            self.tab_view.tab(" ログ "),
            font=self.fonts,
            wrap="word",
            height=_box_height)  # 長い行を折り返す
        self.log_textbox.pack(expand=True, fill="both", padx=0, pady=0)
        self.log_textbox.configure(state="disabled")  # 初期状態では編集不可にする

        # 「データ」タブの作成
        self.tab_view.add("データ")
        self.data_textbox = customtkinter.CTkTextbox(
            self.tab_view.tab("データ"), font=("Courier", 12),
            height=_box_height)  # 等幅フォントで見やすくする
        self.data_textbox.pack(expand=True, fill="both", padx=0, pady=0)
        self.data_textbox.configure(state="disabled")


#測定条件入力フレーム
class Params_Frame(customtkinter.CTkFrame):

    def __init__(self, *args, header_name, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (FONT_TYPE, 12)
        self.header_name = header_name
        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        #測定波長
        self.measurement_wavelengh = []
        ##テキストを表示する
        self.measurement_wavelengh_label = customtkinter.CTkLabel(
            self, text="測定波長", font=self.fonts)
        self.measurement_wavelengh_label.grid(row=0, column=0, padx=2, pady=0)
        for i in range(0, 5):
            ##テキストボックスを表示する
            _padding_y = 2
            self.measurement_wavelengh.append(
                customtkinter.CTkEntry(self,
                                       placeholder_text="",
                                       width=70,
                                       font=self.fonts,
                                       justify=customtkinter.RIGHT))
            self.measurement_wavelengh[i].grid(row=i + 2,
                                               column=0,
                                               padx=6,
                                               pady=_padding_y,
                                               sticky="e")
            ##テキストボックスの後ろにラベルを表示する
            self.measurement_wavelengh_label_after = customtkinter.CTkLabel(
                self, text="nm", font=self.fonts)
            self.measurement_wavelengh_label_after.grid(row=i + 2,
                                                        column=1,
                                                        padx=2,
                                                        pady=2,
                                                        sticky="w")

        #測定間隔
        self.measurement_section = []
        ##テキストを表示する
        self.measurement_section_label = customtkinter.CTkLabel(
            self, text="測定間隔", font=self.fonts)
        self.measurement_section_label.grid(row=0, column=2, padx=2, pady=0)
        for i in range(0, 4):
            ##テキストボックスを表示する
            self.measurement_section.append(
                customtkinter.CTkEntry(master=self,
                                       placeholder_text="",
                                       width=70,
                                       font=self.fonts,
                                       justify=customtkinter.RIGHT))
            self.measurement_section[i].grid(row=i + 2,
                                             column=2,
                                             rowspan=2,
                                             padx=2,
                                             pady=2,
                                             sticky="e")
            ##テキストボックスの後ろにラベルを表示する
            self.measurement_section_label_after = customtkinter.CTkLabel(
                self, text="nm", font=self.fonts)
            self.measurement_section_label_after.grid(row=i + 2,
                                                      column=3,
                                                      rowspan=2,
                                                      padx=2,
                                                      pady=2,
                                                      sticky="w")

        #フィルタ
        self.filter_combobox = []
        ##テキストを表示する
        self.filter_label = customtkinter.CTkLabel(self,
                                                   text="フィルタ",
                                                   font=self.fonts)
        self.filter_label.grid(row=0, column=4, padx=2, pady=0)
        for i in range(0, 4):
            ##プルダウンを表示する
            self.filter_combobox.append(
                customtkinter.CTkComboBox(self,
                                          values=["1"],
                                          width=70,
                                          font=self.fonts))
            self.filter_combobox[i].grid(row=i + 2,
                                         column=4,
                                         rowspan=2,
                                         padx=(10, 2),
                                         pady=2)
            self.filter_combobox[i].set("")

        #回折格子
        self.diffraction_combobox = []
        # テキストを表示する
        self.diffraction_label = customtkinter.CTkLabel(self,
                                                        text="回折格子",
                                                        font=self.fonts)
        self.diffraction_label.grid(row=0, column=5, padx=(10, 2), pady=0)
        for i in range(0, 4):
            ##プルダウンを表示する
            self.diffraction_combobox.append(
                customtkinter.CTkComboBox(self,
                                          values=[
                                              "2400", "1800", "1200", "600",
                                              "300", "150", "120", "60", "30"
                                          ],
                                          width=80,
                                          font=self.fonts))
            self.diffraction_combobox[i].grid(row=i + 2,
                                              column=5,
                                              rowspan=2,
                                              padx=(10, 2),
                                              pady=2)
            self.diffraction_combobox[i].set("")
            ##テキストボックスの後ろにラベルを表示する
            self.measurement_section_label_after = customtkinter.CTkLabel(
                self, text="本/mm", font=self.fonts)
            self.measurement_section_label_after.grid(row=i + 2,
                                                      column=6,
                                                      rowspan=2,
                                                      padx=(2, 6),
                                                      pady=2,
                                                      sticky="w")

        #区切り線を挿入
        self.separator = customtkinter.CTkFrame(self,
                                                height=2,
                                                fg_color="gray")
        self.separator.grid(row=1,
                            column=0,
                            columnspan=7,
                            padx=6,
                            pady=(0, 6),
                            sticky="ew")


#制御ボタンフレーム
class Control_Button_Frame(customtkinter.CTkFrame):

    def __init__(self, *args, header_name, **kwargs):
        super().__init__(*args, **kwargs)

        self.fonts = (FONT_TYPE, 12)
        self.header_name = header_name
        #フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        #GPIB機器動作確認ボタン
        ##GPIB機器動作確認フレーム
        self.check_GPIB_frame_fonts = (FONT_TYPE, 8)
        self.check_GPIB_frame = customtkinter.CTkFrame(self,
                                                       fg_color="transparent")
        self.check_GPIB_frame.grid(row=0,
                                   column=0,
                                   padx=5,
                                   pady=2,
                                   sticky="we")
        self.check_GPIB_frame.columnconfigure(1, weight=1)
        ##分光器確認ボタン
        self.check_CT25_button = customtkinter.CTkButton(
            self.check_GPIB_frame,
            text="CT25",
            font=self.check_GPIB_frame_fonts,
            width=40,
            height=20,
            anchor="center")
        self.check_CT25_button.grid(row=0,
                                    column=0,
                                    padx=(0, 2),
                                    pady=(5, 2),
                                    sticky="w")
        ##デジマル確認ボタン
        self.check_DMM6500_button = customtkinter.CTkButton(
            self.check_GPIB_frame,
            text="DMM6500",
            font=self.check_GPIB_frame_fonts,
            width=40,
            height=20,
            anchor="center")
        self.check_DMM6500_button.grid(row=0,
                                       column=1,
                                       padx=(2, 2),
                                       pady=(5, 2),
                                       sticky="")
        ##ロックインアンプ確認ボタン
        self.check_LIamp_button = customtkinter.CTkButton(
            self.check_GPIB_frame,
            text="LIamp",
            font=self.check_GPIB_frame_fonts,
            width=40,
            height=20,
            anchor="center")
        self.check_LIamp_button.grid(row=0,
                                     column=2,
                                     padx=(2, 0),
                                     pady=(5, 2),
                                     sticky="e")

        #条件保存・読み込みボタン
        ##条件保存・読み込みフレーム
        self.load_save_setting_button_frame = customtkinter.CTkFrame(
            self, fg_color="transparent")
        self.load_save_setting_button_frame.grid(row=1,
                                                 column=0,
                                                 padx=5,
                                                 pady=2,
                                                 sticky="we")
        self.load_save_setting_button_frame.columnconfigure(0, weight=1)
        ###条件読込のボタンを表示する
        self.load_setting_button = customtkinter.CTkButton(
            self.load_save_setting_button_frame,
            text="条件読込",
            font=self.fonts,
            width=90,
            height=26,
            anchor="center")
        self.load_setting_button.grid(row=0,
                                      column=0,
                                      padx=(0, 2),
                                      pady=2,
                                      sticky="w")
        ###条件保存のボタンを表示する
        self.save_setting_button = customtkinter.CTkButton(
            self.load_save_setting_button_frame,
            text="条件保存",
            font=self.fonts,
            width=90,
            height=26,
            anchor="center")
        self.save_setting_button.grid(row=0,
                                      column=1,
                                      padx=(2, 0),
                                      pady=2,
                                      sticky="e")

        #ボタンフレーム
        button_frame_button_height = 40
        self.button_frame = customtkinter.CTkFrame(self,
                                                   fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=5, pady=20, sticky="we")
        self.button_frame.columnconfigure(0, weight=1)
        ##測定のボタンを表示する
        self.measure_button = customtkinter.CTkButton(
            master=self.button_frame,
            text="測定",
            font=self.fonts,
            width=90,
            height=button_frame_button_height,
            anchor="center",
            fg_color="#34C491")
        self.measure_button.grid(row=1,
                                 column=0,
                                 padx=(0, 2),
                                 pady=(2, 0),
                                 sticky="sw")
        ##停止のボタンを表示する
        self.stop_button = customtkinter.CTkButton(
            master=self.button_frame,
            text="停止",
            font=self.fonts,
            state="disable",
            width=90,
            height=button_frame_button_height,
            anchor="center",
            fg_color="#A3A3A3")
        self.stop_button.grid(row=0,
                              column=0,
                              padx=(0, 2),
                              pady=(0, 2),
                              sticky="nw")

        ##中止のボタンを表示する
        self.cancel_button = customtkinter.CTkButton(
            master=self.button_frame,
            text="中止",
            font=self.fonts,
            state="disable",
            width=90,
            height=button_frame_button_height,
            anchor="center",
            fg_color="#A3A3A3")
        self.cancel_button.grid(row=0,
                                column=1,
                                padx=(2, 0),
                                pady=(0, 2),
                                sticky="ne")
        ##終了のボタンを表示する
        self.finish_button = customtkinter.CTkButton(
            master=self.button_frame,
            text="終了",
            font=self.fonts,
            width=90,
            height=button_frame_button_height,
            anchor="center",
            fg_color="#2B2B2B")
        self.finish_button.grid(row=1,
                                column=1,
                                padx=(2, 0),
                                pady=(2, 0),
                                sticky="se")
