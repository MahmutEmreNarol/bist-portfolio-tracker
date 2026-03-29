import sys
import json, os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QFrame, QMessageBox, QHeaderView, QMenu, QDialog
)
from PyQt5.QtCore import QDate, Qt, QTimer
import yfinance as yf

class EditDialog(QDialog):
    def __init__(self, alis, adet, hedef, satis):
        super().__init__()
        self.setWindowTitle("Satırı Düzenle")
        self.resize(300, 200)
        layout = QVBoxLayout(self)

        self.line_alis = QLineEdit(str(alis))
        layout.addWidget(QLabel("Alış Fiyatı"))
        layout.addWidget(self.line_alis)

        self.line_adet = QLineEdit(str(adet))
        layout.addWidget(QLabel("Adet"))
        layout.addWidget(self.line_adet)

        self.line_hedef = QLineEdit(str(hedef))
        layout.addWidget(QLabel("Hedef Satış"))
        layout.addWidget(self.line_hedef)

        self.line_satis = QLineEdit(str(satis))
        layout.addWidget(QLabel("Gerçek Satış"))
        layout.addWidget(self.line_satis)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.accept)
        layout.addWidget(self.btn_save)

    def get_values(self):
        return (self.line_alis.text(), self.line_adet.text(),
                self.line_hedef.text(), self.line_satis.text())

