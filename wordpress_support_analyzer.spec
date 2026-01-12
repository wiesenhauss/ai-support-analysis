# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os

# Collect all Python scripts as data files
script_files = [
    'utils.py',  # Shared utilities module - MUST be first so other scripts can import it
    'orchestrator.py',
    'main-analysis-process.py',
    'support-data-precleanup.py',
    'support-data-cleanup.py',
    'predict_csat.py',
    'topic-aggregator.py',
    'csat-trends.py',
    'product-feedback-trends.py',
    'goals-trends.py',
    'custom-analysis.py',
    'aggregate-daily-reports.py',
    'visualize-overall-sentiment.py',
    'talktodata.py'
]

datas = []
for script in script_files:
    if os.path.exists(script):
        datas.append((script, '.'))

# Add any additional data files if they exist
additional_files = [
    'version.json',
    '.analyzer_settings.json'
]

for file in additional_files:
    if os.path.exists(file):
        datas.append((file, '.'))

block_cipher = None

a = Analysis(
    ['gui_app.py'],  # Main GUI application
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Local modules
        'utils',  # Shared utilities module
        
        # GUI and system modules
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'threading',
        'subprocess',
        'queue',
        'json',
        'datetime',
        'os',
        'sys',
        'time',
        'pathlib',
        'argparse',
        'logging',
        'select',
        'fcntl',
        'glob',
        
        # AI and data processing
        'openai',
        'openai.types',
        'openai.resources',
        'pandas',
        'pandas.core',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.core.dtypes',
        'pandas.core.dtypes.common',
        'pandas.io',
        'pandas.io.common',
        'pandas.io.parsers',
        'pandas.api',
        'pandas.api.types',
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        
        # Visualization
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_tkagg',
        'seaborn',
        'plotly',
        'plotly.graph_objects',
        'plotly.express',
        
        # Network and file handling
        'requests',
        'urllib3',
        'charset_normalizer',
        'idna',
        'certifi',
        'python-dotenv',
        'dotenv',
        'openpyxl',
        'xlsxwriter',
        
        # Token counting
        'tiktoken',
        'tiktoken.core',
        'tiktoken.model',
        
        # Progress bars and utilities
        'tqdm',
        'tqdm.auto',
        'tqdm.std',
        
        # Additional dependencies that might be missed
        'typing_extensions',
        'packaging',
        'six',
        'pyparsing',
        'cycler',
        'kiwisolver',
        'fonttools',
        'pillow',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific configuration
import sys
if sys.platform == 'darwin':
    # macOS - create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='AI_Support_Analyzer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
    
    app = BUNDLE(
        exe,
        name='AI Support Analyzer.app',
        icon=None,
        bundle_identifier='com.automattic.ai-support-analyzer',
        version='1.4.0',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleName': 'AI Support Analyzer',
            'CFBundleDisplayName': 'AI Support Analyzer',
            'CFBundleGetInfoString': 'AI Support Analysis Tool for Customer Data',
            'CFBundleIdentifier': 'com.automattic.ai-support-analyzer',
            'CFBundleVersion': '1.4.0',
            'CFBundleShortVersionString': '1.4.0',
            'NSHumanReadableCopyright': 'Copyright © 2025 Automattic Inc.',
            'NSHighResolutionCapable': 'True',
            'LSApplicationCategoryType': 'public.app-category.business',
        },
    )
else:
    # Windows/Linux - create single executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='AI_Support_Analyzer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window for GUI
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )