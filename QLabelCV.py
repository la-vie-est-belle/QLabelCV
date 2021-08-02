import sys
import cv2 as cv
import numpy as np
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QPixmap
from PyQt5.QtCore import QThread, Qt, pyqtSignal, PYQT_VERSION_STR
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QWidget, QSpinBox, QDoubleSpinBox, QHBoxLayout


class QLabelCV(QLabel):
    def __init__(self):
        super(QLabelCV, self).__init__()
        self.resize(640, 360)

        self._pen = None
        self._frame = []
        self._camera = None
        self._is_camera_ok = True
        self._image_format = None
        self._send_frame_thread = None

        self._roi_top_left_x = 0
        self._roi_top_left_y = 0
        self._roi_bottom_right_x = 0
        self._roi_bottom_right_y = 0

        self._adjust_area = None
        self._show_hide_adjust_area_btn = None
        self._brightness_spin = None
        self._contrast_spin = None
        self._sharpen_spin = None
        self._blur_spin = None

        self._main()

    def _main(self):
        self._init_image_format()
        self._init_thread()
        self._init_pen_style()
        self._init_adjust_area()

    def _init_image_format(self):
        # QImage.Format_BGR888 is added in 5.14
        # Will use QImage.Format_RGB888 if PyQt5 is lower than 5.14
        if PYQT_VERSION_STR < '5.14':
            self._image_format = QImage.Format_RGB888
            print('Attention: your PyQt Version is lower than 5.14, so frames are converted \n'
                  'from BGR to RGB to work with QImage.Format_RGB888. OpenCV Color format is now RGB not BGR!!!')
        else:
            self._image_format = QImage.Format_BGR888

    def _init_thread(self):
        self._send_frame_thread = SendFrameThread(self)
        self._send_frame_thread.frame_signal.connect(self._get_frame_from_thread)

    def _init_pen_style(self):
        self._pen = QPen()
        self.set_pen(2, Qt.green)

    def _init_adjust_area(self):
        self._show_hide_adjust_area_btn = QPushButton('⬇', self)
        self._show_hide_adjust_area_btn.move(self.width()/2, 5)
        self._show_hide_adjust_area_btn.setStyleSheet('QPushButton{border:none}')
        self._show_hide_adjust_area_btn.clicked.connect(self._show_hide_adjust_area)

        self._adjust_area = QWidget(self)
        self._adjust_area.resize(self.width(), 50)
        self._adjust_area.move(0, 0)
        self._adjust_area.hide()

        self._contrast_spin = QDoubleSpinBox(self._adjust_area)
        self._brightness_spin = QSpinBox(self._adjust_area)
        self._sharpen_spin = QSpinBox(self._adjust_area)
        self._blur_spin = QSpinBox(self._adjust_area)

        self._brightness_spin.setMaximum(255)
        self._brightness_spin.setMinimum(-255)
        self._contrast_spin.setSingleStep(0.1)
        self._contrast_spin.setValue(1)
        self._blur_spin.setSingleStep(2)
        self._blur_spin.setMinimum(1)
        self._blur_spin.setValue(1)

        _h_layout = QHBoxLayout()
        _h_layout.addStretch(1)
        _h_layout.addWidget(QLabel('Contrast'))
        _h_layout.addWidget(self._contrast_spin)
        _h_layout.addStretch(1)
        _h_layout.addWidget(QLabel('Brightness'))
        _h_layout.addWidget(self._brightness_spin)
        _h_layout.addStretch(1)
        _h_layout.addWidget(QLabel('Sharpen'))
        _h_layout.addWidget(self._sharpen_spin)
        _h_layout.addStretch(1)
        _h_layout.addWidget(QLabel('Blur'))
        _h_layout.addWidget(self._blur_spin)
        _h_layout.addStretch(1)
        self._adjust_area.setLayout(_h_layout)

    def _show_hide_adjust_area(self):
        if self._show_hide_adjust_area_btn.text() == '⬇':
            self._adjust_area.show()
            self._show_hide_adjust_area_btn.setText('⬆')
            self._show_hide_adjust_area_btn.move(self.width()/2, 40)
        else:
            self._adjust_area.hide()
            self._show_hide_adjust_area_btn.setText('⬇')
            self._show_hide_adjust_area_btn.move(self.width()/2, 5)

    @property
    def camera(self):
        return self._camera

    @property
    def image_format(self):
        return self._image_format

    @property
    def sharpen_value(self):
        return self._sharpen_spin.value()

    @property
    def contrast_value(self):
        return self._contrast_spin.value()

    @property
    def brightness_value(self):
        return self._brightness_spin.value()

    @property
    def blur_value(self):
        return self._blur_spin.value()

    @property
    def roi_top_left_x(self):
        return self._roi_top_left_x

    @property
    def roi_top_left_y(self):
        return self._roi_top_left_y

    @property
    def roi_bottom_right_x(self):
        return self._roi_bottom_right_x

    @property
    def roi_bottom_right_y(self):
        return self._roi_bottom_right_y

    @roi_top_left_x.setter
    def roi_top_left_x(self, value: float):
        self.roi_top_left_x = value

    @roi_top_left_y.setter
    def roi_top_left_y(self, value: float):
        self.roi_top_left_y = value

    @roi_bottom_right_x.setter
    def roi_bottom_right_x(self, value: float):
        self.roi_bottom_right_x = value

    @roi_bottom_right_y.setter
    def roi_bottom_right_y(self, value: float):
        self.roi_bottom_right_y = value

    def get_roi_top_left_x(self):
        return self._roi_top_left_x

    def get_roi_top_left_y(self):
        return self._roi_top_left_y

    def get_roi_bottom_right_x(self):
        return self._roi_bottom_right_x

    def get_roi_bottom_right_y(self):
        return self._roi_bottom_right_y

    def set_roi_top_left_x(self, value: float):
        self._roi_top_left_x = value

    def set_roi_top_left_y(self, value: float):
        self._roi_top_left_y = value

    def set_roi_bottom_right_x(self, value: float):
        self._roi_bottom_right_x = value

    def set_roi_bottom_right_y(self, value: float):
        self._roi_bottom_right_y = value

    def get_rect(self):
        return self._roi_top_left_x, self._roi_top_left_y, self._roi_bottom_right_x, self._roi_bottom_right_y

    @property
    def frame(self):
        return self._frame

    def save_frame(self, path, with_roi_rect=False):
        """
        save frame as a local picture file
        :param path: file path
        :param with_roi_rect: if to draw roi on the saved picture
        :return: None
        """
        if not self._is_camera_ok:
            print('no frame')
            return

        self._frame = np.array(self._frame)
        if self._frame.any():
            if not with_roi_rect:
                cv.imwrite(path, self._frame)
            else:
                cv.rectangle(self._frame,
                             (self._roi_top_left_x, self._roi_top_left_y),
                             (self._roi_bottom_right_x, self._roi_bottom_right_y),
                             (self._pen.color().red(), self._pen.color().green(), self._pen.color().blue()),
                             self._pen.width())
                cv.imwrite(path, self._frame)

    def get_frame(self):
        return self._frame

    def set_camera(self, device_index: int):
        self._camera = cv.VideoCapture(device_index)
        self._check_camera()

    def _check_camera(self):
        """check if the camera is available"""
        if self._camera.isOpened():
            self._is_camera_ok = True
            self._send_frame_thread.stop()
            self._send_frame_thread.start()
        else:
            self._send_frame_thread.stop()
            self._is_camera_ok = False

    def set_pen(self, width: int, color: QColor):
        self._pen.setWidth(width)
        self._pen.setColor(color)

    def _get_frame_from_thread(self, frame: list, width: int, height: int):
        self._frame = np.array(frame)
        _frame_bytes = self._frame.tobytes()
        _image = QImage(_frame_bytes, width, height, self._image_format)
        _pixmap = QPixmap.fromImage(_image)
        self.setPixmap(_pixmap)

    def resizeEvent(self, event):
        self._adjust_area.resize(self.width(), 50)
        if self._show_hide_adjust_area_btn.text() == '⬇':
            self._show_hide_adjust_area_btn.move(self.width()/2, 5)
        else:
            self._show_hide_adjust_area_btn.move(self.width()/2, 40)

    def mousePressEvent(self, event):
        if not self._is_camera_ok:
            return

        if event.buttons() == Qt.LeftButton:
            self._roi_top_left_x = event.pos().x()
            self._roi_top_left_y = event.pos().y()

    def mouseMoveEvent(self, event):
        if not self._is_camera_ok:
            return

        if event.buttons() == Qt.LeftButton:
            self._roi_bottom_right_x = event.pos().x()
            self._roi_bottom_right_y = event.pos().y()

    def paintEvent(self, event):
        super(QLabelCV, self).paintEvent(event)

        _painter = QPainter(self)
        _painter.setPen(self._pen)

        if not self._is_camera_ok:
            _painter.drawText(10, 20, 'Device Not Available')
        else:
            _painter.drawText(self._roi_top_left_x, self._roi_top_left_y, 'ROI')
            _painter.drawRect(self._roi_top_left_x,
                              self._roi_top_left_y,
                              self._roi_bottom_right_x-self._roi_top_left_x,
                              self._roi_bottom_right_y-self._roi_top_left_y)

    def closeEvent(self, event):
        self._send_frame_thread.stop()


