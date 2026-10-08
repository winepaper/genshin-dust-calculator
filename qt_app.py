from __future__ import annotations

import argparse
from dataclasses import replace
import html
import json
import math
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QTabBar, QTableWidget, QTableWidgetItem, QTextBrowser, QToolButton,
    QToolTip, QVBoxLayout, QWidget,
)
import engine as E
from common import INPUT_GUIDE, RULE_TEXT, fmt, inference_text, parse_substat_text, pc, save_report, score_details


LIGHT = dict(bg="#F5F2EC", panel="#FFFFFF", field="#F7F5F1", text="#28333F", muted="#87909A",
             line="#E8E3DB", gold="#AF7D31", gold_hover="#996A28", tint="#FAF1E2", chart="#8296A1",
             green="#638874", red="#B15B58", soft_red="#FFF0ED", grid="#ECEAE6")
DARK = dict(bg="#141C28", panel="#1E2939", field="#253246", text="#ECEDF0", muted="#96A3B6",
            line="#334258", gold="#D7B36F", gold_hover="#E5C385", tint="#393429", chart="#8FAABD",
            green="#9ABDAB", red="#EDABA0", soft_red="#3D2D32", grid="#344154")
FONT = "Microsoft YaHei UI"
TIERS = ("自动", "1档 · 70%", "2档 · 80%", "3档 · 90%", "4档 · 100%")
MAIN_STATS = {"自动 / 不校验": "", **{v[0]: k for k,v in E.STAT_DATA.items()},
              "元素伤害加成": "element", "物理伤害加成": "physical", "治疗加成": "healing"}


def resource(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / name


def text_label(text="", role=None, wrap=False):
    obj = QLabel(text)
    if role:
        obj.setProperty("role", role)
    obj.setWordWrap(wrap)
    return obj


def hbox(spacing=10, margins=(0,0,0,0)):
    layout = QHBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def vbox(spacing=12, margins=(0,0,0,0)):
    layout = QVBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def icon(kind, color="#7B858F", size=20):
    pix = QPixmap(size*2, size*2)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size*2/24, size*2/24)
    painter.setPen(QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    def line(a,b,c,d):
        painter.drawLine(QPointF(a,b),QPointF(c,d))
    if kind == "plus":
        line(12,5,12,19); line(5,12,19,12)
    elif kind == "open":
        path=QPainterPath(QPointF(3,7)); path.lineTo(9,7); path.lineTo(11,10); path.lineTo(21,10)
        path.lineTo(19,19); path.lineTo(4,19); path.closeSubpath(); painter.drawPath(path)
        line(3,7,3,17); line(5,5,9,5)
    elif kind == "save":
        painter.drawRoundedRect(QRectF(4,3,16,18),2,2)
        painter.drawRect(QRectF(8,3,8,6)); painter.drawRect(QRectF(8,14,8,7))
    elif kind == "export":
        line(12,3,12,15); line(8,11,12,15); line(16,11,12,15)
        line(4,16,4,20); line(4,20,20,20); line(20,20,20,16)
    elif kind == "paste":
        painter.drawRoundedRect(QRectF(5,5,14,16),2,2)
        painter.drawRoundedRect(QRectF(8,3,8,4),1,1); line(9,11,15,11); line(9,15,15,15)
    elif kind == "arrow":
        line(4,12,20,12); line(15,7,20,12); line(15,17,20,12)
    elif kind == "moon":
        path=QPainterPath(QPointF(17,4)); path.cubicTo(1,3,2,23,18,20)
        path.cubicTo(9,16,9,8,17,4); painter.drawPath(path)
    elif kind == "sun":
        painter.drawEllipse(QRectF(8,8,8,8))
        for angle in range(0,360,45):
            rad=math.radians(angle); line(12+8*math.cos(rad),12+8*math.sin(rad),
                                         12+10*math.cos(rad),12+10*math.sin(rad))
    elif kind == "help":
        painter.drawEllipse(QRectF(3,3,18,18))
        path=QPainterPath(QPointF(9,9)); path.cubicTo(9,5,17,6,15,10); path.cubicTo(14,12,12,11,12,14)
        painter.drawPath(path); line(12,17,12,17.2)
    elif kind == "star":
        path=QPainterPath(QPointF(12,2))
        for x,y in ((15,9),(22,12),(15,15),(12,22),(9,15),(2,12),(9,9)):
            path.lineTo(x,y)
        path.closeSubpath(); painter.drawPath(path)
    elif kind == "compare":
        line(4,7,20,7); line(15,3,20,7); line(15,11,20,7)
        line(20,17,4,17); line(9,13,4,17); line(9,21,4,17)
    else:
        painter.drawEllipse(QRectF(5,5,14,14))
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)


class CompactSpin(QDoubleSpinBox):
    def textFromValue(self, value):
        return f"{value:.{self.decimals()}f}".rstrip("0").rstrip(".") or "0"


class GainChart(QWidget):
    def __init__(self):
        super().__init__()
        self.result = None
        self.palette_data = LIGHT
        self.mode = "hist"
        self.target = 1.
        self.setMinimumHeight(154)
        self.setMouseTracking(True)

    def set_result(self, result, target):
        self.result, self.target = result, target
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c=self.palette_data
        font=QFont("Segoe UI",10); p.setFont(font)
        if not self.result:
            p.setPen(QColor(c["muted"]))
            p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"计算后查看完整收益分布")
            return
        l,t,r,b = 43.,15.,self.width()-14.,self.height()-34.
        self.plot_bounds=(l,t,r,b)
        xmax=max(.5,self.result["maximum"])
        self.xmax=xmax
        dist=self.result["distribution"]
        bins=[0.]*28
        for x,prob in dist:
            if x>0:
                bins[min(27,int(x/xmax*28))]+=prob
        ymax=1. if self.mode=="cdf" else max(.035,max(bins))*1.2
        self.ymax=ymax
        for i in range(4):
            y=b-(b-t)*i/3
            p.setPen(QPen(QColor(c["grid"]),1,Qt.PenStyle.DashLine))
            p.drawLine(QPointF(l,y),QPointF(r,y))
            p.setPen(QColor(c["muted"]))
            p.drawText(QRectF(0,y-9,l-8,18),Qt.AlignmentFlag.AlignRight, f"{ymax*i/3*100:.0f}%")
        for i in range(5):
            x=l+(r-l)*i/4
            p.setPen(QColor(c["muted"]))
            p.drawText(QRectF(x-26,b+10,52,20),Qt.AlignmentFlag.AlignCenter,f"{xmax*i/4:.2f}")
        if self.mode=="hist":
            p.setPen(Qt.PenStyle.NoPen)
            for i,prob in enumerate(bins):
                x=l+i/28*(r-l)
                h=prob/ymax*(b-t)
                p.setBrush(QColor(c["gold"] if prob==max(bins) else c["chart"]))
                p.drawRoundedRect(QRectF(x+2,b-h,max(1,(r-l)/28-4),h),3,3)
        else:
            path=QPainterPath()
            points=[]
            for i in range(101):
                x=xmax*i/100
                prob=sum(prob for value,prob in dist if value>=x-1e-12)
                point=QPointF(l+x/xmax*(r-l),b-prob*(b-t))
                points.append(point)
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            area=QPainterPath(path); area.lineTo(r,b); area.lineTo(l,b); area.closeSubpath()
            fill=QColor(c["gold"]); fill.setAlpha(20)
            p.fillPath(area,fill)
            p.setPen(QPen(QColor(c["gold"]),2.6)); p.drawPath(path)
        marker=self.result["gain"] if self.mode=="hist" else self.target
        if 0<marker<xmax:
            x=l+marker/xmax*(r-l)
            p.setPen(QPen(QColor(c["gold"]),1.1,Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x,t),QPointF(x,b))
            p.setFont(QFont(FONT,9))
            p.drawText(QRectF(x+5,t,100,20),Qt.AlignmentFlag.AlignLeft,"平均净增" if self.mode=="hist" else "目标提升")
        p.end()

    def mouseMoveEvent(self, event):
        if not self.result or not hasattr(self,"plot_bounds"):
            return
        l,t,r,b=self.plot_bounds
        pos=event.position()
        if not l<=pos.x()<=r or not t<=pos.y()<=b:
            QToolTip.hideText(); return
        x=(pos.x()-l)/(r-l)*self.xmax
        if self.mode=="cdf":
            prob=sum(prob for value,prob in self.result["distribution"] if value>=x-1e-12)
            msg=f"至少净增 {x:.2f} 条：{pc(prob)}"
        else:
            step=self.xmax/28; low=int(x/step)*step; high=low+step
            prob=sum(prob for value,prob in self.result["distribution"] if value>0 and low<=value<high+(1e-12 if high>=self.xmax else 0))
            msg=f"净增 {low:.2f}～{high:.2f} 条：{pc(prob)}"
        QToolTip.showText(event.globalPosition().toPoint(),msg,self)

    def leaveEvent(self,event):
        QToolTip.hideText()


