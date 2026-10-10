"""Collega il branch `stage` allo stage: da qui in poi ogni push su `stage`
costruisce, deploya e verifica da se'. Si esegue UNA VOLTA.

    bin/py scripts/setup_staging_trigger.py        (oppure bin/setup-staging-trigger)

Poi, per sempre:

    git push origin stage

Crea un trigger Cloud Build gemello di quello che gia' esiste per `master`,
puntato su cloudbuild-staging.yaml. Non tocca il trigger di produzione, non
tocca il servizio di produzione, e se il trigger c'e' gia' lo dice e si ferma
invece di crearne un secondo che deployerebbe due volte a ogni push.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

TRIGGER = os.environ.get("STAGING_TRIGGER", "diset-viz-stage")
REGION = os.environ.get("STAGING_TRIGGER_REGION", "global")
REPO_OWNER = os.environ.get("STAGING_REPO_OWNER", "nmaiese")
REPO_NAME = os.environ.get("STAGING_REPO_NAME", "diset-viz")
BRANCH = os.environ.get("STAGING_BRANCH", "stage")


def main() -> int:
    exe = shutil.which("gcloud")
    if not exe:
        print("setup-staging-trigger: gcloud non e' installato.\n"
              "  https://cloud.google.com/sdk/docs/install", file=sys.stderr)
        return 127

    def run(*args: str, stream: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run([exe, *args], text=True, capture_output=not stream)

    project = run("config", "get-value", "project").stdout.strip()
    if not project or project == "(unset)":
        print("setup-staging-trigger: nessun progetto impostato. "
              "Esegui:  gcloud config set project IL_TUO_PROGETTO", file=sys.stderr)
        return 1

    if run("builds", "triggers", "describe", TRIGGER, "--region", REGION).returncode == 0:
        print(f"Il trigger '{TRIGGER}' esiste gia': non tocco niente.")
        print(f"Per cambiarlo:  gcloud builds triggers delete {TRIGGER} --region {REGION}")
        return 0

    print(f"Creo il trigger '{TRIGGER}'")
    print(f"  progetto: {project}")
    print(f"  repo:     {REPO_OWNER}/{REPO_NAME}")
    print(f"  branch:   {BRANCH}")
    print("  build:    cloudbuild-staging.yaml")
    print()

    # `--repo-name`/`--repo-owner` e' la connessione GitHub classica, la stessa
    # che regge il trigger di master: se master si deploya da sola, questa c'e'
    # gia' e non serve autorizzare niente di nuovo.
    created = run(
        "builds", "triggers", "create", "github",
        "--name", TRIGGER,
        "--region", REGION,
        "--repo-owner", REPO_OWNER,
        "--repo-name", REPO_NAME,
        "--branch-pattern", f"^{BRANCH}$",
        "--build-config", "cloudbuild-staging.yaml",
        "--description", f"Build, deploy e verifica dello stage a ogni push su {BRANCH}",
        stream=True,
    )
    if created.returncode != 0:
        return created.returncode

    print()
    print("Fatto. Da adesso:")
    print(f"  git push origin {BRANCH}        costruisce, deploya e verifica lo stage")
    print()
    print("La prima build genera la password e la stampa nel log. Per rileggerla:")
    print("  gcloud run services describe diset-viz-staging --region europe-west1 \\")
    print("    --format='value(spec.template.spec.containers[0].env.filter(\"name:STAGING_PASSWORD\").extract(\"value\"))'")
    print()
    print("Se la build fallisce sul deploy, alla service account di Cloud Build")
    print("mancano i ruoli: roles/run.admin e roles/iam.serviceAccountUser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
