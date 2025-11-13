#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 윈도우용 지뢰찾기 (Minesweeper) — Tkinter 기반
작성자: GitHub Copilot (예시)
요구사항: Python 3 (tkinter 포함; Windows 기본 설치에 포함됨)
실행: python minesweeper.py
선택: pyinstaller --noconsole --onefile minesweeper.py 로 단일 exe 생성 가능
"""

import tkinter as tk
from tkinter import messagebox
import random
import time
import sys

# 색상 설정 (숫자별)
NUM_COLORS = {
    1: "#0000FF",  # 파랑
    2: "#008200",  # 초록
    3: "#FF0000",  # 빨강
    4: "#000084",
    5: "#840000",
    6: "#008284",
    7: "#000000",
    8: "#808080",
}

class Minesweeper:
    def __init__(self, master):
        self.master = master
        master.title("지뢰찾기 (Minesweeper)")
        # 기본 난이도: 초급
        self.difficulties = {
            "초급 (9×9, 10지뢰)": (9, 9, 10),
            "중급 (16×16, 40지뢰)": (16, 16, 40),
            "고급 (16×30, 99지뢰)": (16, 30, 99),
        }
        self.current_difficulty = "초급 (9×9, 10지뢰)"
        self.create_menu()
        self.create_controls()
        self.game_frame = tk.Frame(master)
        self.game_frame.pack(padx=5, pady=5)
        self.new_game()

    def create_menu(self):
        menubar = tk.Menu(self.master)
        game_menu = tk.Menu(menubar, tearoff=0)
        game_menu.add_command(label="새 게임 (Restart)", command=self.new_game)
        diff_menu = tk.Menu(game_menu, tearoff=0)
        for label in self.difficulties.keys():
            diff_menu.add_radiobutton(label=label, command=lambda l=label: self.change_difficulty(l))
        game_menu.add_cascade(label="난이도 (Difficulty)", menu=diff_menu)
        game_menu.add_separator()
        game_menu.add_command(label="종료 (Quit)", command=self.master.quit)
        menubar.add_cascade(label="게임 (Game)", menu=game_menu)
        self.master.config(menu=menubar)

    def create_controls(self):
        top_frame = tk.Frame(self.master)
        top_frame.pack(padx=5, pady=3, fill="x")
        self.mines_var = tk.StringVar()
        self.mines_var.set("지뢰: 0")
        self.timer_var = tk.StringVar()
        self.timer_var.set("시간: 0")
        self.status_var = tk.StringVar()
        self.status_var.set("상태: 준비")
        lbl_mines = tk.Label(top_frame, textvariable=self.mines_var, width=12)
        lbl_mines.pack(side="left", padx=4)
        btn_restart = tk.Button(top_frame, text="재시작", command=self.new_game)
        btn_restart.pack(side="left", padx=4)
        lbl_timer = tk.Label(top_frame, textvariable=self.timer_var, width=12)
        lbl_timer.pack(side="left", padx=4)
        lbl_status = tk.Label(top_frame, textvariable=self.status_var, width=20)
        lbl_status.pack(side="left", padx=4)

    def change_difficulty(self, label):
        self.current_difficulty = label
        self.new_game()

    def new_game(self):
        # 초기화
        if hasattr(self, "cells_widgets"):
            # 제거
            for widget in self.game_frame.winfo_children():
                widget.destroy()

        rows, cols, mines = self.difficulties[self.current_difficulty]
        self.rows = rows
        self.cols = cols
        self.total_mines = mines
        self.flags_left = mines
        self.started = False
        self.game_over = False
        self.start_time = None
        self.elapsed = 0
        self.timer_job = None

        # 모델: -1 = 지뢰, 0..8 = 주변 지뢰 수
        self.board = [[0 for _ in range(cols)] for _ in range(rows)]
        self.revealed = [[False]*cols for _ in range(rows)]
        self.flagged = [[False]*cols for _ in range(rows)]
        self.cells_widgets = [[None]*cols for _ in range(rows)]

        self.mines_var.set(f"지뢰: {self.flags_left}")
        self.timer_var.set("시간: 0")
        self.status_var.set("상태: 준비")

        # UI: grid of buttons
        for r in range(rows):
            for c in range(cols):
                btn = tk.Button(self.game_frame, width=2, height=1, relief="raised", font=("Helvetica", 12, "bold"))
                btn.grid(row=r, column=c, padx=0, pady=0)
                # 바인딩: 왼쪽 클릭, 우클릭(Windows Button-3), 더블클릭은 chord 용도로 X
                btn.bind("<Button-1>", lambda e, x=r, y=c: self.on_left_click(x, y))
                btn.bind("<Button-3>", lambda e, x=r, y=c: self.on_right_click(x, y))
                # 윈도우에서 시프트+왼쪽 클릭 등도 채킹을 원하면 추가 가능
                self.cells_widgets[r][c] = btn

        # 배치: 지뢰는 첫 클릭 이후 배치 (첫 클릭 보호)
        # 빈 상태로 둠.

    def place_mines(self, first_r, first_c):
        # 첫 클릭 보호: first_r, first_c와 주변 8칸은 지뢰에서 제외
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        exclude = [(r, c) for r in range(first_r-1, first_r+2) for c in range(first_c-1, first_c+2)
                   if 0 <= r < self.rows and 0 <= c < self.cols]
        for ex in exclude:
            if ex in positions:
                positions.remove(ex)
        random.shuffle(positions)
        mines_to_place = self.total_mines
        for i in range(mines_to_place):
            r, c = positions[i]
            self.board[r][c] = -1
        # 주변 숫자 계산
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == -1:
                    continue
                cnt = 0
                for rr in range(r-1, r+2):
                    for cc in range(c-1, c+2):
                        if 0 <= rr < self.rows and 0 <= cc < self.cols:
                            if self.board[rr][cc] == -1:
                                cnt += 1
                self.board[r][c] = cnt

    def on_left_click(self, r, c):
        if self.game_over:
            return
        if not self.started:
            # 첫 클릭
            self.place_mines(r, c)
            self.started = True
            self.start_time = time.time()
            self.update_timer()
            self.status_var.set("상태: 진행중")
        if self.flagged[r][c] or self.revealed[r][c]:
            return
        if self.board[r][c] == -1:
            # 폭탄 클릭 -> 게임 오버
            self.reveal_mine(r, c)
            self.end_game(False)
            return
        self.reveal_cell(r, c)
        if self.check_win():
            self.end_game(True)

    def on_right_click(self, r, c):
        if self.game_over or not self.started and self.board[r][c] == 0 and not self.revealed[r][c]:
            # 만약 게임 시작 전 우클릭으로 난이도 보호 고려: 우리는 여전히 플래그 허용
            pass
        if self.revealed[r][c]:
            return
        if self.flagged[r][c]:
            # 플래그 제거
            self.flagged[r][c] = False
            self.cells_widgets[r][c].config(text="", fg="black")
            self.flags_left += 1
            self.cells_widgets[r][c].config(relief="raised")
        else:
            if self.flags_left <= 0:
                return
            self.flagged[r][c] = True
            self.cells_widgets[r][c].config(text="⚑", fg="red")
            self.flags_left -= 1
            self.cells_widgets[r][c].config(relief="sunken")
        self.mines_var.set(f"지뢰: {self.flags_left}")

    def reveal_cell(self, r, c):
        if self.revealed[r][c] or self.flagged[r][c]:
            return
        self.revealed[r][c] = True
        btn = self.cells_widgets[r][c]
        btn.config(relief="sunken", state="disabled", bg="#d9d9d9")
        value = self.board[r][c]
        if value > 0:
            color = NUM_COLORS.get(value, "black")
            btn.config(text=str(value), fg=color)
        elif value == 0:
            btn.config(text="", fg="black")
            # 주변 자동 오픈 (flood fill)
            for rr in range(r-1, r+2):
                for cc in range(c-1, c+2):
                    if 0 <= rr < self.rows and 0 <= cc < self.cols:
                        if not self.revealed[rr][cc]:
                            self.reveal_cell(rr, cc)

    def reveal_mine(self, exploded_r, exploded_c):
        # 모든 지뢰 표시
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == -1:
                    btn = self.cells_widgets[r][c]
                    if r == exploded_r and c == exploded_c:
                        btn.config(text="💣", bg="red", fg="black", relief="sunken")
                    else:
                        if not self.flagged[r][c]:
                            btn.config(text="💣", fg="black", relief="sunken")
                        else:
                            btn.config(text="⚑", fg="green", relief="sunken")

    def check_win(self):
        # 승리: 지뢰가 아닌 모든 칸이 공개되었는가
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != -1 and not self.revealed[r][c]:
                    return False
        return True

    def end_game(self, won):
        self.game_over = True
        if self.timer_job:
            self.master.after_cancel(self.timer_job)
            self.timer_job = None
        if won:
            self.status_var.set("상태: 승리! 🎉")
            elapsed = int(time.time() - self.start_time) if self.start_time else 0
            messagebox.showinfo("승리", f"축하합니다! 모든 지뢰를 찾았습니다.\n시간: {elapsed}초")
            # 모든 지뢰에 깃발 추가 (선택)
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.board[r][c] == -1:
                        self.cells_widgets[r][c].config(text="⚑", fg="green", relief="sunken")
        else:
            self.status_var.set("상태: 실패 💥")
            messagebox.showerror("게임 오버", "지뢰를 밟았습니다! 다시 도전하세요.")
        # 비활성화
        for r in range(self.rows):
            for c in range(self.cols):
                try:
                    self.cells_widgets[r][c].config(state="disabled")
                except Exception:
                    pass

    def update_timer(self):
        if not self.started or self.game_over:
            return
        self.elapsed = int(time.time() - self.start_time)
        self.timer_var.set(f"시간: {self.elapsed}")
        # 매초 갱신
        self.timer_job = self.master.after(1000, self.update_timer)


def main():
    root = tk.Tk()
    # 윈도우에서 적절한 크기 조정
    app = Minesweeper(root)
    # 윈도우 중앙 배치 (간단 구현)
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")
    root.resizable(False, False)
    root.mainloop()

if __name__ == "__main__":
    main()
