import cv2

class VideoSource:
    def __init__(self, source):
        self.source = int(source) if str(source).isdigit() else source
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.source)
        return bool(self.cap and self.cap.isOpened())

    def read(self):
        if not self.cap:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    @property
    def fps(self):
        if not self.cap:
            return 0
        value = self.cap.get(cv2.CAP_PROP_FPS)
        return value if value and value > 0 else 25
