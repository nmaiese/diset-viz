"""Una copia del sito su una seconda URL, per guardarla prima che il branch tocchi master.

Deploya il worktree COM'E', non un branch remoto: `gcloud run deploy --source .`
manda a Cloud Build il contenuto della cartella, quindi si guarda esattamente
quello che si ha davanti, anche non committato. E' il punto: uno stage che
deploya `master` non serve a decidere se mandare una modifica in master.

    bin/py scripts/deploy_staging.py        (oppure bin/deploy-staging)

Lo stesso script lo esegue Cloud Build a ogni push sul branch `stage`
(cloudbuild-staging.yaml), passando STAGING_IMAGE con l'immagine gia'
costruita: il deploy automatico e quello a mano fanno le stesse cose e passano
dalle stesse verifiche. Solo libreria standard, cosi' gira anche nell'immagine
di gcloud e su Windows.

Il servizio e' separato da quello di produzione e non ne eredita niente:

  - `--set-env-vars` (non `--update-env-vars`) azzera l'ambiente e imposta solo
    STAGING=1. Quindi niente GTM, niente GA, niente AdSense, niente verifiche di
    proprieta': sono tutte env-gated e qui non ci sono.
  - Senza DATABASE_URL l'app cade sullo SQLite locale del container, che e'
    effimero. Lo stage NON puo' scrivere sul Postgres di produzione.
  - STAGING=1 rende ogni risposta `noindex, nofollow, noarchive` e fa dire a
    /robots.txt `Disallow: /`. Senza, Google si troverebbe un duplicato completo
    di divarioitalia.it su un secondo dominio.
  - STAGING_PASSWORD chiude tutto dietro un Basic Auth. Lo script ne genera una
    al primo deploy e poi la RIUSA. Per sceglierla: STAGING_PASSWORD=...

Le verifiche finali: se una salta, il deploy e' andato ma lo script esce rosso.
"""
from __future__ import annotations

import base64
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICE = os.environ.get("STAGING_SERVICE", "diset-viz-staging")
REGION = os.environ.get("STAGING_REGION", "europe-west1")
PASSWORD_CHARS = re.compile(r"^[A-Za-z0-9._~-]*$")


def gcloud_exe() -> str:
    exe = shutil.which("gcloud")
    if not exe:
        raise SystemExit(
            "deploy-staging: gcloud non e' installato.\n"
            "  https://cloud.google.com/sdk/docs/install"
        )
    return exe


def gcloud(*args: str, check: bool = True) -> str:
    """Esegue gcloud senza shell e restituisce lo stdout."""
    exe = gcloud_exe()
    proc = subprocess.run([exe, *args], capture_output=True, text=True, cwd=ROOT)
    if check and proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def gcloud_stream(*args: str) -> None:
    """Esegue gcloud lasciando l'output sul terminale (il deploy e' lungo)."""
    if subprocess.run([gcloud_exe(), *args], cwd=ROOT).returncode != 0:
        raise SystemExit(1)


def describe(fmt: str) -> str:
    return gcloud("run", "services", "describe", SERVICE, "--region", REGION,
                  "--format", fmt, check=False)


def env_value(name: str) -> str:
    return describe(
        f'value(spec.template.spec.containers[0].env.filter("name:{name}").extract("value"))'
    )


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)


