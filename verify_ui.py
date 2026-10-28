"""Repeatable Qt interaction checks and screenshots; no changes to source maps."""
import json
from pathlib import Path
import sys
import math
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent, QMouseEvent, QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from main import Window, STYLE
from label_layout import pixel_box
from PySide6.QtGui import QRegion

app = QApplication.instance() or QApplication(sys.argv)
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
w = Window()
w.timer.stop()
w.show()
app.processEvents()
out=Path('verification')
out.mkdir(exist_ok=True)
checks=[]


def check(condition,name):
    assert condition,name
    checks.append(name)


def choose(query):
    w.search.setText(query)
    app.processEvents()
    item=w.stores.item(0)
    check(bool(item.data(Qt.ItemDataRole.UserRole)),'Search '+query)
    QTest.mouseClick(w.stores.viewport(),Qt.MouseButton.LeftButton,pos=w.stores.visualItemRect(item).center())
    app.processEvents()


choose('Fore')
artwork=w.view.svg.pixmap().toImage()
check(artwork.pixelColor(300,300).name()=='#c1c1c1','GF artwork retains exterior coordinates')
check(artwork.pixelColor(2390,1640).name()=='#f4f0e9','GF artwork aligns with player corridor')
check(w.destination.id=='ground:fore','Click search result selects destination')
check('Remaining' in w.route_label.text(),'Route to Fore displayed')
w.view.reset_view()
w.grab().save(str(out/'ground-floor-ui.png'))
before=w.player.xy
w.refresh()
network_item=w.view.network_item
player_item=w.view.player_item
buffer_item=w.view.buffer_item
w.search.setFocus()
QTest.keyClicks(w.search,'wasd')
w.tick()
check(w.player.xy==before,'Typing does not move player')
w.search.clear()
w.view.setFocus()
QTest.keyPress(w.view,Qt.Key.Key_W)
check(Qt.Key.Key_W in w.view.keys,'Keyboard movement key captured')
w.player.move(0,-1,.1)
QTest.keyRelease(w.view,Qt.Key.Key_W)
check(w.player.xy!=before,'Player movement follows graph')
w.refresh()
check(w.view.network_item is network_item,'Static corridor graphics reused')
check(w.view.player_item is player_item and w.view.buffer_item is buffer_item,'Player and buffer graphics reused')
check(not w.view.keys,'Keyboard movement release clears key')
w.activateWindow()
w.view.setFocus()
app.processEvents()
before=w.player.xy
w.last_time=__import__('time').monotonic()
w.timer.start(30)
QTest.keyPress(w.view,Qt.Key.Key_W)
QTest.qWait(300)
QTest.keyRelease(w.view,Qt.Key.Key_W)
w.timer.stop()
check(w.player.xy!=before,'Live timer moves player while keyboard key is held')
for speed, keyboard in ((.5, True), (12, False)):
    w.speed.setValue(speed)
    w.view.setFocus()
    if keyboard:
        QTest.keyPress(w.view, Qt.Key.Key_W)
    else:
        w.set_direction((0,-1))
    with patch.object(w.player, 'move', wraps=w.player.move) as move:
        w.last_time=__import__('time').monotonic()-.05
        w.tick()
        check(move.called and move.call_args.args[3] == speed, f'Speed {speed} reaches movement via keyboard={keyboard}')
    QTest.keyRelease(w.view, Qt.Key.Key_W)
    w.set_direction((0,0))
