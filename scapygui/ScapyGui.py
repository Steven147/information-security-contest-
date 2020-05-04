import sys
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from packetcatch import packetsniff
from scapy.all import *

class Main(QMainWindow):
    def __init__(self):
        super(Main,self).__init__()
        uic.loadUi('main.ui',self)                                          #读取.ui文件（于QtDesigner设计）
        self.setWindowTitle("Something like Scapy")
        self.setFixedSize(800,800)
        #Behavior
        self.summary.setSelectionBehavior(QAbstractItemView.SelectRows)     #点击表格时选择整行
        self.analysis.setHeaderHidden(True)                                 #TreeWidget列头隐藏
        self.summary.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        #signal
        self.summary.cellClicked.connect(self.moreInfo)                     #点击单行表格显示该数据的详细信息
        self.actionOnlineSniff.triggered.connect(self.onlineSniff)          #暂定，menuBar下启动在线抓包
        self.actionOpen.triggered.connect(self.offlineSniff)                #menuBat下选择指定pcap文件读取分析
        self.actionSave.triggered.connect(self.save)
        #Layout setting
        self.layout = QGridLayout()                                         #排版信息
        self.layout.addWidget(self.summary,0,0)
        self.layout.addWidget(self.analysis,1,0)
        #initialize
        self.packet = []
        
    def onlineSniff(self):
        self.packet = []
        self.summary.setRowCount(0)
        #thread settings
        self.threadpool = QThreadPool()                                     #线程池
        thread = packetsniff()
        thread.signals.doneSignal.connect(self.updateOnline)                #捕捉到一条流量的反馈
        self.sniffStop.clicked.connect(thread.stop)                         #暂定，在线捕抓停止按钮
        self.threadpool.start(thread)

    def offlineSniff(self):
        dialog = QFileDialog()
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        while True:
            url = dialog.getOpenFileName()
            if (url[0][-4:] == 'pcap' ):                
                self.summary.setRowCount(0)
                self.packet = sniff(offline = url[0])
                self.updateOffline()
                break
            elif len(url[0]) == 0:                                           #Cancel Button Selected
                break
            else:
                QMessageBox.information(self,"File Extension Error","Only Accept .pcap file")
        
    def updateOnline(self,packet):                                          #在线捕捉的流量显示（单条）
        self.tableUpdate(packet)
        self.summary.resizeColumnsToContents()
        self.packet.append(packet)

    def updateOffline(self):                                         #离线捕捉的流量显示（多条）
        for i in self.packet:
            self.tableUpdate(i)
        self.summary.resizeColumnsToContents()

    def tableUpdate(self,packet):
        rowposition = self.summary.rowCount()
        self.summary.insertRow(rowposition)
        self.summary.setItem(rowposition,3,QTableWidgetItem(str(len(packet))))
        if ARP in packet:
            self.summary.setItem(rowposition,0,QTableWidgetItem(packet[ARP].hwsrc))
            self.summary.setItem(rowposition,1,QTableWidgetItem('ARP'))
            self.summary.setItem(rowposition,2,QTableWidgetItem(packet[ARP].hwdst))
            if (packet[ARP].op == 1): info = "Who has" + packet[ARP].psrc + "? Tell" + packet[ARP].pdst
            elif (packet[ARP].op == 2): info = packet[ARP].pdst + "is at " + packet[ARP].hwsrc
            elif (packet[ARP].op == 3): pass
            elif (packet[ARP].op == 4): pass
            self.summary.setItem(rowposition,4,QTableWidgetItem(info))

        elif IP in packet:
            self.summary.setItem(rowposition,0,QTableWidgetItem(packet[IP].src))
            if (packet[IP].proto == 1): 
                self.summary.setItem(rowposition,1,QTableWidgetItem('ICMP'))
            elif (packet[IP].proto == 6): 
                self.summary.setItem(rowposition,1,QTableWidgetItem('TCP'))
                temp = ""
                for k in packet[TCP].flags:
                    if k == 'C': temp += 'CWR,'
                    if k == 'E': temp += 'ECE,'
                    if k == 'U': temp += 'URG,'
                    if k == 'A': temp += 'ACK,'
                    if k == 'P': temp += 'PSH,'
                    if k == 'R': temp += 'RST,'
                    if k == 'S': temp += 'SYN,'
                    if k == 'F': temp += 'FIN,'
                info = str(packet[TCP].sport) + '->' + str(packet[TCP].dport) + '[' + temp[:-1] + ']'
                self.summary.setItem(rowposition,4,QTableWidgetItem(info))
            elif (packet[IP].proto == 17): 
                self.summary.setItem(rowposition,1,QTableWidgetItem('UDP'))
                info = str(packet[UDP].sport) + '->' + str(packet[UDP].dport)
                self.summary.setItem(rowposition,4,QTableWidgetItem(info))
            self.summary.setItem(rowposition,2,QTableWidgetItem(packet[IP].dst))

    def moreInfo(self,line,col):                                            #暂定，流量详细信息
        packet = self.packet[line]
        self.analysis.clear()
        eth = QTreeWidgetItem(['Ethernel II'])                              #数据链路层
        eth.addChild(QTreeWidgetItem(["Source: " + packet[Ether].src]))
        eth.addChild(QTreeWidgetItem(["Destination: " + packet[Ether].dst]))
        eth.addChild(QTreeWidgetItem(["Type: " + str(packet[Ether].type)]))
        self.analysis.addTopLevelItem(eth)
        #流量检测只检测TCP,UDP的包，非以上两者的包是否要在则例分析与解释?
        if IP in packet:
            ip = QTreeWidgetItem(["IP version 4"])                           #IP层
            ip.addChild(QTreeWidgetItem(["Source:"+packet[IP].src]))
            ip.addChild(QTreeWidgetItem(["Destination:"+packet[IP].dst]))
            ip.addChild(QTreeWidgetItem(["HeaderLength:"+str(packet[IP].ihl*4)]))
            ip.addChild(QTreeWidgetItem(["Type Of Service:"+str(packet[IP].tos)]))
            ip.addChild(QTreeWidgetItem(["Identification:"+str(packet[IP].id)]))
            self.analysis.addTopLevelItem(ip)
        elif ARP in packet:
            ip = QTreeWidgetItem(['Address Resolution Protocol'])           #ARP层
            ip.addChild(QTreeWidgetItem(["Hardware type:"+str(packet[ARP].hwtype)]))
            ip.addChild(QTreeWidgetItem(["Protocol Type:"+str(packet[ARP].ptype)]))
            ip.addChild(QTreeWidgetItem(["Hardware Size:"+str(packet[ARP].hwlen)]))
            ip.addChild(QTreeWidgetItem(["Protocol Size:"+str(packet[ARP].plen)]))
            ip.addChild(QTreeWidgetItem(["Opcode:"+str(packet[ARP].op)]))
            ip.addChild(QTreeWidgetItem(["Sender MAC address:"+str(packet[ARP].hwsrc)]))
            ip.addChild(QTreeWidgetItem(["Sender IP address:"+str(packet[ARP].psrc)]))
            ip.addChild(QTreeWidgetItem(["Target MAC address:"+str(packet[ARP].hwdst)]))
            ip.addChild(QTreeWidgetItem(["Target IP address:"+str(packet[ARP].pdst)]))
            self.analysis.addTopLevelItem(ip)
        elif IPv6 in packet:
            ip = QTreeWidgetItem("[Ip version 6]")
            self.analysis.addTopLevelItem(ip)

        if TCP in packet:
            tp = QTreeWidgetItem(["Transport Control Protocol"])           #TCP层
            tp.addChild(QTreeWidgetItem(['Source Port' + str(packet[TCP].sport)]))
            tp.addChild(QTreeWidgetItem(['Destination Port' + str(packet[TCP].dport)]))
            tp.addChild(QTreeWidgetItem(['Sequence Number' + str(packet[TCP].seq)]))
            tp.addChild(QTreeWidgetItem(['Acknowledgment Number' + str(packet[TCP].ack)]))
            tp.addChild(QTreeWidgetItem(['Header Length' + str(packet[TCP].dataofs)]))
            tp.addChild(QTreeWidgetItem(['Flags' + str(packet[TCP].flags)]))
            #more flag information ..?
            tp.addChild(QTreeWidgetItem(['Windows Size' + str(packet[TCP].window)]))
            tp.addChild(QTreeWidgetItem(['Checksum' + str(packet[TCP].chksum)]))
            tp.addChild(QTreeWidgetItem(['Urgent Pointer' + str(packet[TCP].urgptr)]))
            self.analysis.addTopLevelItem(tp)
        elif UDP in packet:
            tp = QTreeWidgetItem(['User Datagram Protocol'])
            tp.addChild(QTreeWidgetItem(['Source Port' + str(packet[UDP].sport)]))
            tp.addChild(QTreeWidgetItem(['Destination Port' + str(packet[UDP].dport)]))
            tp.addChild(QTreeWidgetItem(['Length' + str(packet[UDP].len)]))
            tp.addChild(QTreeWidgetItem(['Checksum' + str(packet[UDP].chksum)]))
            self.analysis.addTopLevelItem(tp)
        elif ICMP in packet:
            tp = QTreeWidgeItem(['Internet Control Message Protocol'])
            self.analysis.addTopLevelItem(tp)

    def save(self):
        dialog = QFileDialog()
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        fileName = dialog.getSaveFileName()
        if (fileName != None) and (len(self.packet) != 0):
            _ = wrpcap(fileName[0],self.packet)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())
