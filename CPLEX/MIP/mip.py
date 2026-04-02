import sys
import time
import random
from docplex.mp.model import Model
from docplex.mp.progress import ProgressListener

# --- ĐỊNH NGHĨA CLASS CALLBACK ---
class IncumbentCallback(ProgressListener):
    def __init__(self, start_time, num_cells, UB, x_vars, z_var):
        super().__init__()
        self.start_time = start_time
        self.num_cells = num_cells
        self.UB = UB
        self.x = x_vars
        self.Z = z_var

    def notify_solution(self, sol):
        """Được gọi mỗi khi CPLEX tìm thấy một nghiệm (incumbent) mới"""
        elapsed = time.perf_counter() - self.start_time
        
        # Trích xuất giá trị hàm mục tiêu
        max_freq = int(round(sol.get_value(self.Z)))
        span = max_freq - 1
        
        # Khôi phục mảng gán tần số
        assignment = {i: [] for i in range(1, self.num_cells + 1)}
        for i in range(1, self.num_cells + 1):
            for j in range(1, self.UB + 1):
                if sol.get_value(self.x[i, j]) > 0.5:
                    assignment[i].append(j)
                    
        print(f"\n*** [Callback at {elapsed:.2f}s] New Incumbent Found! Span: {span} (Max Freq: {max_freq})")
        # Bỏ comment dòng dưới để in toàn bộ mảng gán mỗi khi tìm ra nghiệm mới
        # print(f"    Assignment: {assignment}\n")


def read_dataset(file_path):
    num_cells = 0
    demand_vector = [0]
    matrix = []
    
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
        
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("Number of cells:"):
            num_cells = int(line.split(":")[1].strip())
            matrix.append([0] * (num_cells + 1))
            
        elif line.startswith("Demand Vector:"):
            i += 1 
            demands = list(map(int, lines[i].split(',')))
            demand_vector.extend(demands)
            
        elif line.startswith("Matrix for"):
            i += 1 
            for _ in range(num_cells):
                if i < len(lines):
                    row_data = list(map(int, lines[i].split(',')))
                    matrix.append([0] + row_data)
                    i += 1
            break 
            
        i += 1

    return num_cells, demand_vector, matrix

def greedy(num_cells, demand, distance_matrix):
    assignment = {i: [] for i in range(1, num_cells + 1)}
    sorted_cells = sorted(range(1, num_cells + 1), key=lambda x: demand[x], reverse=True)
    
    for cell in sorted_cells:
        for _ in range(demand[cell]):
            freq = 1
            while True:
                has_conflict = False
                
                # Co-site
                co_site_dist = distance_matrix[cell][cell]
                for used_f in assignment[cell]:
                    if abs(freq - used_f) < co_site_dist:
                        has_conflict = True
                        break
                
                # Inter-site
                if not has_conflict:
                    for other_cell in range(1, num_cells + 1):
                        if other_cell == cell or not assignment[other_cell]:
                            continue
                        
                        inter_site_dist = distance_matrix[cell][other_cell]
                        if inter_site_dist > 0:
                            for used_f in assignment[other_cell]:
                                if abs(freq - used_f) < inter_site_dist:
                                    has_conflict = True
                                    break
                        if has_conflict:
                            break
                
                if has_conflict:
                    freq += 1
                else:
                    assignment[cell].append(freq)
                    break
                    
    max_freq = 0
    min_freq = 10000
    for freqs in assignment.values():
        if freqs:
            max_freq = max(max_freq, max(freqs))
            min_freq = min(min_freq, min(freqs))
            
    return max_freq, min_freq, assignment

def verify_solution(assignment, demand_vector, distance_matrix):
    for cell, freqs in assignment.items():
        if len(freqs) != demand_vector[cell]:
            print(f"Cell {cell} has {len(freqs)} frequencies assigned, but demand is {demand_vector[cell]}.")
            return False
            
        for i in range(len(freqs)):
            for j in range(i + 1, len(freqs)):
                if abs(freqs[i] - freqs[j]) < distance_matrix[cell][cell]:
                    print(f"Co-site interference in cell {cell}: freqs {freqs[i]}, {freqs[j]}.")
                    return False
        
        for other_cell, other_freqs in assignment.items():
            if other_cell == cell:
                continue
            inter_site_dist = distance_matrix[cell][other_cell]
            if inter_site_dist > 0:
                for f1 in freqs:
                    for f2 in other_freqs:
                        if abs(f1 - f2) < inter_site_dist:
                            print(f"Inter-site interference between cell {cell} (freq {f1}) and cell {other_cell} (freq {f2}).")
                            return False
    return True