class Worker(QObject):
    finished=Signal(object)
    failed=Signal(str)
    progress=Signal(int)
    def __init__(self,job):
        super().__init__(); self.job=job
    @Slot()
    def run(self):
        try:
            self.finished.emit(self.job(self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("启圣之尘 · 收益计算器 2.1")
        self.setWindowIcon(QIcon(str(resource("icon.ico"))))
        self.resize(1380,890)
        self.setMinimumSize(1120,760)
        self.theme="light"
        self.colors=LIGHT
        self.weights={k:"1" if k in ("cr","cd") else "0" for k in E.STAT_KEYS}
        self.loading=False
        self.dirty=True
        self.busy=False
        self.inference=None
        self.results=None
        self.comparison=None
        self.selected_pair=(0,1)
        self.thread=None
        self.worker=None
        self.close_when_done=False
        self.signature_at_start=None
        self.icon_buttons=[]
        self.build()
        self.apply_theme()
        self.new_artifact()

    def button(self,text,kind=None,role="secondary",command=None):
        b=QPushButton(text)
        b.setProperty("role",role)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if kind:
            self.icon_buttons.append((b,kind,role))
        if command:
            b.clicked.connect(command)
        return b

    def card(self,object_name=None):
        f=QFrame(); f.setProperty("role","card")
        if object_name:
            f.setObjectName(object_name)
        return f

    def build(self):
        central=QWidget(); central.setObjectName("shell"); self.setCentralWidget(central)
        root=vbox(19,(26,22,26,14)); central.setLayout(root)
        header=hbox(16)
        logo=QLabel(); logo.setPixmap(QPixmap(str(resource("brand.png"))).scaled(62,62,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(62,62); header.addWidget(logo)
        heading=vbox(3)
        heading.addWidget(text_label("启圣之尘","brand"))
        heading.addWidget(text_label("五星圣遗物重塑 · 让每一次成长都计入期望","muted"))
        header.addLayout(heading); header.addStretch()
        self.new_button=self.button("新建圣遗物","plus",command=self.new_artifact)
        self.open_button=self.button("导入","open","ghost",self.load_config)
        self.save_button=self.button("保存","save","ghost",self.save_config)
        self.export_button=self.button("导出报告","export","ghost",self.export_report)
        for obj in (self.new_button,self.open_button,self.save_button,self.export_button):
            header.addWidget(obj)
        self.theme_button=self.button("","moon","ghost",self.toggle_theme); self.theme_button.setFixedWidth(39)
        self.theme_button.setToolTip("切换明亮 / 深色主题")
        self.help_button=self.button("","help","ghost",self.show_help); self.help_button.setFixedWidth(39)
        self.help_button.setToolTip("怎样填写自己的圣遗物？")
        header.addWidget(self.theme_button); header.addWidget(self.help_button)
        root.addLayout(header)
        body=hbox(22)
        self.input_card=self.card("inputCard"); self.input_card.setFixedWidth(464)
        self.build_input()
        body.addWidget(self.input_card)
        right=vbox(12)
        nav=hbox()
        self.nav=QTabBar(); self.nav.setExpanding(False); self.nav.setDrawBase(False)
        for name in ("收益概览","保底组合","样例对照","核查与规则"):
            self.nav.addTab(name)
        nav.addWidget(self.nav); nav.addStretch()
        self.online_badge=text_label("●  离线计算","green")
        nav.addWidget(self.online_badge)
        right.addLayout(nav)
        self.pages=QStackedWidget(); self.pages.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.overview_page=QWidget(); self.rank_page=self.card(); self.compare_page=self.card(); self.info_page=self.card()
        for page in (self.overview_page,self.rank_page,self.compare_page,self.info_page):
            self.pages.addWidget(page)
        self.nav.currentChanged.connect(self.pages.setCurrentIndex)
        self.build_overview(); self.build_rank(); self.build_compare(); self.build_info()
        right.addWidget(self.pages,1)
        body.addLayout(right,1); root.addLayout(body,1)
        foot=hbox()
        self.status=text_label("准备就绪","muted"); foot.addWidget(self.status,1)
        self.progress=QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedSize(110,4); self.progress.hide()
        foot.addWidget(self.progress)
        foot.addWidget(text_label("DUST  /  2.1","micro"))
        root.addLayout(foot)

    def build_input(self):
        layout=vbox(0,(0,0,0,0)); self.input_card.setLayout(layout)
        self.input_scroll=QScrollArea(); self.input_scroll.setWidgetResizable(True); self.input_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content=QWidget(); self.input_scroll.setWidget(content)
        form=vbox(12,(20,19,20,13)); content.setLayout(form)
        title=hbox(); title.addWidget(text_label("圣遗物","heading")); title.addStretch()
        title.addWidget(text_label("★★★★★  +20","gold")); form.addLayout(title)
        self.name=QLineEdit(); self.name.setPlaceholderText("给这件圣遗物取个名字（可选）")
        self.name.textChanged.connect(self.mark_dirty); form.addWidget(self.name)
        details=QGridLayout(); details.setContentsMargins(0,0,0,0); details.setHorizontalSpacing(12); details.setVerticalSpacing(6)
        details.addWidget(text_label("部位","small"),0,0); details.addWidget(text_label("初始词条","small"),0,1)
        self.slot=QComboBox(); self.slot.addItems(E.SLOTS)
        self.initial=QComboBox(); self.initial.addItems(("自动推断","初始3条","初始4条"))
        self.initial.setToolTip("不知道就选自动。初始三条重塑4次，初始四条重塑5次。")
        details.addWidget(self.slot,1,0); details.addWidget(self.initial,1,1)
        self.slot.currentIndexChanged.connect(self.slot_changed); self.initial.currentIndexChanged.connect(self.mark_dirty)
        form.addLayout(details)
        sample=hbox(7)
        sample.addWidget(self.button("攻击杯示例",role="chip",command=lambda:self.load_sample(0)))
        sample.addWidget(self.button("花示例",role="chip",command=lambda:self.load_sample(1)))
        self.paste_button=self.button("粘贴属性","paste","chip",self.paste_dialog); sample.addWidget(self.paste_button)
        form.addLayout(sample)
        section=hbox(); section.addWidget(text_label("四条副属性","section")); section.addStretch()
        section.addWidget(text_label("填满级面板值","micro")); form.addLayout(section)
        labels=hbox(8,(8,0,8,0))
        type_header=text_label("属性类型","micro")
        labels.addWidget(type_header,1)
        for name,width in (("当前数值",82),("权重",65),("保底",23)):
            obj=text_label(name,"micro"); obj.setFixedWidth(width)
            obj.setAlignment(Qt.AlignmentFlag.AlignCenter); labels.addWidget(obj)
        form.addLayout(labels)
        self.rows=[]
        for i in range(4):
            row=QFrame(); row.setProperty("role","statRow")
            line=hbox(8,(8,5,8,5)); row.setLayout(line)
            stat=QComboBox()
            for key,value in E.STAT_DATA.items():
                stat.addItem(value[0],key)
            stat.setMinimumWidth(153); stat.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            current=QLineEdit(); current.setPlaceholderText("数值"); current.setFixedWidth(62)
            current.setAlignment(Qt.AlignmentFlag.AlignRight)
            unit=text_label("%","micro"); unit.setFixedWidth(17)
            field=hbox(3); field.addWidget(current); field.addWidget(unit)
            weight=CompactSpin(); weight.setRange(0,1000); weight.setDecimals(3); weight.setSingleStep(.25)
            weight.setFixedWidth(65); weight.setToolTip("1=一次平均成长的价值；0=不计收益。支持小数权重。")
            selected=QCheckBox(); selected.setFixedWidth(23); selected.setToolTip("选作游戏保底目标，必须选择两条")
            line.addWidget(stat,1); line.addLayout(field); line.addWidget(weight); line.addWidget(selected)
            hit=QComboBox(); hit.addItems(("自动","0","1","2","3","4","5"))
            base=QComboBox(); base.addItems(TIERS)
            info=dict(stat=stat,value=current,unit=unit,weight=weight,target=selected,hits=hit,base=base,frame=row)
            self.rows.append(info)
            stat.currentIndexChanged.connect(lambda _=0,k=i:self.stat_changed(k))
            current.textChanged.connect(self.mark_dirty); weight.valueChanged.connect(self.mark_dirty)
            selected.toggled.connect(lambda checked,k=i:self.target_changed(k,checked))
            hit.currentIndexChanged.connect(self.mark_dirty); base.currentIndexChanged.connect(self.mark_dirty)
            form.addWidget(row)
        presets=hbox(6)
        for name,kind in (("双暴","crit"),("＋充能","er"),("＋精通","em"),("四条有效","all")):
            presets.addWidget(self.button(name,role="chip",command=lambda _=False,k=kind:self.preset(k)))
        form.addLayout(presets)
        self.selection_hint=text_label("2条有效 · 2条保底","muted"); form.addWidget(self.selection_hint)
        self.advanced_button=QToolButton(); self.advanced_button.setText("高级信息（不知道可保持自动）")
        self.advanced_button.setArrowType(Qt.ArrowType.RightArrow); self.advanced_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_button.setCheckable(True); self.advanced_button.setProperty("role","disclosure")
        self.advanced_button.toggled.connect(self.toggle_advanced); form.addWidget(self.advanced_button)
        self.advanced=QFrame(); self.advanced.setProperty("role","tint")
        adv=vbox(8,(10,12,10,12)); self.advanced.setLayout(adv)
        adv.addWidget(text_label("追加次数不含首次出现；已知信息可缩小收益范围。","micro",True))
        grid=QGridLayout(); grid.setContentsMargins(0,0,0,0); grid.setHorizontalSpacing(8)
        for col,name in enumerate(("副属性","追加次数","基础档位")):
            grid.addWidget(text_label(name,"micro"),0,col)
        self.adv_names=[]
        for i,row in enumerate(self.rows):
            name=text_label("","small"); self.adv_names.append(name)
            grid.addWidget(name,i+1,0); grid.addWidget(row["hits"],i+1,1); grid.addWidget(row["base"],i+1,2)
        adv.addLayout(grid)
        self.main_stat=QComboBox()
        for name,key in MAIN_STATS.items():
            self.main_stat.addItem(name,key)
        adv.addWidget(text_label("主属性类型校验（可选）","micro")); adv.addWidget(self.main_stat)
        self.main_stat.currentIndexChanged.connect(self.mark_dirty)
        self.defined=QCheckBox("祝圣之霜定义：锁定当前两条目标")
        self.defined.toggled.connect(self.lock_changed); adv.addWidget(self.defined)
        form.addWidget(self.advanced); self.advanced.hide()
        form.addStretch()
        layout.addWidget(self.input_scroll,1)
        action=QFrame(); action.setObjectName("inputAction")
        bottom=vbox(10,(20,13,20,17)); action.setLayout(bottom)
        controls=hbox(10)
        controls.addWidget(text_label("本次保底","small"))
        self.guarantee_group=QButtonGroup(self); self.guarantee_buttons=[]
        segment=QFrame(); segment.setProperty("role","segment"); sl=hbox(3,(3,3,3,3)); segment.setLayout(sl)
        for g in (2,3,4):
            button=self.button(f"{g}次",role="segmentButton"); button.setCheckable(True); button.setFixedWidth(47)
            button.setToolTip({2:"普通重塑",3:"高阶重塑",4:"谕告重塑"}[g])
            self.guarantee_group.addButton(button,g); self.guarantee_buttons.append(button); sl.addWidget(button)
        self.guarantee_group.idClicked.connect(self.mark_dirty)
        controls.addWidget(segment); controls.addStretch()
        self.target=CompactSpin(); self.target.setRange(0,100); self.target.setDecimals(2); self.target.setSingleStep(.25)
        self.target.setPrefix("目标 +"); self.target.setSuffix("条"); self.target.setFixedWidth(116)
        self.target.setToolTip("统计至少净增这么多等效平均词条的概率，设0时为100%。")
        self.target.valueChanged.connect(self.mark_dirty); controls.addWidget(self.target)
        bottom.addLayout(controls)
        self.calculate_button=self.button("计算重塑收益","star","primary",self.calculate)
        self.calculate_button.setMinimumHeight(44); bottom.addWidget(self.calculate_button)
        self.input_error=text_label("","error",True); self.input_error.hide(); bottom.addWidget(self.input_error)
        layout.addWidget(action)

    def build_overview(self):
        layout=vbox(0); self.overview_page.setLayout(layout)
        self.overview_scroll=QScrollArea(); self.overview_scroll.setWidgetResizable(True); self.overview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        widget=QWidget(); self.overview_scroll.setWidget(widget)
        self.result_layout=vbox(14); widget.setLayout(self.result_layout)
        title=hbox()
        text=vbox(4)
        self.result_title=text_label("预期收益","heading"); text.addWidget(self.result_title)
        self.result_subtitle=text_label("填写四条属性，看看重塑还能提升多少。","muted",True); text.addWidget(self.result_subtitle)
        title.addLayout(text); title.addStretch()
        self.result_badge=text_label("待计算","badge"); title.addWidget(self.result_badge)
        self.result_layout.addLayout(title)
        self.stale_label=text_label("输入已修改 · 请重新计算后查看结果","warning",True); self.stale_label.hide()
        self.result_layout.addWidget(self.stale_label)
        self.welcome=self.card("welcome")
        welcome=vbox(16,(28,27,28,25)); self.welcome.setLayout(welcome)
        top=hbox(24)
        statement=vbox(8)
        statement.addWidget(text_label("看看这件圣遗物，\n还能提升多少。","hero"))
        statement.addWidget(text_label("计算变好概率、平均净增和每枚尘收益。\n每次强化的四个成长档位都会计入。","muted",True))
        top.addLayout(statement,1)
        mark=QLabel(); mark.setPixmap(QPixmap(str(resource("brand.png"))).scaled(116,116,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        mark.setFixedSize(116,116); top.addWidget(mark)
        welcome.addLayout(top)
        divider=QFrame(); divider.setProperty("role","divider"); divider.setFixedHeight(1); welcome.addWidget(divider)
        for number,name,desc in (("01","填写属性","部位、初始词条数和四条满级副属性。"),
                                  ("02","设定价值","有效属性设正权重，选定两条保底目标。"),
                                  ("03","查看收益","未知基础档位会同时显示估计与收益范围。")):
            line=hbox(16); line.addWidget(text_label(number,"step"))
            words=vbox(3); words.addWidget(text_label(name,"section")); words.addWidget(text_label(desc,"muted",True))
            line.addLayout(words,1); welcome.addLayout(line)
        action=hbox(); action.addWidget(self.button("看看攻击杯示例","arrow","primary",lambda:self.demo(0))); action.addStretch()
        welcome.addLayout(action)
        self.result_layout.addWidget(self.welcome)
        self.output_content=QWidget(); out=vbox(14); self.output_content.setLayout(out)
        score_card=self.card(); score_box=vbox(5,(16,12,16,12)); score_card.setLayout(score_box)
        self.current_score_label=text_label("","section",True); score_box.addWidget(self.current_score_label)
        self.score_breakdown_label=text_label("","small",True); score_box.addWidget(self.score_breakdown_label)
        self.effective_hits_label=text_label("","micro",True); score_box.addWidget(self.effective_hits_label)
        out.addWidget(score_card)
        metrics=hbox(12); self.metric_numbers=[]; self.metric_notes=[]
        for i,name in enumerate(("变好概率","平均净提升","每枚尘收益","目标达成概率")):
            frame=self.card(); frame.setProperty("role","metricHighlight" if i==1 else "card")
            box=vbox(5,(14,15,14,13)); frame.setLayout(box)
            box.addWidget(text_label(name,"small"))
            number=text_label("—","numberGold" if i==1 else "number"); self.metric_numbers.append(number); box.addWidget(number)
            note=text_label("","micro"); self.metric_notes.append(note); box.addWidget(note)
            metrics.addWidget(frame,1)
        out.addLayout(metrics)
        self.range_label=text_label("","range",True); out.addWidget(self.range_label)
        chart_card=self.card(); chart=vbox(8,(18,15,18,10)); chart_card.setLayout(chart)
        chart_top=hbox()
        self.chart_tabs=QTabBar(); self.chart_tabs.setExpanding(False); self.chart_tabs.setDrawBase(False)
        self.chart_tabs.addTab("收益分布"); self.chart_tabs.addTab("至少提升概率")
        self.chart_tabs.currentChanged.connect(self.chart_mode_changed)
        chart_top.addWidget(self.chart_tabs); chart_top.addStretch()
        self.no_gain_tag=text_label("","micro"); chart_top.addWidget(self.no_gain_tag)
        chart.addLayout(chart_top)
        self.chart=GainChart(); chart.addWidget(self.chart)
        self.chart_caption=text_label("横轴：净增加的等效平均词条  ·  鼠标悬停查看概率","micro"); chart.addWidget(self.chart_caption)
        out.addWidget(chart_card)
        comparison_card=self.card(); comp=vbox(10,(18,15,18,13)); comparison_card.setLayout(comp)
        title=hbox(); title.addWidget(text_label("保底机会对照","section")); title.addStretch()
        title.addWidget(text_label("同一保底目标","micro")); comp.addLayout(title)
        self.guarantee_table=self.make_table(("保底档位","变好概率","期望净增","每枚尘收益"),3)
        comp.addWidget(self.guarantee_table)
        self.score_summary=text_label("","muted",True); comp.addWidget(self.score_summary)
        out.addWidget(comparison_card)
        self.result_layout.addWidget(self.output_content); self.output_content.hide()
        self.result_layout.addStretch(); layout.addWidget(self.overview_scroll)

    def build_rank(self):
        layout=vbox(16,(22,23,22,22)); self.rank_page.setLayout(layout)
        layout.addWidget(text_label("选哪两条保底？","heading"))
        layout.addWidget(text_label("比较六种组合，按择优保留后的期望净增排序。\n未选作保底的有效属性，也会计入收益。","muted",True))
        self.rank_table=self.make_table(("保底目标","变好概率","期望净增","每枚尘收益"),6)
        layout.addWidget(self.rank_table)
        self.rank_pairs=[]
        line=hbox(); line.addStretch(); self.adopt_button=self.button("采用选中的组合","arrow","primary",self.use_rank); line.addWidget(self.adopt_button)
        layout.addLayout(line)
        layout.addWidget(text_label("保底目标只选两条，评分权重可覆盖四条。\n比较不同保底时，假定本次已获得对应机会。","muted",True))
        layout.addStretch()

    def build_compare(self):
        layout=vbox(16,(22,23,22,22)); self.compare_page.setLayout(layout)
        title=hbox(); title.addWidget(text_label("两个截图的收益对照","heading")); title.addStretch()
        self.compare_button=self.button("按当前权重比较","compare",command=self.compare_samples); title.addWidget(self.compare_button)
        layout.addLayout(title)
        layout.addWidget(text_label("攻击杯每次消耗2枚；花消耗1枚。总收益与每枚尘收益可以一起比较。","muted",True))
        self.compare_table=self.make_table(("圣遗物","保底","变好概率","期望净增","每枚尘收益"),6)
        layout.addWidget(self.compare_table)
        self.compare_text=QTextBrowser(); self.compare_text.setOpenExternalLinks(True); layout.addWidget(self.compare_text,1)

    def build_info(self):
        layout=vbox(13,(22,23,22,22)); self.info_page.setLayout(layout)
        layout.addWidget(text_label("核查输入与计算依据","heading"))
        self.info_tabs=QTabBar(); self.info_tabs.setExpanding(False); self.info_tabs.setDrawBase(False)
        for name in ("当前输入","填写指南","模型与来源"):
            self.info_tabs.addTab(name)
        layout.addWidget(self.info_tabs)
        self.info_stack=QStackedWidget(); self.info_tabs.currentChanged.connect(self.info_stack.setCurrentIndex)
        self.input_browser=QTextBrowser(); self.help_browser=QTextBrowser(); self.rule_browser=QTextBrowser()
        for browser in (self.input_browser,self.help_browser,self.rule_browser):
            browser.setOpenExternalLinks(True); self.info_stack.addWidget(browser)
        layout.addWidget(self.info_stack,1)

    def make_table(self,headers,rows):
        table=QTableWidget(0,len(headers)); table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide(); table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setHighlightSections(False)
        table.verticalHeader().setDefaultSectionSize(39)
        table.verticalHeader().setMinimumSectionSize(0)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setMinimumHeight(34+rows*39)
        table.setMaximumHeight(34+rows*39)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return table

    def table_rows(self,table,rows):
        table.setRowCount(len(rows))
        for i in range(len(rows)):
            table.setRowHeight(i,36)
        height=table.horizontalHeader().sizeHint().height()+len(rows)*36+4
        table.setMinimumHeight(height); table.setMaximumHeight(height)
        for i,values in enumerate(rows):
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value)); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i,j,item)

    def rich_text(self,text):
        c=self.colors
        return f'<div style="font-family:Microsoft YaHei UI;font-size:13px;line-height:1.8;color:{c["text"]}">' + html.escape(text).replace("\n","<br>") + '</div>'

    def apply_theme(self):
        c=DARK if self.theme=="dark" else LIGHT
        self.colors=c
        palette=QPalette()
        for role,key in ((QPalette.ColorRole.Window,"bg"),(QPalette.ColorRole.WindowText,"text"),
                         (QPalette.ColorRole.Base,"panel"),(QPalette.ColorRole.AlternateBase,"field"),
                         (QPalette.ColorRole.Text,"text"),(QPalette.ColorRole.Button,"panel"),
                         (QPalette.ColorRole.ButtonText,"text"),(QPalette.ColorRole.Highlight,"tint"),
                         (QPalette.ColorRole.HighlightedText,"gold"),(QPalette.ColorRole.ToolTipBase,"panel"),
                         (QPalette.ColorRole.ToolTipText,"text")):
            palette.setColor(role,QColor(c[key]))
        self.setPalette(palette)
        chevron=resource(f"chevron_{self.theme}.png").as_posix()
        check=resource(f"check_{self.theme}.png").as_posix()
        self.setStyleSheet(f'''
            QMainWindow,QWidget#shell {{ background:{c['bg']}; }}
            QWidget {{ color:{c['text']}; font-family:"Microsoft YaHei UI"; font-size:13px; }}
            QLabel {{ background:transparent; border:none; }}
            QLabel[role="brand"] {{ font-size:28px; font-weight:700; letter-spacing:2px; }}
            QLabel[role="heading"] {{ font-size:21px; font-weight:650; }}
            QLabel[role="hero"] {{ font-size:29px; font-weight:650; }}
            QLabel[role="section"] {{ font-size:14px; font-weight:650; }}
            QLabel[role="small"] {{ font-size:12px; color:{c['text']}; }}
            QLabel[role="micro"] {{ font-size:11px; color:{c['muted']}; }}
            QLabel[role="muted"] {{ color:{c['muted']}; font-size:12px; }}
            QLabel[role="gold"],QLabel[role="step"] {{ color:{c['gold']}; }}
            QLabel[role="step"] {{ font-family:"Segoe UI"; font-size:23px; font-weight:600; }}
            QLabel[role="green"] {{ color:{c['green']}; font-size:11px; }}
            QLabel[role="number"],QLabel[role="numberGold"] {{ font-family:"Segoe UI"; font-size:30px; font-weight:650; }}
            QLabel[role="numberGold"] {{ color:{c['gold']}; }}
            QLabel[role="badge"] {{ background:{c['tint']}; color:{c['gold']}; border-radius:13px; padding:7px 13px; font-size:11px; }}
            QLabel[role="range"] {{ color:{c['gold']}; font-size:11px; padding:2px 3px; }}
            QLabel[role="warning"] {{ background:{c['tint']}; color:{c['gold']}; border-radius:9px; padding:10px 12px; }}
            QLabel[role="error"] {{ color:{c['red']}; font-size:11px; }}
            QFrame[role="card"] {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:17px; }}
            QFrame[role="metricHighlight"] {{ background:{c['tint']}; border:1px solid {c['line']}; border-radius:17px; }}
            QFrame[role="statRow"] {{ background:{c['field']}; border:none; border-radius:11px; }}
            QFrame[role="segment"],QFrame[role="tint"] {{ background:{c['field']}; border-radius:10px; }}
            QFrame[role="divider"] {{ background:{c['line']}; }}
            QFrame#inputAction {{ background:{c['panel']}; border-top:1px solid {c['line']}; border-bottom-left-radius:17px; border-bottom-right-radius:17px; }}
            QLineEdit,QComboBox,QDoubleSpinBox {{ background:{c['field']}; border:1px solid {c['line']}; border-radius:9px; padding:7px 8px; min-height:18px; }}
            QLineEdit:focus,QComboBox:focus,QDoubleSpinBox:focus {{ border-color:{c['gold']}; }}
            QComboBox::drop-down {{ border:none; width:22px; }}
            QComboBox::down-arrow {{ image:url("{chevron}"); width:13px; height:13px; }}
            QComboBox QAbstractItemView {{ background:{c['panel']}; border:1px solid {c['line']}; selection-background-color:{c['tint']}; selection-color:{c['text']}; padding:6px; outline:0; }}
            QDoubleSpinBox::up-button,QDoubleSpinBox::down-button {{ width:12px; border:none; background:transparent; }}
            QPushButton {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:10px; padding:8px 12px; font-weight:550; }}
            QPushButton:hover {{ background:{c['field']}; border-color:{c['gold']}; }}
            QPushButton[role="primary"] {{ background:{c['gold']}; color:{'#233044' if self.theme=='dark' else '#FFFFFF'}; border:none; }}
            QPushButton[role="primary"]:hover {{ background:{c['gold_hover']}; }}
            QPushButton[role="ghost"] {{ background:transparent; border:none; padding:8px 10px; }}
            QPushButton[role="ghost"]:hover {{ background:{c['panel']}; }}
            QPushButton[role="chip"] {{ background:{c['field']}; border:none; border-radius:8px; padding:5px 9px; font-size:11px; font-weight:400; }}
            QPushButton[role="chip"]:hover {{ background:{c['tint']}; color:{c['gold']}; }}
            QPushButton[role="segmentButton"] {{ background:transparent; border:none; border-radius:7px; padding:4px 5px; font-size:12px; }}
            QPushButton[role="segmentButton"]:checked {{ background:{c['panel']}; color:{c['gold']}; font-weight:650; }}
            QPushButton:disabled {{ color:{c['muted']}; background:{c['field']}; border-color:{c['line']}; }}
            QPushButton[role="ghost"]:disabled {{ background:transparent; }}
            QToolButton[role="disclosure"] {{ background:transparent; border:none; color:{c['muted']}; padding:4px 0; font-size:11px; }}
            QCheckBox {{ spacing:7px; font-size:11px; }}
            QCheckBox::indicator {{ width:17px; height:17px; border:1px solid {c['line']}; border-radius:5px; background:{c['panel']}; }}
            QCheckBox::indicator:checked {{ background:{c['gold']}; border-color:{c['gold']}; image:url("{check}"); }}
            QTabBar::tab {{ background:transparent; border:none; color:{c['muted']}; padding:9px 14px; margin-right:4px; border-radius:9px; }}
            QTabBar::tab:selected {{ background:{c['panel']}; color:{c['gold']}; font-weight:600; }}
            QTabBar::tab:hover {{ color:{c['gold']}; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollArea > QWidget > QWidget {{ background:transparent; }}
            QScrollBar:vertical {{ width:6px; background:transparent; margin:4px 0; }}
            QScrollBar::handle:vertical {{ background:{c['line']}; border-radius:3px; min-height:35px; }}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{ background:none; }}
            QTableWidget {{ background:transparent; border:none; selection-background-color:{c['tint']}; selection-color:{c['gold']}; outline:0; }}
            QTableWidget::item {{ padding:5px; border-bottom:1px solid {c['line']}; }}
            QHeaderView {{ background:{c['panel']}; }}
            QHeaderView::section {{ background:{c['panel']}; color:{c['muted']}; border:none; padding:7px 4px; font-size:11px; }}
            QTextBrowser,QPlainTextEdit {{ background:{c['panel']}; border:1px solid {c['line']}; border-radius:10px; padding:12px; selection-background-color:{c['tint']}; }}
            QProgressBar {{ background:{c['line']}; border:none; border-radius:2px; }}
            QProgressBar::chunk {{ background:{c['gold']}; border-radius:2px; }}
            QToolTip {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['line']}; border-radius:6px; padding:8px; }}
            QDialog {{ background:{c['bg']}; }}
        ''')
        for button,kind,role in self.icon_buttons:
            color=("#233044" if self.theme=="dark" else "#FFFFFF") if role=="primary" else c["muted"]
            button.setIcon(icon(kind,color))
        self.theme_button.setIcon(icon("sun" if self.theme=="dark" else "moon",c["muted"]))
        self.chart.palette_data=c; self.chart.update()
        self.help_browser.setHtml(self.rich_text(INPUT_GUIDE))
        links="".join(f'<p><a style="color:{c["gold"]}" href="{html.escape(url)}">{html.escape(name)} ↗</a></p>' for name,url in E.SOURCES)
        self.rule_browser.setHtml(self.rich_text(RULE_TEXT)+links)
        if self.inference:
            self.input_browser.setHtml(self.rich_text(inference_text(self.inference)))
        if self.comparison:
            self.show_comparison(navigate=False)

    def toggle_theme(self):
        self.theme="dark" if self.theme=="light" else "light"
        self.apply_theme()

    def show_help(self):
        self.nav.setCurrentIndex(3); self.info_tabs.setCurrentIndex(1)

    def toggle_advanced(self,checked):
        self.advanced.setVisible(checked)
        self.advanced_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def stat_changed(self,index):
        row=self.rows[index]; key=row["stat"].currentData()
        row["unit"].setText("%" if E.STAT_DATA[key][2] else "点")
        self.adv_names[index].setText(E.STAT_DATA[key][0])
        if not self.loading:
            row["weight"].blockSignals(True); row["weight"].setValue(float(self.weights[key])); row["weight"].blockSignals(False)
            self.mark_dirty()

    def slot_changed(self,*_):
        if not self.loading:
            self.main_stat.setCurrentIndex(0); self.mark_dirty()

    def target_changed(self,index,checked):
        if self.loading:
            return
        if checked and sum(row["target"].isChecked() for row in self.rows)>2:
            self.rows[index]["target"].blockSignals(True); self.rows[index]["target"].setChecked(False); self.rows[index]["target"].blockSignals(False)
            self.status.setText("保底目标只能选两条；先取消一条，再勾选新的目标。")
        self.mark_dirty()

    def lock_changed(self,*_):
        for row in self.rows:
            row["target"].setEnabled(not self.defined.isChecked())
        self.mark_dirty()

    def mark_dirty(self,*_):
        if self.loading:
            return
        self.dirty=True
        self.input_error.hide()
        self.refresh_selection()
        self.stale_label.setVisible(bool(self.results))
        if self.results:
            self.result_badge.setText("等待重算")
        self.status.setText("输入已修改，点击计算更新收益。")
        self.update_actions()

    def refresh_selection(self):
        positive=sum(row["weight"].value()>0 for row in self.rows)
        chosen=sum(row["target"].isChecked() for row in self.rows)
        self.selection_hint.setText(f"{positive}条有效属性  ·  已选 {chosen}/2 条保底目标")
        for row in self.rows:
            self.weights[row["stat"].currentData()]=str(row["weight"].value())

    def update_actions(self):
        clean=bool(self.results) and not self.dirty and not self.busy
        self.export_button.setEnabled(clean); self.adopt_button.setEnabled(clean)
        self.calculate_button.setEnabled(not self.busy)
        self.new_button.setEnabled(not self.busy); self.open_button.setEnabled(not self.busy)
        self.compare_button.setEnabled(not self.busy); self.paste_button.setEnabled(not self.busy)

    def signature(self):
        return (self.name.text(),self.slot.currentText(),self.initial.currentIndex(),self.main_stat.currentData(),
                self.guarantee_group.checkedId(),self.target.value(),self.defined.isChecked(),
                tuple((r["stat"].currentData(),r["value"].text(),r["weight"].value(),r["target"].isChecked(),
                       r["hits"].currentIndex(),r["base"].currentIndex()) for r in self.rows))

    def new_artifact(self):
        if self.busy:
            return
        art=E.Artifact("","生之花",None,tuple(E.Row(key,"",self.weights[key]) for key in ("cr","cd","er","em")),(0,1))
        self.apply_artifact(art)
        self.inference=self.results=self.comparison=None
        self.welcome.show(); self.output_content.hide(); self.stale_label.hide()
        self.result_title.setText("预期收益"); self.result_subtitle.setText("填写四条属性，看看重塑还能提升多少。")
        self.result_badge.setText("待计算")
        for table in (self.rank_table,self.compare_table,self.guarantee_table):
            table.setRowCount(0)
        self.input_browser.setHtml(self.rich_text("计算后，这里会列出每条属性的次数和基础档位推断。"))
        self.compare_text.clear()
        self.advanced_button.setChecked(False)
        self.nav.setCurrentIndex(0)
        self.input_scroll.verticalScrollBar().setValue(0)
        self.overview_scroll.verticalScrollBar().setValue(0)
        self.status.setText("选择部位，填四条副属性的当前值；高级信息可保持自动。")
        self.update_actions()
        self.rows[0]["value"].setFocus()

    def apply_artifact(self,art):
        self.loading=True
        try:
            self.name.setText(art.name); self.slot.setCurrentText(art.slot)
            self.initial.setCurrentIndex(0 if art.initial is None else art.initial-2)
            self.main_stat.setCurrentIndex(max(0,self.main_stat.findData(art.main_stat)))
            self.target.setValue(art.target_gain); self.defined.setChecked(art.defined)
            self.guarantee_group.button(art.guarantee).setChecked(True)
            for i,(r,data) in enumerate(zip(self.rows,art.rows)):
                r["stat"].setCurrentIndex(r["stat"].findData(data.stat)); self.stat_changed(i)
                r["value"].setText(data.value); r["weight"].setValue(float(data.weight))
                r["target"].setChecked(i in art.selected)
                r["hits"].setCurrentText("自动" if data.hits is None else str(data.hits))
                r["base"].setCurrentIndex(0 if data.base is None else data.base+1)
                r["target"].setEnabled(not art.defined)
        finally:
            self.loading=False
        self.mark_dirty()

    def collect(self):
        rows=tuple(E.Row(r["stat"].currentData(),r["value"].text().strip(),str(r["weight"].value()),
                         None if r["hits"].currentIndex()==0 else int(r["hits"].currentText()),
                         None if r["base"].currentIndex()==0 else r["base"].currentIndex()-1) for r in self.rows)
        art=E.Artifact(self.name.text().strip() or "我的圣遗物",self.slot.currentText(),
                       None if self.initial.currentIndex()==0 else self.initial.currentIndex()+2,
                       rows,tuple(i for i,r in enumerate(self.rows) if r["target"].isChecked()),
                       self.guarantee_group.checkedId(),self.target.value(),self.defined.isChecked(),self.main_stat.currentData())
        E.validate(art)
        self.refresh_selection()
        return art

    def load_sample(self,index):
        if self.busy:
            return
        art=E.SAMPLES[index]
        self.apply_artifact(replace(art,rows=tuple(replace(r,weight=self.weights[r.stat]) for r in art.rows)))
        self.status.setText("已载入截图示例，点击计算查看收益。")

    def demo(self,index):
        self.load_sample(index); self.calculate()

    def preset(self,kind):
        self.loading=True
        for r in self.rows:
            key=r["stat"].currentData()
            r["weight"].setValue(1 if kind=="all" or key in ("cr","cd",kind) else 0)
        self.loading=False; self.mark_dirty()

    def start_job(self,job):
        if self.busy:
            return
        self.busy=True; self.progress.show(); self.progress.setValue(0)
        self.calculate_button.setText("正在计算…"); self.update_actions()
        self.status.setText("正在计算强化落点、成长档位和全部保底组合…")
        thread=QThread(self); worker=Worker(job); worker.moveToThread(thread)
        self.thread,self.worker=thread,worker
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress.setValue)
        worker.finished.connect(self.job_done); worker.failed.connect(self.job_failed)
        worker.finished.connect(thread.quit); worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater); worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self.thread_finished)
        thread.start()

    @Slot()
    def thread_finished(self):
        if self.close_when_done:
            self.close()

    def calculate(self):
        if self.busy:
            return
        missing=[i+1 for i,r in enumerate(self.rows) if not r["value"].text().strip()]
        if missing:
            self.input_error.setText("请填写第"+"、".join(map(str,missing))+"条副属性的当前数值。")
            self.input_error.show(); self.rows[missing[0]-1]["value"].setFocus(); return
        try:
            art=self.collect()
        except ValueError as exc:
            self.job_failed(str(exc)); return
        self.signature_at_start=self.signature()
        def job(progress):
            inf,results=E.analyze_all(art,lambda done,total:progress(int(done/total*100)))
            return "result",(inf,results)
        self.start_job(job)

    @Slot(object)
    def job_done(self,data):
        self.busy=False; self.progress.hide(); self.calculate_button.setText("计算重塑收益")
        kind,payload=data
        if kind=="result":
            self.inference,self.results=payload
            self.selected_pair=tuple(sorted(self.inference.artifact.selected))
            self.dirty=self.signature()!=self.signature_at_start
            self.show_results()
            self.status.setText("输入已修改，请重新计算。" if self.dirty else "计算完成 · 四个成长档位已全部纳入")
        else:
            self.comparison=payload; self.show_comparison()
            self.status.setText("两个截图样例已按当前权重完成对照。")
        self.update_actions()

    @Slot(str)
    def job_failed(self,message):
        self.busy=False; self.progress.hide(); self.calculate_button.setText("计算重塑收益")
        self.input_error.setText(message); self.input_error.show()
        self.status.setText("请核查输入后重新计算。")
        self.update_actions()

    def pair_name(self,pair,art=None):
        art=art or self.inference.artifact
        return "＋".join(E.STAT_DATA[art.rows[i].stat][0] for i in pair)

    def show_results(self):
        inf=self.inference; art=inf.artifact; g=art.guarantee
        result=self.results[self.selected_pair,g]
        self.welcome.hide(); self.output_content.show()
        self.result_title.setText(art.name)
        effective="＋".join(E.STAT_DATA[r.stat][0] for r in art.rows if E.parse_weight(r.weight)>0) or "无"
        self.result_subtitle.setText("计分："+effective+"  ·  保底："+self.pair_name(self.selected_pair))
        self.current_score_label.setText(f"当前总评分 {inf.current_mean:.3f}  →  择优保留后期望 {result['final_mean']:.3f}")
        breakdown,hit_note=score_details(inf)
        self.score_breakdown_label.setText(breakdown)
        self.effective_hits_label.setText(hit_note)
        self.result_badge.setText("等待重算" if self.dirty else f"保底{g}次  ·  {art.cost}枚尘")
        self.stale_label.setVisible(self.dirty)
        values=(pc(result["pwin"]),fmt(result["gain"]),fmt(result["per_dust"]),pc(result["target_probability"]))
        notes=(f"未提升 {pc(result['no_gain'])}","等效平均词条","等效平均词条",f"至少净增 {art.target_gain:g} 条")
        for label,value,note_label,note in zip(self.metric_numbers,values,self.metric_notes,notes):
            label.setText(value); note_label.setText(note)
        if inf.uncertain:
            low,high=result["gain_range"]
            self.range_label.setText(f"基础档位未确定 · 净增合法范围 {low:.3f}～{high:.3f} 条；上方为条件估计。")
        else:
            self.range_label.setText("基础档位与当前总值已唯一确定。")
        self.chart.set_result(result,art.target_gain)
        self.no_gain_tag.setText("保留原状 "+pc(result["no_gain"]))
        rows=[]
        for gg in (2,3,4):
            r=self.results[self.selected_pair,gg]
            rows.append((f"{gg}次 · "+{2:"普通",3:"高阶",4:"谕告"}[gg],pc(r["pwin"]),fmt(r["gain"]),fmt(r["per_dust"])))
        self.table_rows(self.guarantee_table,rows); self.guarantee_table.selectRow(g-2)
        self.score_summary.setText(f"当前 {inf.current_mean:.3f} → 预计保留 {result['final_mean']:.3f}  ·  成功时平均净增 {result['success_gain']:.3f} 条")
        rank=sorted(((pair,r) for (pair,gg),r in self.results.items() if gg==g),key=lambda x:(x[1]["gain"],x[1]["pwin"]),reverse=True)
        self.rank_pairs=[pair for pair,_ in rank]
        self.table_rows(self.rank_table,[(self.pair_name(pair),pc(r["pwin"]),fmt(r["gain"]),fmt(r["per_dust"])) for pair,r in rank])
        self.rank_table.selectRow(0)
        self.input_browser.setHtml(self.rich_text(inference_text(inf)))
        self.update_actions()

    def chart_mode_changed(self,index):
        self.chart.mode="hist" if index==0 else "cdf"; self.chart.update()

    def use_rank(self):
        if not self.results or self.dirty or self.busy:
            return
        index=self.rank_table.currentRow()
        if index<0:
            return
        pair=self.rank_pairs[index]
        art=replace(self.inference.artifact,selected=pair)
        self.apply_artifact(art); self.inference.artifact=art; self.selected_pair=pair; self.dirty=False
        self.show_results(); self.nav.setCurrentIndex(0)
        self.status.setText("已采用 "+self.pair_name(pair)+"，结果与当前输入一致。")

    def compare_samples(self):
        if self.busy:
            return
        self.refresh_selection(); weights=dict(self.weights); target=self.target.value()
        def job(progress):
            data=[]
            for index,a in enumerate(E.SAMPLES):
                art=replace(a,rows=tuple(replace(r,weight=weights[r.stat]) for r in a.rows),target_gain=target)
                inf=E.infer(art)
                data.append((inf,{g:E.analyze(inf,guarantee=g) for g in (2,3,4)}))
                progress((index+1)*50)
            return "comparison",data
        self.start_job(job)

    def show_comparison(self,navigate=True):
        rows=[]; lines=[]
        for inf,results in self.comparison:
            name="攻击杯" if inf.artifact.cost==2 else "生之花"
            lines.append(inf.artifact.name)
            lines.append("权重："+" / ".join(f"{E.STAT_DATA[r.stat][0]}={r.weight}" for r in inf.artifact.rows))
            for g,r in results.items():
                rows.append((name,f"{g}次",pc(r["pwin"]),fmt(r["gain"]),fmt(r["per_dust"])))
                lines.append(f"保底{g}净增范围：{r['gain_range'][0]:.4f}～{r['gain_range'][1]:.4f}。")
            lines.append("")
        self.table_rows(self.compare_table,rows)
        self.compare_text.setHtml(self.rich_text("\n".join(lines)))
        if navigate:
            self.nav.setCurrentIndex(2)

    def paste_values(self,text):
        parsed=parse_substat_text(text)
        old=self.collect_optional()
        rows=tuple(E.Row(key,value,self.weights[key]) for key,value in parsed)
        pair=tuple(sorted(sorted(range(4),key=lambda i:float(rows[i].weight),reverse=True)[:2]))
        self.apply_artifact(replace(old,rows=rows,selected=pair,defined=False))
        self.status.setText("已填入四条副属性。核对部位和初始词条后点击计算。")

    def collect_optional(self):
        # Used before mandatory values exist: carry only basic metadata.
        return E.Artifact(self.name.text(),self.slot.currentText(),None if self.initial.currentIndex()==0 else self.initial.currentIndex()+2,
                          tuple(),(0,1),self.guarantee_group.checkedId(),self.target.value(),False,self.main_stat.currentData())

    def paste_dialog(self):
        if self.busy:
            return
        dialog=QDialog(self); dialog.setWindowTitle("粘贴四条副属性"); dialog.resize(540,430)
        layout=vbox(14,(24,24,24,24)); dialog.setLayout(layout)
        layout.addWidget(text_label("粘贴属性文字","heading"))
        layout.addWidget(text_label("每条一行，只粘贴四条副属性，不包含主属性。","muted",True))
        field=QPlainTextEdit(); field.setPlaceholderText("暴击率+6.6%\n暴击伤害+20.2%\n防御力+42\n元素精通+23")
        layout.addWidget(field,1)
        error=text_label("","error",True); layout.addWidget(error)
        controls=hbox(); clipboard=self.button("从剪贴板粘贴","paste",command=lambda:field.setPlainText(QApplication.clipboard().text()))
        controls.addWidget(clipboard); controls.addStretch()
        def use():
            try:
                self.paste_values(field.toPlainText())
            except ValueError as exc:
                error.setText(str(exc)); return
            dialog.accept()
        controls.addWidget(self.button("填入这四条","arrow","primary",use)); layout.addLayout(controls)
        dialog.exec()

    def save_config(self):
        try:
            art=self.collect()
        except ValueError as exc:
            self.job_failed(str(exc)); return
        path,_=QFileDialog.getSaveFileName(self,"保存圣遗物与权重","圣遗物配置.json","JSON配置 (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(dict(version=E.VERSION,artifact=E.artifact_to_dict(art),weights=self.weights,theme=self.theme),ensure_ascii=False,indent=2),encoding="utf-8")
            self.status.setText("配置已保存。")
        except OSError as exc:
            self.job_failed(str(exc))

    def load_config(self):
        if self.busy:
            return
        path,_=QFileDialog.getOpenFileName(self,"导入圣遗物配置","","JSON配置 (*.json)")
        if path:
            try:
                data=json.loads(Path(path).read_text(encoding="utf-8-sig")); art=E.artifact_from_dict(data["artifact"])
                E.infer(art)
                for key,value in data.get("weights",{}).items():
                    if key in self.weights:
                        E.parse_weight(value); self.weights[key]=str(value)
                self.apply_artifact(art)
                if data.get("theme") in ("light","dark"):
                    self.theme=data["theme"]; self.apply_theme()
                self.status.setText("已导入配置，点击计算更新结果。")
            except (OSError,ValueError,KeyError,TypeError) as exc:
                self.job_failed(str(exc))

    def export_report(self):
        if not self.results or self.dirty:
            return
        path,_=QFileDialog.getSaveFileName(self,"导出收益报告","启圣之尘收益报告.html","HTML报告 (*.html)")
        if path:
            try:
                save_report(Path(path),self.inference,self.results,self.selected_pair)
                self.status.setText("HTML报告与完整分布CSV已导出。")
            except OSError as exc:
                self.job_failed(str(exc))

    def closeEvent(self,event):
        if self.thread and self.thread.isRunning():
            self.close_when_done=True; self.status.setText("正在结束本次计算…"); event.ignore()
        else:
            event.accept()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify",metavar="JSON_PATH")
    parser.add_argument("--smoke-test",metavar="PNG_PATH")
    parser.add_argument("--preview-new",action="store_true")
    parser.add_argument("--dark",action="store_true")
    parser.add_argument("--preset",choices=("crit","er","em","all"))
    args=parser.parse_args()
    if args.verify:
        data=[]
        for sample in E.SAMPLES:
            inf=E.infer(sample)
            data.append(dict(name=sample.name,current=inf.current_mean,results={g:{k:v for k,v in E.analyze(inf,guarantee=g).items()
                         if k not in ("distribution","raw_distribution","final_distribution")} for g in (2,3,4)}))
        Path(args.verify).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        return
    qt=QApplication(sys.argv[:1]); qt.setStyle("Fusion"); qt.setFont(QFont(FONT,10))
    qt.setApplicationName("启圣之尘收益计算器")
    window=App()
    if args.dark:
        window.theme="dark"; window.apply_theme()
    window.show()
    if not args.preview_new:
        def demo():
            window.load_sample(0)
            if args.preset:
                window.preset(args.preset)
            window.calculate()
        QTimer.singleShot(80,demo)
    if args.smoke_test:
        def capture():
            if window.busy or (not args.preview_new and window.results is None) or (window.thread and window.thread.isRunning()):
                QTimer.singleShot(100,capture); return
            window.grab().save(args.smoke_test)
            window.close(); qt.quit()
        QTimer.singleShot(650,capture)
    sys.exit(qt.exec())


if __name__=="__main__":
    try:
        main()
    except Exception:
        details=traceback.format_exc()
        if QApplication.instance():
            QMessageBox.critical(None,"启动失败",details)
        raise
