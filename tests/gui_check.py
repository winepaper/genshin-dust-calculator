"""Exercise only the owned Qt application and its computation workers."""
import time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
ARTIFACTS=ROOT/"artifacts"
ARTIFACTS.mkdir(exist_ok=True)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
import app
import engine as E

qt=QApplication([])
qt.setStyle("Fusion")
root=app.App()
root.show()

def wait_done():
    end=time.monotonic()+30
    while (root.busy or (root.thread and root.thread.isRunning())) and time.monotonic()<end:
        qt.processEvents()
        time.sleep(.015)
    qt.processEvents()
    assert not root.busy
    assert not (root.thread and root.thread.isRunning())
    assert root.input_error.isHidden(), root.input_error.text()

try:
    assert root.results is None
    assert all(not r["value"].text() for r in root.rows)
    assert root.advanced.isHidden()
    root.calculate()
    assert not root.input_error.isHidden()
    root.load_sample(0)
    root.calculate()
    wait_done()
    assert abs(root.results[root.selected_pair,2]["pwin"]-.41078694661458326)<1e-12
    assert root.metric_numbers[0].text()=="41.08%"
    root.preset("er")
    root.calculate()
    wait_done()
    assert "8.000" in root.current_score_label.text()
    assert "元素充能效率" in root.score_breakdown_label.text()
    assert "5 / 总强化 5" in root.effective_hits_label.text()
    assert "计分：元素充能效率＋暴击伤害＋暴击率" in root.result_subtitle.text()
    assert root.metric_numbers[0].text()=="10.59%"
    root.rows[0]["weight"].setValue(.1)
    assert root.dirty and not root.export_button.isEnabled()
    signature=root.signature()
    root.use_rank()
    assert root.signature()==signature
    root.preset("all")
    root.calculate()
    wait_done()
    assert all(E.parse_weight(r.weight)==1 for r in root.inference.artifact.rows)
    root.rank_table.selectRow(0)
    root.use_rank()
    assert not root.dirty
    root.defined.setChecked(True)
    assert all(not r["target"].isEnabled() for r in root.rows)
    root.defined.setChecked(False)
    root.compare_samples()
    wait_done()
    assert root.compare_table.rowCount()==6
    root.load_sample(1)
    root.preset("crit")
    root.calculate()
    wait_done()
    assert abs(root.results[root.selected_pair,2]["pwin"]-.17405414581298717)<1e-12
    report=ARTIFACTS/"ui-test-report.html"
    app.save_report(report,root.inference,root.results,root.selected_pair)
    assert report.exists() and report.with_suffix(".csv").exists()
    root.toggle_theme()
    assert root.theme=="dark"
    root.toggle_theme()
    assert root.theme=="light"
    root.resize(1120,760)
    qt.processEvents()
    assert root.calculate_button.isVisible()
    root.grab().save(str(ARTIFACTS/"ui-minimum.png"))
    root.new_artifact()
    assert root.results is None
    assert all(r["hits"].currentIndex()==0 and r["base"].currentIndex()==0 for r in root.rows)
    root.paste_values("暴击率+6.6%\n暴击伤害+20.2%\n防御力+42\n元素精通+23")
    assert [r["value"].text() for r in root.rows]==["6.6","20.2","42","23"]
    root.initial.setCurrentIndex(1)
    root.calculate()
    wait_done()
    assert not root.dirty
    assert abs(root.results[root.selected_pair,2]["pwin"]-.17405414581298717)<1e-12
    root.advanced_button.setChecked(True)
    assert not root.advanced.isHidden()
    root.advanced_button.setChecked(False)
    assert root.advanced.isHidden()
    root.guarantee_group.button(4).click()
    assert root.dirty and root.collect().guarantee==4
    root.calculate()
    wait_done()
    root.chart_tabs.setCurrentIndex(1)
    assert root.chart.mode=="cdf"
    root.new_artifact()
    root.compare_samples()
    wait_done()
    assert root.compare_table.rowCount()==6
    print("PASS: Qt UI, workers, both themes, new/reset, required fields, advanced fields, text paste, stale guard, four weights, best pair, definition lock, sample comparison, chart switch, report export, minimum window")
finally:
    root.close()
    qt.processEvents()
