import sys
import re
import os
import vlc
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QSlider, QLabel, QFileDialog, QCheckBox, QComboBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("美剧学英语播放器")

        # 创建 VLC 播放器实例
        self.instance = vlc.Instance()
        self.mediaplayer = self.instance.media_player_new()

        # 视频显示区域
        self.videoFrame = QWidget(self)
        self.videoFrame.setStyleSheet("background-color: black;")

        # 控制面板控件
        self.btnLoadVideo = QPushButton("加载视频")
        self.btnLoadSubtitle = QPushButton("加载字幕")
        self.btnPlayPause = QPushButton("播放")
        self.sliderPosition = QSlider(Qt.Horizontal)
        self.sliderPosition.setRange(0, 1000)
        self.sliderVolume = QSlider(Qt.Horizontal)
        self.sliderVolume.setRange(0, 100)
        self.sliderVolume.setValue(50)
        self.comboSpeed = QComboBox()
        self.comboSpeed.addItems(["0.5x", "1x", "1.5x", "2x"])
        self.checkLoop = QCheckBox("局部循环")
        self.comboSliceDuration = QComboBox()
        self.comboSliceDuration.addItems(["1分钟", "2分钟", "5分钟"])
        self.checkSliceLoop = QCheckBox("切片循环")
        # 预留字幕相关控件
        self.checkShowSubtitle = QCheckBox("显示字幕")
        self.checkShowSubtitle.setChecked(True)
        self.comboSubtitleLanguage = QComboBox()
        self.comboSubtitleLanguage.addItems(["英文", "中文"])
        self.checkSubtitleAlwaysOnTop = QCheckBox("字幕总在最前")  # 此处仅做界面预留

        # 字幕显示区控件：上一句、当前句、下一句
        self.lblPrevSubtitle = QLabel("")
        self.lblCurrentSubtitle = QLabel("")
        self.lblNextSubtitle = QLabel("")
        self.lblCurrentSubtitle.setFont(QFont("Arial", 16, QFont.Bold))
        self.btnNextSentence = QPushButton("下一句")
        self.btnNextSlice = QPushButton("下一个切片")

        # 布局设置
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.videoFrame)

        # 控制面板布局
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(self.btnLoadVideo)
        controlLayout.addWidget(self.btnLoadSubtitle)
        controlLayout.addWidget(self.btnPlayPause)
        controlLayout.addWidget(QLabel("进度:"))
        controlLayout.addWidget(self.sliderPosition)
        controlLayout.addWidget(QLabel("音量:"))
        controlLayout.addWidget(self.sliderVolume)
        controlLayout.addWidget(QLabel("倍速:"))
        controlLayout.addWidget(self.comboSpeed)
        controlLayout.addWidget(self.checkLoop)
        controlLayout.addWidget(QLabel("切片时长:"))
        controlLayout.addWidget(self.comboSliceDuration)
        controlLayout.addWidget(self.checkSliceLoop)
        controlLayout.addWidget(self.checkShowSubtitle)
        controlLayout.addWidget(QLabel("字幕语言:"))
        controlLayout.addWidget(self.comboSubtitleLanguage)
        controlLayout.addWidget(self.checkSubtitleAlwaysOnTop)
        mainLayout.addLayout(controlLayout)

        # 字幕显示区域布局
        subtitleLayout = QVBoxLayout()
        subtitleLayout.addWidget(self.lblPrevSubtitle)
        subtitleLayout.addWidget(self.lblCurrentSubtitle)
        subtitleLayout.addWidget(self.lblNextSubtitle)
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.btnNextSentence)
        btnLayout.addWidget(self.btnNextSlice)
        subtitleLayout.addLayout(btnLayout)
        mainLayout.addLayout(subtitleLayout)

        centralWidget = QWidget(self)
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        # 定时器用于更新进度和字幕
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()

        # 信号与槽的连接
        self.btnLoadVideo.clicked.connect(self.load_video)
        self.btnLoadSubtitle.clicked.connect(self.load_subtitle)
        self.btnPlayPause.clicked.connect(self.play_pause)
        self.sliderPosition.sliderMoved.connect(self.set_position)
        self.sliderVolume.valueChanged.connect(self.set_volume)
        self.comboSpeed.currentIndexChanged.connect(self.change_speed)
        self.btnNextSentence.clicked.connect(self.next_sentence)
        self.btnNextSlice.clicked.connect(self.next_slice)

        # 字幕数据（存放解析后的字幕字典，每项包含 start, end, text）
        self.subtitles = []
        self.currentSubtitleIndex = -1

        # 根据操作系统设置 VLC 视频输出窗口
        if sys.platform.startswith('linux'):
            self.mediaplayer.set_xwindow(self.videoFrame.winId())
        elif sys.platform == "win32":
            self.mediaplayer.set_hwnd(self.videoFrame.winId())
        elif sys.platform == "darwin":
            self.mediaplayer.set_nsobject(int(self.videoFrame.winId()))

    def load_video(self):
        video_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", ".", "Video Files (*.mp4 *.avi *.mkv)")
        if video_path:
            media = self.instance.media_new(video_path)
            self.mediaplayer.set_media(media)
            self.mediaplayer.play()

    def load_subtitle(self):
        subtitle_path, _ = QFileDialog.getOpenFileName(self, "选择字幕文件", ".", "Subtitle Files (*.srt)")
        if subtitle_path:
            self.subtitles = self.parse_srt(subtitle_path)

    def parse_srt(self, path):
        """解析 SRT 字幕文件，返回字幕列表，每项为字典 {start, end, text}，单位均为毫秒"""
        subtitles = []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        entries = re.split(r'\n\s*\n', content.strip())
        for entry in entries:
            lines = entry.splitlines()
            if len(lines) >= 3:
                time_line = lines[1]
                times = time_line.split(" --> ")
                if len(times) == 2:
                    start = self.time_to_millis(times[0].strip())
                    end = self.time_to_millis(times[1].strip())
                    text = "\n".join(lines[2:])
                    subtitles.append({"start": start, "end": end, "text": text})
        subtitles.sort(key=lambda x: x["start"])
        return subtitles

    def time_to_millis(self, time_str):
        """将 'hh:mm:ss,ms' 格式的时间转换为毫秒"""
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds, millis = parts[2].split(",")
        seconds = int(seconds)
        millis = int(millis)
        total = (hours * 3600 + minutes * 60 + seconds) * 1000 + millis
        return total

    def play_pause(self):
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.btnPlayPause.setText("播放")
        else:
            self.mediaplayer.play()
            self.btnPlayPause.setText("暂停")

    def set_position(self, position):
        # slider 数值范围 0~1000，转换为百分比
        self.mediaplayer.set_position(position / 1000.0)

    def set_volume(self, volume):
        self.mediaplayer.audio_set_volume(volume)

    def change_speed(self, index):
        speeds = [0.5, 1.0, 1.5, 2.0]
        self.mediaplayer.set_rate(speeds[index])

    def update_ui(self):
        # 更新进度条
        if self.mediaplayer.get_length() > 0:
            pos = self.mediaplayer.get_position() * 1000
            self.sliderPosition.setValue(int(pos))
        # 更新字幕显示（若开启显示字幕）
        if self.checkShowSubtitle.isChecked():
            self.update_subtitles()
        else:
            self.lblPrevSubtitle.setText("")
            self.lblCurrentSubtitle.setText("")
            self.lblNextSubtitle.setText("")
        # 检查局部循环功能
        if self.checkLoop.isChecked():
            self.loop_current_sentence()
        # 检查切片循环功能
        if self.checkSliceLoop.isChecked():
            self.loop_current_slice()

    def update_subtitles(self):
        if not self.subtitles:
            self.lblPrevSubtitle.setText("")
            self.lblCurrentSubtitle.setText("")
            self.lblNextSubtitle.setText("")
            return
        current_time = self.mediaplayer.get_time()  # 毫秒单位
        index = -1
        for i, sub in enumerate(self.subtitles):
            if sub["start"] <= current_time <= sub["end"]:
                index = i
                break
        self.currentSubtitleIndex = index
        if index == -1:
            self.lblPrevSubtitle.setText("")
            self.lblCurrentSubtitle.setText("")
            self.lblNextSubtitle.setText("")
        else:
            prev_text = self.subtitles[index-1]["text"] if index > 0 else ""
            current_text = self.subtitles[index]["text"]
            next_text = self.subtitles[index+1]["text"] if index < len(self.subtitles)-1 else ""
            # 若选择中文模式，这里可加入翻译处理，目前简单加个前缀标记
            if self.comboSubtitleLanguage.currentText() == "中文":
                current_text = "[中]" + current_text
                prev_text = "[中]" + prev_text if prev_text else ""
                next_text = "[中]" + next_text if next_text else ""
            self.lblPrevSubtitle.setText(prev_text)
            self.lblCurrentSubtitle.setText(current_text)
            self.lblNextSubtitle.setText(next_text)

    def loop_current_sentence(self):
        # 对当前字幕句子进行局部循环播放
        if self.currentSubtitleIndex != -1:
            current_time = self.mediaplayer.get_time()
            sub = self.subtitles[self.currentSubtitleIndex]
            if current_time > sub["end"]:
                self.mediaplayer.set_time(sub["start"])

    def loop_current_slice(self):
        # 按切片时长循环播放，切片时长由 comboSliceDuration 确定
        duration_text = self.comboSliceDuration.currentText()
        try:
            minutes = int(re.findall(r'\d+', duration_text)[0])
        except:
            minutes = 1
        slice_duration = minutes * 60 * 1000
        current_time = self.mediaplayer.get_time()
        current_slice_start = (current_time // slice_duration) * slice_duration
        current_slice_end = current_slice_start + slice_duration
        if current_time > current_slice_end:
            self.mediaplayer.set_time(current_slice_start)

    def next_sentence(self):
        # 跳转到下一句字幕的起始时间
        if self.currentSubtitleIndex != -1 and self.currentSubtitleIndex < len(self.subtitles) - 1:
            next_sub = self.subtitles[self.currentSubtitleIndex + 1]
            self.mediaplayer.set_time(next_sub["start"])

    def next_slice(self):
        # 跳转到下一个切片起始点
        duration_text = self.comboSliceDuration.currentText()
        try:
            minutes = int(re.findall(r'\d+', duration_text)[0])
        except:
            minutes = 1
        slice_duration = minutes * 60 * 1000
        current_time = self.mediaplayer.get_time()
        current_slice = current_time // slice_duration
        next_slice_start = (current_slice + 1) * slice_duration
        self.mediaplayer.set_time(next_slice_start)

    def closeEvent(self, event):
        self.mediaplayer.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = MainWindow()
    player.resize(800, 600)
    player.show()
    sys.exit(app.exec_())
