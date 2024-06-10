"""ECG via 3.5mm Jack GUI is monitoring a Live ECG signal with the the help of just
one Opamp i.e. LM324 and few resistors. The Idea was to make a low cost ECG device
under few bucks. If you haven't built any ckt yet just load a wav file, I have added
that functionalities too. Other wise build a circuit and use a biopatch for electrode.
"""

from PyQt5 import QtGui,QtCore,QtWidgets
import sys
import GUI
import numpy as np
import pyqtgraph
import Plottingfunctions
import time
import pyqtgraph.exporters

class ExampleApp(QtWidgets.QMainWindow, GUI.Ui_MainWindow):
    def __init__(self, parent=None):
        pyqtgraph.setConfigOption('background', 'w') #This loads before the widget loads
        super(ExampleApp, self).__init__(parent)
        self.setupUi(self)
        self.grECG.plotItem.showGrid(True, True, 0.7)
        self.btnSave.clicked.connect(self.saveFig)
        self.btnSite.clicked.connect(self.website)
        stamp="ECG by Vaibhav Rachalwar"
        self.stamp = pyqtgraph.TextItem(stamp,anchor=(-.01,1),color=(150,150,150),
                                        fill=pyqtgraph.mkBrush('w'))
        self.Record = Plottingfunctions.Record(chunk=int(100)) # Constantly determines
                                                        # the rate and refreshes it
        if len(self.Record.check_inputdevices()):
            self.Record.stream_starting()
            self.lblDevice.setText(self.Record.msg)
            self.update()

    def closeEvent(self, event):
        self.Record.shut()
        event.accept()

    def saveFig(self):
        fname="ECG_%d.png"%time.time()
        exp = pyqtgraph.exporters.ImageExporter(self.grECG.plotItem)
        exp.parameters()['width'] = 1000
        exp.export(fname)
        print("saved",fname)

    def update(self):
        t1,timeTook=time.time(),0
        if len(self.Record.data) and not self.btnPause.isChecked():
            freqHighCutoff=0
            if self.spinBox.value()>0:
                freqHighCutoff=self.spinBox.value()
            data=self.Record.Filtering_out(freqHighCutoff)
            if self.checkBox.isChecked():
                data=np.negative(data)
            if self.checkBox_2.isChecked():
                self.Yscale=np.max(np.abs(data))*1.1
            self.grECG.plotItem.setRange(xRange=[0,self.Record.maxMemorySec],
                            yRange=[-self.Yscale,self.Yscale],padding=0)
            self.grECG.plot(np.arange(len(data))/float(self.Record.rate),data,clear=True,
                            pen=pyqtgraph.mkPen(color='r'),antialias=True)
            self.stamp.setPos(0,-self.Yscale)
            self.grECG.plotItem.addItem(self.stamp)
            timeTook=(time.time()-t1)*1000
            print("plotting took %.02f ms"%(timeTook))
        msTillUpdate=int(self.Record.chunk/self.Record.rate*1000)-timeTook
        QtCore.QTimer.singleShot(max(0,msTillUpdate), self.update)

    def website(self):
        webbrowser.open("--")

if __name__=="__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = ExampleApp()
    form.show()
    app.exec_()
