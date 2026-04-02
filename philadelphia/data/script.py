import os
import csv
import re
import sys

def extract_result(file_path):
    result = None
    status = "-"

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

        # 1. Check optimal trước
        match_opt = re.search(r"Optimal span found:\s*(\d+)", content)
        if match_opt:
            return match_opt.group(1), "optimal"

        # 2. Lấy tất cả Span rồi chọn cái cuối
        matches = re.findall(r"Span:\s*(\d+)", content)
        if matches:
            result = matches[-1]

    return result, status


def process_folder(folder_path, output_csv="results.csv"):
    rows = []

    for i in range(1, 20):
        filename = f"P{i}.log"
        file_path = os.path.join(folder_path, filename)

        if os.path.exists(file_path):
            result, status = extract_result(file_path)
        else:
            result, status = None, "-"

        rows.append([f"P{i}", result, status])

    # ghi CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["problem", "result", "status"])
        writer.writerows(rows)

    print(f"Saved to {output_csv}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)
    folder_path = sys.argv[1]
    process_folder(folder_path)