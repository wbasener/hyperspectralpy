from PyQt5 import QtCore, QtGui, QtWidgets

class GraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        scene = QtWidgets.QGraphicsScene(self)
        self.setScene(scene)
        self._pixmap_item = QtWidgets.QGraphicsPixmapItem()
        scene.addItem(self.pixmap_item)
        self._polygon_item = QtWidgets.QGraphicsPolygonItem(self.pixmap_item)
        self.polygon_item.setPen(QtGui.QPen(QtCore.Qt.black, 5, QtCore.Qt.SolidLine))
        self.polygon_item.setBrush(QtGui.QBrush(QtCore.Qt.red, QtCore.Qt.VerPattern))

    @property
    def pixmap_item(self):
        return self._pixmap_item

    @property
    def polygon_item(self):
        return self._polygon_item

    def setPixmap(self, pixmap):
        self.pixmap_item.setPixmap(pixmap)

    def resizeEvent(self, event):
        self.fitInView(self.pixmap_item, QtCore.Qt.KeepAspectRatio)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        sp = self.mapToScene(event.pos())
        lp = self.pixmap_item.mapFromScene(sp)

        poly = self.polygon_item.polygon()
        poly.append(lp)
        self.polygon_item.setPolygon(poly)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        view = GraphicsView()
        self.setCentralWidget(view)
        view.setPixmap(QtGui.QPixmap("img.png"))
        self.resize(640, 480)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())