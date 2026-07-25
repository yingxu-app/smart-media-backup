"""PyInstaller entry point for Smart Media Backup"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from smb.server import main
main()
