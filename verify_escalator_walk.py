"""Walk the live Qt UI to every escalator without setting player positions."""
import json
import math
import time
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from main import Window, STYLE
from navigation import ROOT

app=QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
w=Window()
w.show()
w.activateWindow()
app.processEvents()
w.speed.setValue(12)
w.view.setFocus()
headings=[((dx,dy),keys) for dx,dy,keys in [
    (1,0,(Qt.Key.Key_D,)),(-1,0,(Qt.Key.Key_A,)),(0,1,(Qt.Key.Key_S,)),(0,-1,(Qt.Key.Key_W,)),
    (1,1,(Qt.Key.Key_D,Qt.Key.Key_S)),(1,-1,(Qt.Key.Key_D,Qt.Key.Key_W)),
    (-1,1,(Qt.Key.Key_A,Qt.Key.Key_S)),(-1,-1,(Qt.Key.Key_A,Qt.Key.Key_W))]]
held=()
records=[]
connections=[c for c in w.model.data['connectors'] if c['kind']=='escalator']
for connection in connections * 2:
    end=next(n for n in (connection['a'],connection['b']) if w.model.nodes[n]['floor']==w.player.floor)
    other=connection['b'] if end==connection['a'] else connection['a']
    place=next(p for p in w.model.places if p.category=='Escalators' and p.entrance==end)
    w.search.setText(place.title)
    item=next(w.stores.item(i) for i in range(w.stores.count()) if w.stores.item(i).data(Qt.ItemDataRole.UserRole)==place.id)
    w.stores.scrollToItem(item)
    QTest.mouseClick(w.stores.viewport(),Qt.MouseButton.LeftButton,pos=w.stores.visualItemRect(item).center())
    w.view.setFocus()
    QTest.qWait(50)
    deadline=time.monotonic()+90
    print('Starting',end,'active',w.isActiveWindow(),flush=True)
    while w.player.connector()!=connection:
        if time.monotonic()>deadline:
            raise AssertionError(f'UI walk stuck toward {end}: {w.player.xy}, {w.player.node}, {w.player.target}')
        path,_=w.player.route(end)
        assert path and all(w.model.nodes[n]['floor']==w.player.floor for n in path)
        index=0
        if w.player.target is None and path[0]==w.player.node and len(path)>1:
            index=1
        waypoint=w.model.nodes[path[index]]['xy']
        if math.dist(w.player.xy,waypoint)*w.model.scale<1.5 and index+1<len(path):
            origin=waypoint
            waypoint=w.model.nodes[path[index+1]]['xy']
        else:
            origin=w.player.xy
        dx,dy=waypoint[0]-origin[0],waypoint[1]-origin[1]
        keys=max(headings,key=lambda h:(h[0][0]*dx+h[0][1]*dy)/math.hypot(*h[0]))[1]
        if keys!=held or not w.view.keys:
            for key in held: QTest.keyRelease(w.view,key)
            for key in keys: QTest.keyPress(w.view,key)
            held=keys
        QTest.qWait(25)
    for key in held: QTest.keyRelease(w.view,key)
    held=()
    w.refresh()
    assert w.cross.isEnabled()
    position=w.player.xy
    if len(records)%2:
        QTest.mouseClick(w.cross,Qt.MouseButton.LeftButton)
    else:
        QTest.keyClick(w.view,Qt.Key.Key_E)
    assert w.player.node==other
    records.append(dict(endpoint=end,approach_xy=position,arrived_node=w.player.node))
    print('Walked UI and used connection:',end,flush=True)
    w.view.setFocus()
(ROOT/'verification/escalator-ui-walk.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
w.close()
print('All ten endpoints reached with live keyboard movement and floor actions',flush=True)
