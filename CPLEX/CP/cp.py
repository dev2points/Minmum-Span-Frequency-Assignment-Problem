import sys
import time
from docplex.cp.model import CpoModel

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

def solve_with_cp(num_cells, demand_vector, matrix, UB):
    """
    Xây dựng và giải bằng Constraint Programming (CPLEX CPO).
    """
    mdl = CpoModel(name='FAP_CP')

    # Biến số: Thay vì mảng nhị phân, ta tạo trực tiếp các biến số nguyên đại diện cho tần số
    # freq_vars[(i, k)] là tần số thứ k được gán cho cell i
    freq_vars = {}
    all_vars = []
    
    for i in range(1, num_cells + 1):
        for k in range(demand_vector[i]):
            # Miền giá trị của mỗi tần số là từ 1 đến UB
            var = mdl.integer_var(1, UB, name=f"f_{i}_{k}")
            freq_vars[(i, k)] = var
            all_vars.append(var)

    # 1. Hàm mục tiêu: Tối thiểu hóa tần số lớn nhất (Z)
    # [ĐÃ SỬA]: Khai báo Z là một biến nguyên thay vì một biểu thức để có thể get_value()
    Z = mdl.integer_var(1, UB, name="Z")
    mdl.add(Z == mdl.max(all_vars))
    mdl.add(mdl.minimize(Z))

    # 2. Ràng buộc Symmetry Breaking & Co-site (Nhiễu cục bộ)
    for i in range(1, num_cells + 1):
        d_ii = matrix[i][i]
        for k in range(demand_vector[i] - 1):
            mdl.add(freq_vars[(i, k+1)] - freq_vars[(i, k)] >= d_ii)

    # 3. Ràng buộc Inter-site (Nhiễu liên trạm)
    for i in range(1, num_cells + 1):
        for j in range(i + 1, num_cells + 1):
            d_ij = matrix[i][j]
            if d_ij > 0:
                for k in range(demand_vector[i]):
                    for m in range(demand_vector[j]):
                        mdl.add(mdl.abs(freq_vars[(i, k)] - freq_vars[(j, m)]) >= d_ij)

    # 4. Global Symmetry Breaking: Bắt buộc tần số nhỏ nhất trên toàn mạng bằng 1
    mdl.add(mdl.min(all_vars) == 1)

    # Gọi bộ giải CP
    print("Mô hình CP đã xây dựng xong, bắt đầu giải...")
    # Thêm TimeLimit nếu bạn không muốn chờ quá lâu (ví dụ: TimeLimit=60)
    solution = mdl.solve(LogVerbosity="Terse")

    # Trích xuất kết quả
    if solution and solution.is_solution():
        # Lệnh này giờ sẽ chạy thành công vì Z là một decision variable
        max_freq = solution.get_value(Z)
        span = max_freq - 1
        
        assignment = {i: [] for i in range(1, num_cells + 1)}
        for i in range(1, num_cells + 1):
            for k in range(demand_vector[i]):
                val = solution.get_value(freq_vars[(i, k)])
                assignment[i].append(val)
                
        return span, max_freq, assignment
    else:
        return None, None, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Vui lòng cung cấp tên file dataset. Ví dụ: python script.py dataset1")
        sys.exit(1)

    dataset = sys.argv[1]
    # Sửa lại đường dẫn file nếu file txt không nằm trong thư mục data/
    file_path = f"data/{dataset}.txt"
    print(f"Reading dataset from {file_path}...")

    num_cells, demand_vector, matrix = read_dataset(file_path)

    start_time = time.perf_counter()
    
    # Sử dụng Greedy để tìm Upper Bound
    max_fre_greedy, min_fre_greedy, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    print(f"Greedy span: {max_fre_greedy - min_fre_greedy} ({max_fre_greedy}-{min_fre_greedy})")
    
    UB = max_fre_greedy
    print("-" * 32)
    print(f"Starting CP Optimizer with Initial UB = {UB}...")
    
    span, max_freq_opt, assignment = solve_with_cp(num_cells, demand_vector, matrix, UB)

    print("-" * 32)
    if assignment:
        print(f"Optimal span found: {span} ({max_freq_opt}-1)")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")
        if verify_solution(assignment, demand_vector, matrix):
            print("CP solution is valid.")
        else:
            print("CP solution is invalid.")
    else:
        print("No optimal solution found by CP.")
        print(f"Total time taken: {time.perf_counter() - start_time:.2f}s")