class HisseTakip(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hisse Defterim")
        self.setGeometry(100, 100, 1500, 600)
        main_layout = QHBoxLayout(self)

        # ----------------- Sol Panel -----------------
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)

        left_layout.addWidget(QLabel("Hisse Seç"))
        self.combo_hisse = QComboBox()
        left_layout.addWidget(self.combo_hisse)

        left_layout.addWidget(QLabel("Alış Fiyatı"))
        self.line_alis = QLineEdit()
        left_layout.addWidget(self.line_alis)

        left_layout.addWidget(QLabel("Adet / Hacim"))
        self.line_adet = QLineEdit()
        left_layout.addWidget(self.line_adet)

        left_layout.addWidget(QLabel("Hedef Satış Fiyatı (Opsiyonel)"))
        self.line_hedef_satis = QLineEdit()
        left_layout.addWidget(self.line_hedef_satis)

        left_layout.addWidget(QLabel("Stop Loss"))
        self.line_stop = QLineEdit()
        left_layout.addWidget(self.line_stop)

        self.btn_ekle = QPushButton("İşlemi Ekle")
        self.btn_ekle.clicked.connect(self.add_row)
        left_layout.addWidget(self.btn_ekle)

        left_layout.addWidget(QLabel("Gerçek Satış Fiyatı"))
        self.line_satis = QLineEdit()
        left_layout.addWidget(self.line_satis)

        self.btn_guncelle = QPushButton("İşlem Güncelle")
        self.btn_guncelle.clicked.connect(self.update_selected_row)
        left_layout.addWidget(self.btn_guncelle)

        main_layout.addWidget(left_frame, 1)

        # ----------------- Sağ Panel -----------------
        right_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            ["Hisse", "İşlem Tarihi", "Alış", "Adet", "Hedef Satış",
             "Gerçek Satış", "Satış Tarihi", "Kar TL", "Kar %", "Doğruluk Oranı", "Anlık Fiyat"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_menu)
        right_layout.addWidget(self.table)

        self.total_info_label = QLineEdit()
        self.total_info_label.setReadOnly(True)
        self.total_info_label.setText(
            "Toplam Kar TL: 0 | Ortalama Kar %: 0 | Toplam Yatırım: 0 | Net Bakiye: 0 | Ortalama Doğruluk: 0"
        )
        right_layout.addWidget(self.total_info_label)
        main_layout.addLayout(right_layout, 3)

        # ----------------- Load -----------------
        self.load_hisse_list()
        self.load_data()

        # ----------------- Anlık Fiyat Güncelle -----------------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(60 * 1000)  # 1 dakika

    # ----------------- Hisse Listesi -----------------
    def load_hisse_list(self):
        self.hisse_logolar = {}
        if os.path.exists("Hisseler.json"):
            with open("Hisseler.json", "r", encoding="utf-8") as f:
                data = json.load(f)  # data bir liste
            for hisse in data:
                symbol = hisse["symbol"]
                logo = hisse.get("logoUrl", "")
                self.combo_hisse.addItem(symbol)
                self.hisse_logolar[symbol] = logo
        else:
            default_hisseler = ["ASELS", "THYAO", "GARAN"]
            self.combo_hisse.addItems(default_hisseler)
            for symbol in default_hisseler:
                self.hisse_logolar[symbol] = ""

    # ----------------- Verileri Yükle -----------------
    def load_data(self):
        if not os.path.exists("data.json"):
            return
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(row_data):
                if col in [1,6,7,8,9]:  # sadece okunabilir kolonlar
                    self.table.setItem(row, col, ReadOnlyTableWidgetItem(value))
                else:
                    self.table.setItem(row, col, EditableTableWidgetItem(value))
            if len(row_data) < 11:
                self.table.setItem(row, 10, ReadOnlyTableWidgetItem("?"))

        self.update_totals()
        self.update_prices()

    # ----------------- Satır Ekleme -----------------
    def add_row(self):
        hisse = self.combo_hisse.currentText()
        alis = self.line_alis.text().replace(',', '.').strip()
        adet = self.line_adet.text().strip()
        hedef_satis = self.line_hedef_satis.text().replace(',', '.').strip()

        if not alis or not adet:
            QMessageBox.warning(self, "Hata", "Alış fiyatı ve adet zorunlu alanlardır!")
            return

        try:
            alis_f = float(alis)
            adet_f = float(adet)
        except ValueError:
            QMessageBox.warning(self, "Hata", "Geçersiz sayı formatı!")
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, EditableTableWidgetItem(hisse))
        self.table.setItem(row, 1, ReadOnlyTableWidgetItem(QDate.currentDate().toString("dd.MM.yyyy")))
        self.table.setItem(row, 2, EditableTableWidgetItem(f"{alis_f:.2f}"))
        self.table.setItem(row, 3, EditableTableWidgetItem(f"{adet_f:.0f}" if adet_f.is_integer() else f"{adet_f:.2f}"))
        self.table.setItem(row, 4, EditableTableWidgetItem(hedef_satis if hedef_satis else "?"))
        self.table.setItem(row, 5, EditableTableWidgetItem("?"))
        self.table.setItem(row, 6, ReadOnlyTableWidgetItem("?"))
        self.table.setItem(row, 7, ReadOnlyTableWidgetItem("?"))
        self.table.setItem(row, 8, ReadOnlyTableWidgetItem("?"))
        self.table.setItem(row, 9, ReadOnlyTableWidgetItem("?"))
        self.table.setItem(row, 10, ReadOnlyTableWidgetItem("?"))

        self.line_alis.clear()
        self.line_adet.clear()
        self.line_hedef_satis.clear()
        self.line_stop.clear()
        self.update_totals()

    # ----------------- Sağ Tık Menüsü -----------------
    def open_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        menu = QMenu()
        edit_action = menu.addAction("Düzenle")
        delete_action = menu.addAction("Satırı Sil")
        action = menu.exec_(self.table.viewport().mapToGlobal(position))

        if action == delete_action:
            self.delete_row(row)
        elif action == edit_action:
            self.edit_row(row)

    def edit_row(self, row):
        alis = self.table.item(row, 2).text()
        adet = self.table.item(row, 3).text()
        hedef = self.table.item(row, 4).text()
        satis = self.table.item(row, 5).text()

        dlg = EditDialog(alis, adet, hedef, satis)
        if dlg.exec_():
            alis_n, adet_n, hedef_n, satis_n = dlg.get_values()
            self.table.setItem(row, 2, EditableTableWidgetItem(alis_n))
            self.table.setItem(row, 3, EditableTableWidgetItem(adet_n))
            self.table.setItem(row, 4, EditableTableWidgetItem(hedef_n if hedef_n else "?"))
            self.table.setItem(row, 5, EditableTableWidgetItem(satis_n if satis_n else "?"))
            self.update_row_calculations(row)
            self.update_totals()

    def update_row_calculations(self, row):
        try:
            alis_item = self.table.item(row, 2)
            adet_item = self.table.item(row, 3)
            satis_item = self.table.item(row, 5)
            hedef_item = self.table.item(row, 4)
            if not alis_item or not adet_item:
                return
            alis = float(alis_item.text())
            adet = float(adet_item.text())
            satis = satis_item.text()
            if satis != "?":
                satis_f = float(satis)
                kar_tl = (satis_f - alis) * adet
                kar_pct = ((satis_f - alis) / alis) * 100
                self.table.setItem(row, 6, ReadOnlyTableWidgetItem(QDate.currentDate().toString("dd.MM.yyyy")))
                self.table.setItem(row, 7, ReadOnlyTableWidgetItem(f"{kar_tl:.2f}"))
                self.table.setItem(row, 8, ReadOnlyTableWidgetItem(f"{kar_pct:.2f}%"))
                if hedef_item and hedef_item.text() != "?":
                    hedef_f = float(hedef_item.text())
                    dogruluk = (satis_f / hedef_f) * 100
                    self.table.setItem(row, 9, ReadOnlyTableWidgetItem(f"{dogruluk:.2f}%"))
                else:
                    self.table.setItem(row, 9, ReadOnlyTableWidgetItem("?"))
            else:
                self.table.setItem(row, 6, ReadOnlyTableWidgetItem("?"))
                self.table.setItem(row, 7, ReadOnlyTableWidgetItem("?"))
                self.table.setItem(row, 8, ReadOnlyTableWidgetItem("?"))
                self.table.setItem(row, 9, ReadOnlyTableWidgetItem("?"))
        except ValueError:
            pass

    def delete_row(self, row):
        self.table.removeRow(row)
        self.update_totals()

    def update_selected_row(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen güncellenecek satırı seçin.")
            return
        satis_text = self.line_satis.text().replace(',', '.').strip()
        if not satis_text:
            QMessageBox.warning(self, "Hata", "Lütfen gerçek satış fiyatı girin!")
            return
        try:
            satis_f = float(satis_text)
        except ValueError:
            QMessageBox.warning(self, "Hata", "Geçerli sayı girin!")
            return
        self.table.setItem(selected, 5, EditableTableWidgetItem(f"{satis_f:.2f}"))
        self.update_row_calculations(selected)
        self.line_satis.clear()
        self.update_totals()

    # ----------------- Toplamları Güncelle -----------------
    def update_totals(self):
        total_kar_tl = 0.0
        toplam_kar_pct = 0.0
        toplam_yatirim = 0.0
        net_bakiye = 0.0
        toplam_dogruluk = 0.0
        satir_sayisi = 0
        dogruluk_sayisi = 0

        for row in range(self.table.rowCount()):
            alis_item = self.table.item(row, 2)
            adet_item = self.table.item(row, 3)
            satis_item = self.table.item(row, 5)

            if alis_item and adet_item:
                alis = float(alis_item.text())
                adet = float(adet_item.text())
                toplam_yatirim += alis * adet
                if satis_item.text() == "?":
                    net_bakiye += alis * adet

            kar_item = self.table.item(row, 7)
            if kar_item and kar_item.text() != "?":
                total_kar_tl += float(kar_item.text())

            kar_pct_item = self.table.item(row, 8)
            if kar_pct_item and kar_pct_item.text() != "?":
                toplam_kar_pct += float(kar_pct_item.text().replace('%', ''))
                satir_sayisi += 1

            dogruluk_item = self.table.item(row, 9)
            if dogruluk_item and dogruluk_item.text() != "?":
                toplam_dogruluk += float(dogruluk_item.text().replace('%', ''))
                dogruluk_sayisi += 1

        ortalama_kar_pct = toplam_kar_pct / satir_sayisi if satir_sayisi else 0
        ortalama_dogruluk = toplam_dogruluk / dogruluk_sayisi if dogruluk_sayisi else 0

        self.total_info_label.setText(
            f"Toplam Kar TL: {total_kar_tl:.2f} | Ortalama Kar %: {ortalama_kar_pct:.2f}% | "
            f"Toplam Yatırım: {toplam_yatirim:.2f} | Net Bakiye: {net_bakiye:.2f} | "
            f"Ortalama Doğruluk: {ortalama_dogruluk:.2f}%"
        )

        # --- Tabloyu kaydet ---
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ----------------- Anlık Fiyat Güncelle -----------------
    def update_prices(self):
        if self.table.rowCount() == 0:
            return
        tickers = []
        for row in range(self.table.rowCount()):
            hisse = self.table.item(row, 0).text()
            if not hisse.endswith(".IS"):
                hisse += ".IS"
            tickers.append(hisse)
        data = yf.download(tickers=tickers, period="1d", interval="1m", progress=False, group_by='ticker')
        for row in range(self.table.rowCount()):
            hisse = self.table.item(row, 0).text()
            ticker = hisse if hisse.endswith(".IS") else hisse + ".IS"
            try:
                fiyat = data[ticker]['Close'][-1]
                self.table.setItem(row, 10, ReadOnlyTableWidgetItem(f"{fiyat:.2f}"))
            except Exception:
                self.table.setItem(row, 10, ReadOnlyTableWidgetItem("?"))

class EditableTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.setFlags(self.flags() | Qt.ItemIsEditable)

class ReadOnlyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HisseTakip()
    window.showMaximized()
    sys.exit(app.exec_())
