# -*- mode: python ; coding: utf-8 -*-
# Story 2.12: PyInstaller onedir spec for the GraceTree engine.
#
# Build from the project root:
#   node scripts/build-engine.mjs
#
# Or directly (must run from the project root so relative paths resolve):
#   pyinstaller engine/packaging/gracetree-engine.spec
#
# Architecture decision: onedir (NOT onefile). See architecture.md §6.21.
# onedir avoids temp-extraction latency on every launch and makes it easier
# to inspect, sign, and notarise individual files on macOS/Windows.
#
# Model data is NOT bundled. faster-whisper loads the Whisper "base" model
# from an offline local cache (set via GRACETREE_MODEL_DIR env var or the
# HuggingFace default cache). Bundling the model (~150 MB) would exceed the
# target installer size budget and is unnecessary because the model is
# pre-downloaded during the initial setup phase.

from pathlib import Path

block_cipher = None

_spec_dir    = Path(SPEC).resolve().parent          # engine/packaging/
_engine_root = _spec_dir.parent                     # engine/
_proj_root   = _engine_root.parent                  # project root

_contracts_schemas = _proj_root / "packages" / "contracts" / "schemas"
_migrations        = _engine_root / "migrations"
_licenses          = _proj_root / "resources" / "licenses"

a = Analysis(
    [str(_engine_root / "gracetree_engine" / "__main__.py")],
    pathex=[str(_engine_root)],
    binaries=[],
    datas=[
        # Schema JSON files referenced by resource_resolver.contracts_dir()
        (str(_contracts_schemas), "contracts/schemas"),
        # SQL migration files referenced by resource_resolver.migrations_dir()
        (str(_migrations), "migrations"),
        # Third-party license notices
        (str(_licenses), "licenses"),
    ],
    hiddenimports=[
        # Engine sub-packages (PyInstaller may miss them without explicit listing)
        "gracetree_engine.cli",
        "gracetree_engine.resource_resolver",
        "gracetree_engine.diagnostics",
        "gracetree_engine.diagnostics.logger",
        "gracetree_engine.diagnostics.verifier",
        "gracetree_engine.inputs",
        "gracetree_engine.inputs.classifier",
        "gracetree_engine.inputs.input_service",
        "gracetree_engine.inputs.resource_service",
        "gracetree_engine.inputs.validation",
        "gracetree_engine.jobs",
        "gracetree_engine.jobs.attempt_repository",
        "gracetree_engine.jobs.orchestrator",
        "gracetree_engine.media",
        "gracetree_engine.media.audio",
        "gracetree_engine.media.background",
        "gracetree_engine.media.compose",
        "gracetree_engine.media.ffmpeg",
        "gracetree_engine.media.probe",
        "gracetree_engine.media.runner",
        "gracetree_engine.media.validation",
        "gracetree_engine.packaging",
        "gracetree_engine.packaging.verifier",
        "gracetree_engine.scripts",
        "gracetree_engine.scripts.parser",
        "gracetree_engine.scripts.validator",
        "gracetree_engine.speech",
        "gracetree_engine.speech.aligner",
        "gracetree_engine.speech.benchmark",
        "gracetree_engine.speech.config",
        "gracetree_engine.storage",
        "gracetree_engine.storage.commit",
        "gracetree_engine.storage.input_repository",
        "gracetree_engine.storage.job_repository",
        "gracetree_engine.storage.migrations",
        "gracetree_engine.storage.resource_repository",
        "gracetree_engine.subtitles",
        "gracetree_engine.subtitles.config",
        "gracetree_engine.subtitles.generator",
        # faster-whisper and its native backend
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        "huggingface_hub",
        "huggingface_hub.utils",
        # jsonschema 4.x
        "jsonschema",
        "jsonschema.validators",
        "jsonschema._format",
        "jsonschema._legacy_validators",
        "jsonschema._types",
        "jsonschema._utils",
        "jsonschema._validators",
        "jsonschema.exceptions",
        "jsonschema.protocols",
        "jsonschema_specifications",
        "referencing",
        "referencing._core",
        "rpds",
        # stdlib extras that PyInstaller sometimes misses
        "sqlite3",
        "unicodedata",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Test infrastructure — not needed at runtime
        "pytest",
        "py",
        "_pytest",
        # Notebooks / IPython
        "IPython",
        "ipykernel",
        # GUI toolkits
        "tkinter",
        "PyQt5",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gracetree-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="gracetree-engine",
)