w.speed.setValue(3)
w.transport.setCurrentIndex(2)
choose('Lacoste')
check('escalator' in w.route_label.text(),'Cross-floor routing instruction')
w.floor.setCurrentIndex(1)
check(w.player.floor=='ground' and w.viewed_floor=='first','Viewing floor does not teleport player')
first_map=w.view.svg
check(first_map.pixmap().toImage().pixelColor(2400,1400).name()=='#f4f0e9','1F artwork aligns with corridor coordinates')
w.floor.setCurrentIndex(0)
w.floor.setCurrentIndex(1)
check(w.view.svg is first_map,'Floor artwork reused after switching')
w.view.reset_view()
w.grab().save(str(out/'first-floor-ui.png'))
w.player.node='ground-central-escalator-approach'
w.player.target=None
w.player.progress=0
w.refresh()
check(w.cross.isEnabled(),'Transition enabled at connector')
QTest.mouseClick(w.cross,Qt.MouseButton.LeftButton)
check(w.player.floor=='first','Explicit floor transition')
w.category.setCurrentText('ATMs')
check('0 results' in w.near_status.text(),'Unavailable category has empty state')
w.category.setCurrentText('Escalators')
check(w.nearby_list.item(0).data(Qt.ItemDataRole.UserRole)=='first:central-escalator','Nearby follows player floor')
item=w.nearby_list.item(0)
QTest.mouseClick(w.nearby_list.viewport(),Qt.MouseButton.LeftButton,pos=w.nearby_list.visualItemRect(item).center())
check(w.destination.id=='first:central-escalator','Recommendation click sets destination')
check('Arrived' in w.route_label.text(),'Arrival message')
choose('MyCWS')
check(w.destination.entrance is not None and 'Remaining' in w.route_label.text(),'Newly mapped lounge destination routes')
choose('Autoschoon')
check('unavailable' in w.route_label.text() and 'parking' in w.route_label.text(),'Unmapped parking connection is explained')
w.search.setText('nothing matches this')
check(not w.stores.item(0).data(Qt.ItemDataRole.UserRole),'Search empty state')
buttons={b.text():b for b in w.findChildren(QPushButton)}
for name in ['Zoom in','Zoom out','Reset view','Clear destination','Show player floor']:
    before_scale=w.view.transform().m11()
    QTest.mouseClick(buttons[name],Qt.MouseButton.LeftButton)
    if name=='Zoom in': check(w.view.transform().m11()>before_scale,'Zoom in control')
    if name=='Zoom out': check(w.view.transform().m11()<before_scale,'Zoom out control')
check(w.destination is None,'Clear destination control')
w.view.setFocus()
pos=w.view.viewport().rect().center()
before_scale=w.view.transform().m11()
wheel=QWheelEvent(QPointF(pos),QPointF(w.view.viewport().mapToGlobal(pos)),QPoint(0,0),QPoint(0,120),
                  Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
QApplication.sendEvent(w.view.viewport(),wheel)
check(w.view.transform().m11()>before_scale,'Mouse wheel zoom')
w.view.zoom(2)
w.view.centerOn(w.view.sceneRect().center())
app.processEvents()
before_scroll=(w.view.horizontalScrollBar().value(),w.view.verticalScrollBar().value())
QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=pos)
move=QMouseEvent(QMouseEvent.Type.MouseMove,QPointF(pos+QPoint(60,40)),
                 QPointF(w.view.viewport().mapToGlobal(pos+QPoint(60,40))),
                 Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(w.view.viewport(),move)
QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=pos+QPoint(60,40))
after_scroll=(w.view.horizontalScrollBar().value(),w.view.verticalScrollBar().value())
check(before_scroll!=after_scroll,'Mouse drag pan')
w.view.reset_view()
for name in ['Left','Up','Down','Right']:
    QTest.mousePress(buttons[name],Qt.MouseButton.LeftButton)
    check(w.held_direction!=(0,0),name+' on-screen movement press')
    QTest.mouseRelease(buttons[name],Qt.MouseButton.LeftButton)
    check(w.held_direction==(0,0),name+' on-screen movement release')
w.radius.setValue(35)
check('35 m' in w.near_status.text(),'Custom radius applied')
w.network.setChecked(False)
check(not w.network.isChecked(),'Mapped paths toggle')
w.network.setChecked(True)
choose('Lacoste')
for floor_index in (0, 1):
    w.floor.setCurrentIndex(floor_index)
    labels = w.view.shop_labels[w.viewed_floor]
    captions = '\n'.join(item.toolTip() for item in labels)
    check(all(item.data(2) for item in labels), f'Floor {floor_index}: every label matches a source shop silhouette')
    check(all(QRegion(pixel_box(item.sceneBoundingRect().center(), item.rect().width(), item.rect().height())).subtracted(item.data(1)).isEmpty()
              for item in labels), f'Floor {floor_index}: entire labels fit inside shop silhouettes')
    check(not any(a.sceneBoundingRect().intersects(b.sceneBoundingRect()) for i,a in enumerate(labels) for b in labels[i+1:]),
          f'Floor {floor_index}: shop labels do not overlap')
    check(all(p.title in captions for p in w.model.places if p.floor == w.viewed_floor and p.category in ('Stores', 'Dining')),
          f'Floor {floor_index}: every directory shop has a fixed label')
    positions = [item.pos() for item in labels]
    w.view.zoom(1.2)
    w.refresh()
    check(positions == [item.pos() for item in labels], f'Floor {floor_index}: labels stay anchored after zoom and refresh')
    w.view.reset_view()
    for picture, graph in ((True, False), (False, True), (False, False), (True, True)):
        w.map_picture.setChecked(picture)
        w.network.setChecked(graph)
        w.refresh()
        w.view.update_player()
        check(w.view.svg.isVisible() == picture, f'Floor {floor_index}: picture visibility {picture}/{graph}')
        check(w.view.network_item.isVisible() == graph and
              w.view.structure_items[w.viewed_floor].isVisible() == graph and
              all(item.isVisible() == graph for item in w.view.overlay),
              f'Floor {floor_index}: graph visibility {picture}/{graph}')
        check(w.view.player_item.isVisible() == (graph and w.player.floor == w.viewed_floor),
              f'Floor {floor_index}: player visibility {picture}/{graph}')
        check(all(item.isVisible() == graph for item in labels), f'Floor {floor_index}: shop label visibility {picture}/{graph}')
        check(all(item.brush().style() == Qt.BrushStyle.NoBrush and
                  item.childItems()[0].brush().color().name() == ('#ffffff' if picture and item.data(0) else '#20332c')
                  for item in labels), f'Floor {floor_index}: text-only labels adapt to background {picture}/{graph}')
        if not picture and graph:
            w.grab().save(str(out/f'graph-only-{floor_index}.png'))
