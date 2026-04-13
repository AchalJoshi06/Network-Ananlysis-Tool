# FILE REMOVED

try:
    print("[1/5] Testing imports...")
    from monitor import get_network_monitor, ConnectionInfo
    print("    ✓ monitor module imported")
    
    from main import NetworkAnalysisGUI
    print("    ✓ main module imported")
    
    print()
    print("[2/5] Testing network monitor...")
    monitor = get_network_monitor()
    print("    ✓ Network monitor created")
    
    print()
    print("[3/5] Testing connection info...")
    # Try to get connections
    conns = monitor.get_active_connections()
    print(f"    ✓ Retrieved {len(conns)} connections")
    
    print()
    print("[4/5] Testing GUI initialization...")
    import tkinter as tk
    root = tk.Tk()
    print("    ✓ Tkinter root created")
    
    print()
    print("[5/5] Creating GUI...")
    app = NetworkAnalysisGUI(root)
    print("    ✓ GUI created successfully")
    
    print()
    print("=" * 60)
    print("All tests passed! Starting GUI...")
    print("=" * 60)
    print()
    
    # Start the GUI
    root.mainloop()
    
except Exception as e:
    print()
    print("=" * 60)
    print("ERROR DETECTED!")
    print("=" * 60)
    print()
    print(f"Error: {e}")
    print()
    print("Full traceback:")
    print("-" * 60)
    traceback.print_exc()
    print("-" * 60)
    print()
    input("Press Enter to exit...")
    sys.exit(1)