class SendFrameThread(QThread):
    frame_signal = pyqtSignal(list, int, int)

    def __init__(self, parent):
        super(SendFrameThread, self).__init__()
        self._parent = parent
        self._flag = True

    def run(self):
        self._flag = True
        while self._flag:
            self._send_video_frame()

            # prevent crushing
            self.usleep(1000)

    def stop(self):
        self._flag = False

    def _send_video_frame(self):
        _ret, _frame = self._parent.camera.read()
        if self._parent.image_format == QImage.Format_RGB888:
            _frame = cv.cvtColor(_frame, cv.COLOR_BGR2RGB)

        if not _ret:
            return

        _frame = cv.resize(_frame, (self._parent.width(), self._parent.height()))
        _frame = self._optimize_frame(_frame)
        _frame_width, _frame_height = _frame.shape[1], _frame.shape[0]
        self.frame_signal.emit(list(_frame), _frame_width, _frame_height)

    def _optimize_frame(self, frame):
        _optimized_frame = self._sharpen(frame)
        _optimized_frame = self._blur(_optimized_frame)
        _optimized_frame = self._set_contrast_brightness(_optimized_frame)
        return _optimized_frame

    def _sharpen(self, frame):
        _sharpen_value = self._parent.sharpen_value
        _sharpen_value += 4

        if _sharpen_value > 4:
            _kernel = np.array([[0, -1, 0], [-1, _sharpen_value, -1], [0, -1, 0]], np.float32)
            frame = cv.filter2D(frame, -1, kernel=_kernel)

        return frame

    def _blur(self, frame):
        _blur_value = self._parent.blur_value

        if _blur_value:
            frame = cv.GaussianBlur(frame, (_blur_value, _blur_value), 0)

        return frame

    def _set_contrast_brightness(self, frame):
        _contrast_value = self._parent.contrast_value
        _blank = np.zeros(frame.shape, frame.dtype)
        frame = cv.addWeighted(frame, _contrast_value, _blank, 1-_contrast_value, self._parent.brightness_value)
        return frame


if __name__ == '__main__':
    app = QApplication(sys.argv)
    label = QLabelCV()
    label.show()
    label.set_camera(0)
    sys.exit(app.exec_())

