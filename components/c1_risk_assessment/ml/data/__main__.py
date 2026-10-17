from pathlib import Path

from ml.data.make_synthetic import write_synthetic

if __name__ == "__main__":
    write_synthetic(Path("ml/data/synthetic/visits.csv"))
