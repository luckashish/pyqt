try:
    import pandas_ta
    print("pandas_ta is installed")
except ImportError:
    print("pandas_ta is NOT installed")
except Exception as e:
    print(f"Error importing pandas_ta: {e}")
