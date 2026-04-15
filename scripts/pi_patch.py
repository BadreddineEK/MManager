with open("/home/mosquee/nidham-dev/frontend/index.html", "r", encoding="utf-8") as f:
    c = f.read()
orig = len(c)
c = c.replace("<title>Mosqu\u00e9e Manager</title>", "<title>Nidham</title>")
c = c.replace('<div class="brand-name">Mosqu\u00e9e Manager</div>', '<div class="brand-name" id="sidebar-mosque-name">Ma Mosqu\u00e9e</div>')
c = c.replace('<div class="brand-sub">Administration</div>', '<div class="brand-sub">Administration \u00b7 <span id="plan-badge" class="plan-badge">Free</span></div>')
ANCHOR = "</div>\n\n    <!-- Dashboard -->"
BANNER = '</div>\n\n    <div id="plan-banner" class="plan-banner hidden">\n      <span id="plan-trial-info"></span>\n      <button class="btn-upgrade" onclick="showSection(\'settings\')">Upgrader</button>\n    </div>\n\n    <!-- Dashboard -->'
if ANCHOR in c:
    c = c.replace(ANCHOR, BANNER, 1)
    print("plan-banner: OK")
else:
    print("plan-banner: NOT FOUND")
OLD = '<script src="js/bulk.js"></script>\n<script src="js/auth.js"></script>'
NEW = '<script src="js/bulk.js"></script>\n<script src="js/plan.js"></script>\n<script src="js/auth.js"></script>'
if OLD in c:
    c = c.replace(OLD, NEW)
    print("plan.js: OK")
else:
    print("plan.js: NOT FOUND")
with open("/home/mosquee/nidham-dev/frontend/index.html", "w", encoding="utf-8") as f:
    f.write(c)
print("chars: %d -> %d" % (orig, len(c)))
for k in ["sidebar-mosque-name","plan-badge","plan-banner","plan.js"]:
    print(k + ": " + ("OK" if k in c else "MISSING"))
