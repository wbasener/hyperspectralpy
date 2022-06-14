from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt4agg import FigureManagerQT
import numpy as np


class MyFigureCanvas(FigureCanvasQTAgg):
    def __init__(self):
        super(MyFigureCanvas, self).__init__(Figure())
        # init class attributes:
        self.background = None
        self.draggable = None
        self.msize = 6
        # plot some data:
        x = np.random.rand(25)
        self.ax = self.figure.add_subplot(111)
        self.markers, = self.ax.plot(x, marker='o', ms=self.msize)
        # define event connections:
        self.mpl_connect('motion_notify_event', self.on_motion)
        self.mpl_connect('button_press_event', self.on_click)
        self.mpl_connect('button_release_event', self.on_release)

    def on_click(self, event):
        if event.button == 2:  # 2 is for middle mouse button
            # get mouse cursor coordinates in pixels:
            x = event.x
            y = event.y
            # get markers xy coordinate in pixels:
            xydata = self.ax.transData.transform(self.markers.get_xydata())
            xdata, ydata = xydata.T
            # compute the linear distance between the markers and the cursor:
            r = ((xdata - x)**2 + (ydata - y)**2)**0.5
            if np.min(r) < self.msize:
                # save figure background:
                self.markers.set_visible(False)
                self.draw()
                self.background = self.copy_from_bbox(self.ax.bbox)
                self.markers.set_visible(True)
                self.ax.draw_artist(self.markers)
                self.update()
                # store index of draggable marker:
                self.draggable = np.argmin(r)
            else:
                self.draggable = None

    def on_motion(self, event):
        if self.draggable is not None:
            if event.xdata and event.ydata:
                # get markers coordinate in data units:
                xdata, ydata = self.markers.get_data()
                # change the coordinate of the marker that is
                # being dragged to the ones of the mouse cursor:
                xdata[self.draggable] = event.xdata
                ydata[self.draggable] = event.ydata
                # update the data of the artist:
                self.markers.set_xdata(xdata)
                self.markers.set_ydata(ydata)
                # update the plot:
                self.restore_region(self.background)
                self.ax.draw_artist(self.markers)
                self.update()

    def on_release(self, event):
        self.draggable = None

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)

    canvas = MyFigureCanvas()
    manager = FigureManagerQT(canvas, 1)
    manager.show()

    sys.exit(app.exec_())