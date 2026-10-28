"""Measure warm map updates including synchronous painting at fit and 4x zoom."""
import json
from pathlib import Path
import statistics
import time

from PySide6.QtWidgets import QApplication
from main import Window

app = QApplication([])
window = Window()
window.timer.stop()
window.show()
app.processEvents()
window.category.setCurrentText('All')
window.radius.setValue(60)
window.network.setChecked(True)
results = []
for floor in (0, 1):
    window.floor.setCurrentIndex(floor)
    window.player.node = 'g0' if floor == 0 else 'f0'
    window.player.target = None
    window.player.transport = 'lift'
    window.destination = window.model.by_id['first:levis' if floor == 0 else 'ground:denza']
    for zoom in (1, 4):
        window.view.reset_view()
        window.view.zoom(zoom)
        samples = []
        for _ in range(60):
            start = time.perf_counter()
            window.player.move(0, -1, .016)
            window.refresh()
            app.processEvents()
            window.view.viewport().repaint()
            samples.append((time.perf_counter()-start)*1000)
        samples = samples[5:]
        result = {'floor': floor, 'zoom': zoom,
                  'median_ms': round(statistics.median(samples), 2),
                  'p95_ms': round(sorted(samples)[52], 2)}
        results.append(result)
        print(result, flush=True)
        assert result['p95_ms'] < 50, 'Warm map updates exceeded the 50 ms regression budget'
Path('verification').mkdir(exist_ok=True)
Path('verification/performance.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
window.close()
