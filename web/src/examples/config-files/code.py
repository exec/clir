import json, tempfile, os
from clir import ClirApp

# Write a temp config and load it
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump({"debug": True, "port": 8080}, f)
    cfg_path = f.name

app = ClirApp(name="myapp")
app.load_config(cfg_path)
print("debug =", app.get_config_value("debug"))
print("port  =", app.get_config_value("port"))
os.unlink(cfg_path)