w.map_picture.setChecked(False)
w.network.setChecked(False)
w.floor.setCurrentIndex(0)
check(not any(item.isVisible() for item in w.view.scene().items()), 'Both layers stay hidden across floor switch')
w.map_picture.setChecked(True)
w.network.setChecked(True)
choose('Fore')
w.stores.setFocus()
QTest.keyClick(w.stores,Qt.Key.Key_Return)
check(w.destination.id=='ground:fore','Enter activates search result')
w.player.node='first-central-escalator-approach'
w.player.target=None
w.view.setFocus()
QTest.keyClick(w.view,Qt.Key.Key_E)
check(w.player.floor=='ground','E key uses floor connector')
w.transport.setCurrentIndex(1)
choose('Lacoste')
check('lift' in w.route_label.text(),'Lift-only route instruction')
w.show_player()
w.grab().save(str(out/'lift-route-ui.png'))
lift=next(c for c in w.model.data['connectors'] if c['kind']=='lift')
w.player.node=lift['a']
w.player.target=None
w.refresh()
check('lift' in w.cross.text() and w.cross.isEnabled(),'Lift action enabled near lift')
QTest.mouseClick(w.cross,Qt.MouseButton.LeftButton)
check(w.player.node==lift['b'] and w.player.floor=='first','Lift action changes floor')
w.player.node='g0'
w.player.target=None
w.transport.setCurrentIndex(2)
check('escalator' in w.route_label.text(),'Escalator-only route instruction')
w.transport.setCurrentIndex(0)
for connection in w.model.data['connectors']:
    if connection['kind'] != 'escalator':
        continue
    for end, other in ((connection['a'],connection['b']),(connection['b'],connection['a'])):
        for use_key in (False, True):
            w.player.node = 'g0' if w.model.nodes[end]['floor']=='ground' else 'f0'
            w.player.target=None
            w.player.progress=0
            path,_=w.player.route(end)
            remaining=2.5
            for a,b in reversed(list(zip(path,path[1:]))):
                length=math.dist(w.model.nodes[a]['xy'],w.model.nodes[b]['xy'])*w.model.scale
                if length>=remaining:
                    w.player.node,w.player.target,w.player.progress=a,b,1-remaining/length
                    break
                remaining-=length
            w.show_player()
            w.refresh()
            check(w.cross.isEnabled() and connection['name'] in w.cross.toolTip(),
                  f'Nearby connection available: {end}, keyboard={use_key}')
            w.view.setFocus()
            if use_key:
                QTest.keyClick(w.view,Qt.Key.Key_E)
            else:
                QTest.mouseClick(w.cross,Qt.MouseButton.LeftButton)
            check(w.player.node==other and w.player.target is None,
                  f'Nearby connection changes floor: {end}, keyboard={use_key}')
            repeat=QKeyEvent(QKeyEvent.Type.KeyPress,Qt.Key.Key_E,Qt.KeyboardModifier.NoModifier,'e',True)
            QApplication.sendEvent(w.view,repeat)
            check(w.player.node==other,'Held E cannot bounce back: '+end)
w.player.node='g0'
w.player.target=None
w.player.progress=0
w.search.setText('no such tenant')
w.clear_destination()
w.show_player()
w.resize(900,680)
app.processEvents()
w.view.reset_view()
w.grab().save(str(out/'compact-ui.png'))
check(w.view.width()>200,'Compact layout preserves map')
(out/'ui-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(f'{len(checks)} Qt interaction checks passed; screenshots in {out.resolve()}')
w.close()
