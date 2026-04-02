import sys
import time
import random
import gurobipy as gp
from gurobipy import GRB


def read_dataset(file_path):
    num_cells = 0
    demand_vector = [0]  # Thêm 0 ở đầu để index bắt đầu từ 1
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
            freq = 1  # Tần số bắt đầu thử vẫn là 1
            
            while True:
                has_conflict = False
                
                # Kiểm tra nhiễu Co-site (d_ii)
                co_site_dist = distance_matrix[cell][cell]
                for used_f in assignment[cell]:
                    if abs(freq - used_f) < co_site_dist:
                        has_conflict = True
                        break
                
                # Kiểm tra nhiễu Inter-site (d_ij)
                if not has_conflict:
                    # Vòng lặp các trạm lân cận cũng chạy từ 1 đến num_cells
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
                
                # Tăng tần số nếu có xung đột, ngược lại chốt gán
                if has_conflict:
                    freq += 1
                else:
                    assignment[cell].append(freq)
                    break
                    
    # Tìm Max Freq (UB) an toàn, tránh lỗi nếu đồ thị rỗng
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


def solve_with_gurobi(num_cells, demand_vector, matrix, UB):
    """
    Xây dựng và giải mô hình ILP bằng Gurobi, có in nghiệm trung gian.
    """
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)  # Bật log của Gurobi
    env.start()
    model = gp.Model("FAP", env=env)

    # Khởi tạo biến
    x = {}
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    Z = model.addVar(vtype=GRB.INTEGER, name="Z")

    model.setObjective(Z, GRB.MINIMIZE)

    # 1. Ràng buộc: Exactly k
    for i in range(1, num_cells + 1):
        model.addConstr(gp.quicksum(x[i, j] for j in range(1, UB + 1)) == demand_vector[i], name=f"Demand_{i}")

    # 2. Ràng buộc: Max Freq
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            model.addConstr(Z >= j * x[i, j], name=f"MaxFreqTracker_{i}_{j}")

    # 3. Ràng buộc: Symmetry Min Freq
    model.addConstr(gp.quicksum(x[i, 1] for i in range(1, num_cells + 1)) >= 1, name="Symmetry_MinFreq")

    # 4. Ràng buộc: Interference
    for u in range(1, num_cells + 1):
        for v in range(u, num_cells + 1):
            d = matrix[u][v]
            if d > 0:
                for j in range(1, UB + 1):
                    for k in range(max(1, j - d + 1), min(UB, j + d - 1) + 1):
                        if u == v and k <= j:
                            continue  
                        model.addConstr(x[u, j] + x[v, k] <= 1, name=f"Interference_{u}_{v}_{j}_{k}")

    # GẮN CÁC BIẾN VÀ THAM SỐ VÀO MODEL ĐỂ CALLBACK CÓ THỂ ĐỌC ĐƯỢC
    model._x = x
    model._Z = Z
    model._num_cells = num_cells
    model._UB = UB

    # Gọi bộ giải VÀ truyền hàm callback vào
    model.optimize(gurobi_callback)

    # Trích xuất kết quả cuối cùng
    if model.status == GRB.OPTIMAL or model.SolCount > 0:
        max_freq = int(round(Z.X))
        span = max_freq - 1
        
        assignment = {i: [] for i in range(1, num_cells + 1)}
        for i in range(1, num_cells + 1):
            for j in range(1, UB + 1):
                if x[i, j].X > 0.5:  
                    assignment[i].append(j)
                    
        return span, max_freq, assignment
    else:
        return None, None, None

def gurobi_callback(model, where):
    # Kích hoạt khi Gurobi tìm thấy một nghiệm nguyên (MIP Solution) mới
    if where == GRB.Callback.MIPSOL:
        # Lấy thời gian hiện tại của bộ giải
        runtime = model.cbGet(GRB.Callback.RUNTIME)
        
        # Trích xuất giá trị của biến Z (Max Freq) và các biến x
        z_val = model.cbGetSolution(model._Z)
        x_vals = model.cbGetSolution(model._x)
        
        max_freq = int(round(z_val))
        span = max_freq - 1
        
        # Khôi phục lại assignment từ x_vals
        assignment = {i: [] for i in range(1, model._num_cells + 1)}
        for i in range(1, model._num_cells + 1):
            for j in range(1, model._UB + 1):
                if x_vals[i, j] > 0.5:
                    assignment[i].append(j)
                    
        print(f"*** [Callback at {runtime:.2f}s] New Incumbent Found! Span: {span} (Max Freq: {max_freq})")
        # Bỏ comment dòng dưới nếu bạn muốn in chi tiết toàn bộ mảng gán tần số mỗi khi tìm ra
        # print(f"    Assignment: {assignment}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Vui lòng cung cấp tên file dataset. Ví dụ: python script.py dataset1")
        sys.exit(1)

    dataset = sys.argv[1]
    file_path = f"data/{dataset}.txt"
    print(f"Reading dataset from {file_path}...")

    num_cells, demand_vector, matrix = read_dataset(file_path)

    start_time = time.perf_counter()
    
    # Sử dụng Greedy để tìm Upper Bound an toàn
    max_fre_greedy, min_fre_greedy, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    print(f"Greedy span: {max_fre_greedy - min_fre_greedy} ({max_fre_greedy}-{min_fre_greedy})")
    if verify_solution(greedy_assignment, demand_vector, matrix):
        print("Greedy solution is valid.")
    else:
        print("Greedy solution is invalid.")

    # Sử dụng kết quả Greedy làm Upper Bound (không gian tìm kiếm tối đa) cho Gurobi
    UB = max_fre_greedy
    print("-" * 32)
    print(f"Starting Gurobi solver with Initial UB = {UB}...")
    
    span, max_freq_opt, assignment = solve_with_gurobi(num_cells, demand_vector, matrix, UB)

    print("-" * 32)
    if assignment:
        print(f"Optimal span found: {span} ({max_freq_opt}-1)")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")
        if verify_solution(assignment, demand_vector, matrix):
            print("Gurobi solution is valid.")
        else:
            print("Gurobi solution is invalid.")
    else:
        print("No optimal solution found by Gurobi.")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")