import customtkinter as ctk
from typing import List

# --- アプリケーション本体からViewクラスをインポート ---
from view import View

# --- デバッグ設定 ---
# Trueにすると、各フレームの境界線が分かりやすいように背景色が変わります
SHOW_BORDERS = True

# -------------------


class DummyModel:
    """
    Viewの初期化に必要な、Modelのダミー（偽物）。
    UI部品（ウィジェット）が必要とする変数（StringVarなど）だけを持つ。
    """

    def __init__(self, parent):
        self.var_measurement = ctk.StringVar(parent)
        self.var_mode = ctk.StringVar(parent)
        self.var_LIamp = ctk.StringVar(parent)
        self.var_wait_time = ctk.StringVar(parent)
        self.var_total_duration = ctk.StringVar(parent)
        self.var_measurement_interval = ctk.StringVar(parent)
        self.var_measurement_wavelength: List[ctk.StringVar] = [
            ctk.StringVar(parent) for _ in range(5)
        ]
        self.var_measurement_section: List[ctk.StringVar] = [
            ctk.StringVar(parent) for _ in range(4)
        ]
        self.var_filter: List[ctk.StringVar] = [
            ctk.StringVar(parent) for _ in range(4)
        ]
        self.var_diffraction: List[ctk.StringVar] = [
            ctk.StringVar(parent) for _ in range(4)
        ]
        self.var_spectrometer_wavelength = ctk.StringVar(parent)
        self.var_now_wavelength = ctk.StringVar(parent)
        self.var_send_wavelength = ctk.StringVar(parent)


class DummyController:
    """Viewの初期化に必要な、Controllerのダミー。"""

    def __init__(self, parent):
        # Viewが `self.controller.model` を参照できるように、
        # ダミーのModelインスタンスを持たせておく。
        self.model = DummyModel(parent)


# --- ここからがプレビュー表示のメイン処理 ---
if __name__ == "__main__":
    # 1. メインウィンドウを作成
    root = ctk.CTk()

    # 2. ダミーのControllerを作成
    dummy_controller = DummyController(root)

    # 3. ダミーのControllerを渡して、Viewクラスのインスタンスを作成
    #    これにより、アプリケーションの見た目だけが構築される
    app_view = View(root, dummy_controller)

    # 4. (任意) フレームの境界線を色付けして分かりやすくする
    if SHOW_BORDERS:
        app_view.frame_1.configure(fg_color="lightcoral")
        app_view.frame_2.configure(fg_color="skyblue")
        app_view.graph_frame.configure(fg_color="#FFF5E0")
        app_view.mode_frame.configure(fg_color="#D8E3E7")
        app_view.text_frame.configure(fg_color="#F6F6F6")
        app_view.params_frame.configure(fg_color="#F6F6F6")
        app_view.control_button_frame.configure(fg_color="#F6F6F6")

    # 5. ウィンドウを表示
    root.mainloop()
