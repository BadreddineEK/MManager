
with open("/home/mosquee/nidham-dev/frontend/index.html", "r", encoding="utf-8") as f:
    c = f.read()

# Supprimer le premier plan-banner (le mauvais avec chr(39))
import re
# Remplacer les deux plan-banner par un seul correct
pattern = (
    '    <div id="plan-banner" class="plan-banner hidden">\n'
    '      <span id="plan-trial-info"></span>\n'
    "      <button class=\"btn-upgrade\" onclick=\"showSection(chr(39)settings chr(39))\">Upgrader</button>\n"
    '    </div>\n'
    '\n'
    '    <div id="plan-banner" class="plan-banner hidden">\n'
    '      <span id="plan-trial-info"></span>\n'
    "      <button class=\"btn-upgrade\" onclick=\"showSection('settings')\">Upgrader</button>\n"
    '    </div>'
)
replacement = (
    '    <div id="plan-banner" class="plan-banner hidden">\n'
    '      <span id="plan-trial-info"></span>\n'
    "      <button class=\"btn-upgrade\" onclick=\"showSection('settings')\">Upgrader \u2192</button>\n"
    '    </div>'
)
if pattern in c:
    c = c.replace(pattern, replacement)
    print("doublon supprime: OK")
else:
    print("PATTERN NOT FOUND")
    idx = c.find('plan-banner')
    print(repr(c[idx:idx+500]))

with open("/home/mosquee/nidham-dev/frontend/index.html", "w", encoding="utf-8") as f:
    f.write(c)
print("plan-banner occurrences:", c.count('id="plan-banner"'))
