import customtkinter as ctk


class DataTableManager:
    """
    GUIのデータタブへのテーブル表示を専門に担当するクラス。
    """

    def __init__(self, textbox: ctk.CTkTextbox):
        self.textbox = textbox
        self.row_count = 0
        self.column_headers = []  # ヘッダーを保持する変数を追加

    def clear_and_set_header(self, *headers: str):
        """
        テーブルをクリアし、指定されたヘッダーを設定する。

        Args:
            *headers (str): 可変長の引数として列のヘッダー名を受け取る。
                           例: "#", "波長 (nm)", "測定値 (V)"
        """
        self.row_count = 0
        self.column_headers = headers

        #【変更】受け取ったヘッダーで見出しを生成
        header_line = f"{headers[0]:>4} | {headers[1]:<15} | {headers[2]:<20}\n"
        separator = "-" * (len(header_line) + 5) + "\n"

        try:
            self.textbox.configure(state="normal")
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", header_line + separator)  # ヘッダーと区切り線を挿入
            self.textbox.configure(state="disabled")
        except Exception as e:
            print(f"データテーブルのヘッダー設定中にエラーが発生しました: {e}")

    def add_row(self, *rowData):
        """
        新しいデータ行をテーブルの末尾に追加する。

        Args:
            *rowData: 可変長の引数として行データを受け取る。
        """
        self.row_count += 1
        # フォーマットを統一
        new_row = f"{self.row_count:>4} | {rowData[0]:<15.2f} | {rowData[1]:<20.6f}\n"

        try:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", new_row)
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        except Exception as e:
            print(f"データテーブルへの行追加中にエラーが発生しました: {e}")
