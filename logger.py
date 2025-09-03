import customtkinter as ctk
from datetime import datetime


class Logger:
    """
    GUIのテキストボックスへのログ出力を専門に担当するクラス。
    """

    def __init__(self, textbox: ctk.CTkTextbox):
        self.textbox = textbox
        # ログレベルに応じた色を設定
        self.textbox.tag_config("INFO", foreground="black")
        self.textbox.tag_config("STATE", foreground="blue")
        self.textbox.tag_config("GPIB", foreground="green")
        self.textbox.tag_config("DATA", foreground="#653496")  # 紫色
        self.textbox.tag_config("WARN", foreground="orange")
        self.textbox.tag_config("ERROR", foreground="red")

    def add_log(self, message: str, level: str = "INFO"):
        """
        指定されたレベルでテキストボックスにログメッセージを追加する。

        Args:
            message (str): ログに表示するメッセージ。
            level (str): ログのレベル (INFO, STATE, GPIB, WARN, ERRORなど)。
        """
        try:
            # テキストボックスを一時的に編集可能にする
            self.textbox.configure(state="normal")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"

            self.textbox.insert("end", log_entry, level.upper())
            self.textbox.see("end")  # 自動で最下部にスクロール

            # 再び編集不可に戻す
            self.textbox.configure(state="disabled")
        except Exception as e:
            print(f"ロガーでエラーが発生しました: {e}")
