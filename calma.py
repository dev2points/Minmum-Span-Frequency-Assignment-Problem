import os
import re
import csv

RESULTS_DIR = "results"
OUTPUT_CSV = "calma.csv"

# ===== DANH SÁCH DATASET =====
datasets = []

datasets += [f"graph{str(i).zfill(2)}" for i in range(1, 15)]
datasets += [f"scen{str(i).zfill(2)}" for i in range(1, 12)]
datasets += [f"TUD200.{i}" for i in range(1, 6)]
datasets += [f"TUD916.{i}" for i in range(1, 6)]


def extract_optimal(content):
    match = re.search(r"Optimal span:\s*(\d+)", content)
    if match:
        return match.group(1)
    return "-"


def extract_time(content):
    # tìm tất cả các dòng Time taken
    matches = re.findall(r"Time taken:\s*([\d\.]+)", content)
    if matches:
        return matches[-1]  # lấy cái cuối cùng
    return "-"


def main():
    rows = []

    for dataset in datasets:
        filepath = os.path.join(RESULTS_DIR, f"{dataset}.log")

        if not os.path.exists(filepath):
            optimal = "-"
            time = "-"
        else:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            optimal = extract_optimal(content)
            time = extract_time(content)

        rows.append([dataset, optimal, time])

    # ghi CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dataset", "optimal", "time_seconds"])
        writer.writerows(rows)

    print(f"Done! Output written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()