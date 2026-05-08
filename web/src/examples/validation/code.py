from clir import BaseModel, Field, ValidationError, ClirApp, argument, option
from clir.output import error

class Config(BaseModel):
    port: int = Field(ge=1, le=65535)
    host: str = "localhost"

app = ClirApp(name="serve")

@app.command()
@argument("port")
@option("--host", default="localhost")
def start(port: str, host: str = "localhost"):
    try:
        cfg = Config(port=int(port), host=host)
        print(f"Starting on {cfg.host}:{cfg.port}")
    except ValidationError as e:
        for err in e.errors():
            error(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}")

app.run(["start", "99999"])