def http(url: str, auth: tuple[str, str] | None = None, head: bool = False) -> tuple[int, dict, str]:
    """GET (o HEAD) senza seguire altro: restituisce stato, header in minuscolo, corpo."""
    headers = {}
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(url, headers=headers, method="HEAD" if head else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, {k.lower(): v for k, v in err.headers.items()}, err.read().decode("utf-8", "replace")


def main() -> int:
    account = gcloud("auth", "list", "--filter=status:ACTIVE", "--format=value(account)", check=False)
    if not account:
        print("deploy-staging: nessun account gcloud attivo. Esegui:  gcloud auth login", file=sys.stderr)
        return 1
    project = gcloud("config", "get-value", "project", check=False)
    if not project or project == "(unset)":
        print("deploy-staging: nessun progetto impostato. Esegui:  gcloud config set project IL_TUO_PROGETTO",
              file=sys.stderr)
        return 1

    # La password dello stage, in ordine: quella gia' sul servizio (per non
    # invalidare il link che qualcuno ha in mano), poi quella chiesta
    # dall'ambiente, infine una generata. Non esiste il caso "senza password".
    existing = env_value("STAGING_PASSWORD")
    requested = os.environ.get("STAGING_PASSWORD", "")
    password = requested or existing
    origin = "presa da STAGING_PASSWORD" if requested else "riusata dal servizio"
    if not password:
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(20))
        origin = "generata adesso"
    # `--set-env-vars` separa le variabili con la virgola: una password che ne
    # contiene una arriverebbe troncata e lo stage risponderebbe 401 a chi usa
    # quella giusta.
    if not PASSWORD_CHARS.match(password):
        print("deploy-staging: la password puo' contenere solo lettere, cifre e . _ ~ -\n"
              "  (la virgola separa le variabili d'ambiente di gcloud)", file=sys.stderr)
        return 1

    user = os.environ.get("STAGING_USER", "divario")
    image = os.environ.get("STAGING_IMAGE", "")
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "?"
    dirty = ""
    if not image and git("diff", "--quiet", "HEAD").returncode != 0:
        dirty = " (con modifiche non committate)"
    source_label = f"immagine {image}" if image else f"{branch}{dirty}"

    print("Stage di Divario Italia")
    print(f"  progetto: {project}")
    print(f"  servizio: {SERVICE} ({REGION})")
    print(f"  sorgente: {source_label}")
    print()

    source = ["--image", image] if image else ["--source", "."]
    gcloud_stream(
        "run", "deploy", SERVICE, *source,
        "--region", REGION,
        "--allow-unauthenticated",
        "--min-instances", "0",
        "--memory", "1Gi",
        "--set-env-vars", f"STAGING=1,STAGING_USER={user},STAGING_PASSWORD={password}",
        "--quiet",
    )

    url = describe("value(status.url)")
    if not url:
        print("deploy-staging: deploy fatto ma non riesco a leggere la URL del servizio.", file=sys.stderr)
        return 1

    # SITE_URL deve essere quella dello stage, non quella di produzione:
    # canonical, og:url e link assoluti altrimenti rimandano al sito vero.
    if env_value("SITE_URL") != url:
        gcloud("run", "services", "update", SERVICE, "--region", REGION,
               "--update-env-vars", f"SITE_URL={url}", "--quiet")

    print()
    print(f"Stage online:  {url}")
    print()

    # --- verifiche: non "il deploy e' riuscito" ma "lo stage si comporta da stage".
    fail = False

    def check(ok: bool, good: str, bad: str) -> None:
        nonlocal fail
        if ok:
            print(f"  ok    {good}")
        else:
            print(f"  ROTTO {bad}", file=sys.stderr)
            fail = True

    anon, _, _ = http(f"{url}/")
    check(anon == 401, "senza password la home risponde 401",
          f"senza password la home risponde {anon}, doveva essere 401")
    wrong, _, _ = http(f"{url}/", auth=(user, "password-sbagliata-di-prova"))
    check(wrong == 401, "una password sbagliata risponde 401",
          f"una password sbagliata risponde {wrong}, doveva essere 401")
    status, _, home = http(f"{url}/", auth=(user, password))
    check(status == 200, "con la password la home si apre",
          f"con la password la home risponde {status}, doveva essere 200")
    _, head_headers, _ = http(f"{url}/", auth=(user, password), head=True)
    robots_header = head_headers.get("x-robots-tag", "")
    check("noindex" in robots_header, f"X-Robots-Tag: {robots_header}",
          f"X-Robots-Tag sulla home: '{robots_header or 'assente'}', doveva essere noindex")
    # Senza credenziali apposta: il file che nega la scansione vale solo se un
    # crawler lo puo' leggere. Dietro al 401 vedrebbe un errore, non un divieto.
    _, _, robots_txt = http(f"{url}/robots.txt")
    check("Disallow: /" in robots_txt, "/robots.txt vieta la scansione",
          "/robots.txt non contiene 'Disallow: /'")
    check("Ambiente di stage" in home, "la fascia di stage e' in pagina",
          "la fascia di stage non compare: la copia e' indistinguibile dal sito vero")
    check("googletagmanager" not in home, "nessun tag di analytics",
          "Google Tag Manager e' attivo sullo stage")

    print()
    if fail:
        print("Lo stage e' online ma NON si comporta da stage: leggi i ROTTO qui sopra.", file=sys.stderr)
        return 1

    print(f"Credenziali dello stage ({origin}):")
    print(f"  utente:   {user}")
    print(f"  password: {password}")
    print()
    print("Da guardare:")
    print(f"  {url}/                     la home (design system 2026)")
    print(f"  {url}/blog                 una pagina non ancora migrata")
    print(f"  {url}/atlante              l'atlante")
    print()
    print(f"Per spegnerlo:  gcloud run services delete {SERVICE} --region {REGION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