def solve_with_cplex(num_cells, demand_vector, matrix, UB):
    """
    Xây dựng và giải mô hình ILP bằng CPLEX (docplex).
    """
    # Khởi tạo mô hình CPLEX
    mdl = Model(name='FAP')
    
    # Bật log của CPLEX để theo dõi quá trình giải
    mdl.parameters.mip.display = 2

    # Biến x[i, j]: 1 nếu cell i sử dụng tần số j, ngược lại 0
    x = {}
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            x[i, j] = mdl.binary_var(name=f"x_{i}_{j}")

    # Biến Z: Đại diện cho Max Frequency (tần số lớn nhất được sử dụng)
    Z = mdl.integer_var(name="Z")

    # Hàm mục tiêu: Tối thiểu hóa Z
    mdl.minimize(Z)

    # 1. Ràng buộc: Exactly k (Demand)
    for i in range(1, num_cells + 1):
        mdl.add_constraint(mdl.sum(x[i, j] for j in range(1, UB + 1)) == demand_vector[i], ctname=f"Demand_{i}")

    # 2. Ràng buộc: Theo dõi tần số lớn nhất
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            mdl.add_constraint(Z >= j * x[i, j], ctname=f"MaxFreqTracker_{i}_{j}")

    # 3. Ràng buộc Symmetry Breaking: Bắt buộc tần số 1 phải được sử dụng ít nhất 1 lần
    mdl.add_constraint(mdl.sum(x[i, 1] for i in range(1, num_cells + 1)) >= 1, ctname="Symmetry_MinFreq")

    # 4. Ràng buộc: Khoảng cách (Interference)
    for u in range(1, num_cells + 1):
        for v in range(u, num_cells + 1):
            d = matrix[u][v]
            if d > 0:
                for j in range(1, UB + 1):
                    for k in range(max(1, j - d + 1), min(UB, j + d - 1) + 1):
                        # Bỏ qua để tránh thêm trùng lặp ràng buộc co-site
                        if u == v and k <= j:
                            continue  
                        
                        # Không thể đồng thời gán tần số j cho u và k cho v
                        mdl.add_constraint(x[u, j] + x[v, k] <= 1, ctname=f"Interference_{u}_{v}_{j}_{k}")

    # --- ĐĂNG KÝ CALLBACK LẮNG NGHE NGHIỆM ---
    start_solve_time = time.perf_counter()
    listener = IncumbentCallback(start_solve_time, num_cells, UB, x, Z)
    mdl.add_progress_listener(listener)

    # Gọi bộ giải
    solution = mdl.solve(log_output=True)

    # Trích xuất kết quả cuối cùng
    if solution:
        max_freq = int(round(solution.get_value(Z)))
        span = max_freq - 1
        
        assignment = {i: [] for i in range(1, num_cells + 1)}
        for i in range(1, num_cells + 1):
            for j in range(1, UB + 1):
                if solution.get_value(x[i, j]) > 0.5:
                    assignment[i].append(j)
                    
        return span, max_freq, assignment
    else:
        return None, None, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Vui lòng cung cấp tên file dataset. Ví dụ: python script.py dataset1")
        sys.exit(1)

    dataset = sys.argv[1]
    file_path = f"data/{dataset}.txt"
    print(f"Reading dataset from {file_path}...")

    num_cells, demand_vector, matrix = read_dataset(file_path)

    start_time = time.perf_counter()
    
    # Greedy để tìm UB
    max_fre_greedy, min_fre_greedy, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    print(f"Greedy span: {max_fre_greedy - min_fre_greedy} ({max_fre_greedy}-{min_fre_greedy})")
    
    UB = max_fre_greedy
    print("-" * 32)
    print(f"Starting CPLEX solver with Initial UB = {UB}...")
    
    span, max_freq_opt, assignment = solve_with_cplex(num_cells, demand_vector, matrix, UB)

    print("-" * 32)
    if assignment:
        print(f"Optimal span found: {span} ({max_freq_opt}-1)")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")
        if verify_solution(assignment, demand_vector, matrix):
            print("CPLEX solution is valid.")
        else:
            print("CPLEX solution is invalid.")
    else:
        print("No optimal solution found by CPLEX.")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")